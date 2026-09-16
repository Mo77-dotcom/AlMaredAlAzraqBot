import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# خادم الصحة للحفاظ على تشغيل البوت 24/7 على Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active 24/7!")

def run_health_check():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    try:
        # 1. معالجة الصور
        if message.photo:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="upload_photo")
            photo = message.photo[-1]
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[
                    message.caption if message.caption else "حلل هذه الصورة بالتفصيل واذكر أهم ما فيها.",
                    {
                        "mime_type": "image/jpeg",
                        "data": bytes(file_bytes)
                    }
                ],
                config={'system_instruction': 'أنت مساعد ذكي متعدد الوسائط. قدم إجابات دقيقة ومفيدة.'}
            )
            
            if response and response.text:
                await message.reply_text(response.text[:3500])
            else:
                await message.reply_text("عذراً، لم أتمكن من تحليل الصورة.")
            return

        # 2. معالجة ملفات الـ PDF أو المستندات أو الفيديوهات المرفوعة كملفات
        if message.document or message.video:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            
            media_obj = message.document or message.video
            file_obj = await context.bot.get_file(media_obj.file_id)
            
            # تحميل الملف مؤقتامحلياً لمعالجته
            file_extension = media_obj.file_name.split('.')[-1] if media_obj.file_name else "bin"
            temp_filename = f"temp_file.{file_extension}"
            await file_obj.download_to_drive(temp_filename)
            
            # رفع الملف إلى خوادم Gemini للتعامل مع الملفات الكبيرة (PDF / Video)
            uploaded_file_ref = client.files.upload(file=temp_filename)
            
            prompt_text = message.caption if message.caption else "قم بتحليل هذا الملف أو الفيديو وتلخيص محتواه بشكل شامل."
            
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[uploaded_file_ref, prompt_text]
            )
            
            # حذف الملف المؤقت من الذاكرة المحلية للحفاظ على مساحة السيرفر
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                
            if response and response.text:
                await message.reply_text(response.text[:3500])
            else:
                await message.reply_text("عذراً، لم أتمكن من معالجة الملف.")
            return

        # 3. معالجة النصوص العادية
        if message.text:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[message.text],
                config={'system_instruction': 'أنت مساعد ذكي ومحترف.'}
            )
            if response and response.text:
                await message.reply_text(response.text[:3500])
            return

    except Exception as e:
        await message.reply_text(f"حدث خطأ أثناء المعالجة: {str(e)[:200]}")

def main():
    t = threading.Thread(target=run_health_check)
    t.daemon = True
    t.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))
    
    print("Bot is polling safely...")
    # drop_pending_updates لمنع تضارب الاتصالات وتوقف البوت نهائياً
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
