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
    user_text = message.caption or message.text or "قم بتحليل هذا الملف أو الصورة أو الفيديو بدقة واستخرج كافة التفاصيل والمحتوى."
    
    try:
        contents = [user_text]
        file_bytes = None
        mime_type = "application/pdf"

        # 1. التعامل مع الصور المرفقة
        if message.photo:
            photo = message.photo[-1] # اختيار أعلى دقة للصورة
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            mime_type = "image/jpeg"

        # 2. التعامل مع ملفات الـ PDF والمستندات
        elif message.document:
            file_obj = await context.bot.get_file(message.document.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            mime_type = message.document.mime_type or "application/pdf"

        # 3. التعامل مع ملفات الفيديو والصوت
        elif message.video or message.audio or message.effective_attachment:
            attachment = message.video or message.audio or message.effective_attachment
            if hasattr(attachment, 'file_id'):
                file_obj = await context.bot.get_file(attachment.file_id)
                file_bytes = await file_obj.download_as_bytearray()
                mime_type = getattr(attachment, 'mime_type', 'video/mp4')

        # إرفاق البيانات إن وجدت إلى محتوى الطلب للذكاء الاصطناعي
        if file_bytes:
            contents.append({
                "mime_type": mime_type,
                "data": bytes(file_bytes)
            })

        # إرسال البيانات للنموذج gemini-3.6-flash
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=contents,
            config={
                'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. تحلل بدقة فائقة الصور، ملفات الـ PDF، والفيديوهات وتجيب بوضوح واحترافية.'
            }
        )
        
        await message.reply_text(response.text)
        
    except Exception as e:
        await message.reply_text(f"خطأ تقني أثناء معالجة الملف أو الوسائط: {e}")

def main():
    t = threading.Thread(target=run_health_check)
    t.daemon = True
    t.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # فلاتر شاملة تلتقط النصوص، الصور، المستندات، والفيديوهات والملفات بكل أنواعها
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.ATTACHMENT) & (~filters.COMMAND), handle_message))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
