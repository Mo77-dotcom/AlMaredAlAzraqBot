import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from google import genai

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

user_last_file = {}

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
    user_id = update.effective_user.id
    user_text = message.caption or message.text or ""

    try:
        file_bytes = None
        mime_type = "application/pdf"
        is_new_file = False

        # 1. فحص الصور
        if message.photo:
            photo = message.photo[-1]
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            mime_type = "image/jpeg"
            is_new_file = True

        # 2. فحص المستندات والـ PDF
        elif message.document:
            file_obj = await context.bot.get_file(message.document.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            mime_type = message.document.mime_type or "application/pdf"
            is_new_file = True

        # 3. فحص الفيديوهات أو الصوتيات
        elif message.video or message.audio or message.effective_attachment:
            attachment = message.video or message.audio or message.effective_attachment
            if hasattr(attachment, 'file_id'):
                file_obj = await context.bot.get_file(attachment.file_id)
                file_bytes = await file_obj.download_as_bytearray()
                mime_type = getattr(attachment, 'mime_type', 'video/mp4')
                is_new_file = True

        # إذا أرسل المستخدم ملفاً جديداً
        if is_new_file and file_bytes:
            user_last_file[user_id] = {"data": bytes(file_bytes), "mime_type": mime_type}
            
            # إذا كان هناك نص مع الملف (Caption)، قم بتحليله فوراً دون انتظار!
            if user_text and user_text not in ["حلل", "حلله", "حللي", "تحليل"]:
                contents = [user_text, {"mime_type": mime_type, "data": bytes(file_bytes)}]
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=contents,
                    config={'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. تحلل بدقة فائقة الملفات والصور والفيديوهات.'}
                )
                await message.reply_text(response.text)
                return
            else:
                await message.reply_text("📥 تم استلام الملف بنجاح! تفضل بأمرني الآن (مثال: حلل الملف، استخرج النقاط...).")
                return

        # إذا أرسل نصاً استكمائياً (مثل "حلله" أو "تحليل")
        if user_text:
            contents = [user_text]
            if user_id in user_last_file:
                contents.append({
                    "mime_type": user_last_file[user_id]["mime_type"],
                    "data": user_last_file[user_id]["data"]
                })
            else:
                await message.reply_text("⚠️ لم أجد أي ملف محفوظ في الذاكرة. يرجى إرسال الملف أولاً أو إرفاقه مع رسالتك.")
                return

            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=contents,
                config={'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. تحلل بدقة فائقة الملفات والصور والفيديوهات.'}
            )
            await message.reply_text(response.text)

    except Exception as e:
        await message.reply_text(f"خطأ تقني أثناء المعالجة: {e}")

def main():
    t = threading.Thread(target=run_health_check)
    t.daemon = True
    t.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.ATTACHMENT) & (~filters.COMMAND), handle_message))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
