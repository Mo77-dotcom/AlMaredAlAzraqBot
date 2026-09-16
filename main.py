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
    if not message:
        return

    user_text = message.caption or message.text or ""

    try:
        # 1. معالجة الصور (سواء أُرسلت لوحدها أو مع تعليق تحتها)
        if message.photo:
            photo = message.photo[-1]
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            
            # النص الافتراضي للتحليل إذا لم يكتب المستخدم تعليقاً
            prompt_text = user_text if user_text else "حلل هذه الصورة بدقة فائقة واستخرج كافة التفاصيل والعناصر الموجودة فيها."
            
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[
                    prompt_text,
                    {
                        "mime_type": "image/jpeg",
                        "data": bytes(file_bytes)
                    }
                ],
                config={
                    'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. تحلل بدقة فائقة الصور والملفات وتجيب باحترافية.'
                }
            )
            await message.reply_text(response.text)
            return

        # 2. معالجة المستندات والملفات (PDF وغيرها)
        elif message.document:
            file_obj = await context.bot.get_file(message.document.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            mime_type = message.document.mime_type or "application/pdf"
            
            prompt_text = user_text if user_text else "حلل هذا المستند بدقة واستخرج أبرز النقاط والأفكار."
            
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[
                    prompt_text,
                    {
                        "mime_type": mime_type,
                        "data": bytes(file_bytes)
                    }
                ],
                config={
                    'system_instruction': 'أنت المارد الأزرق ([], مساعد ذكي لطلاب الجامعات في سوريا. تحلل بدقة فائقة الصور والملفات وتجيب باحترافية.'
                }
            )
            await message.reply_text(response.text)
            return

        # 3. معالجة النصوص العادية
        elif user_text:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[user_text],
                config={
                    'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا.'
                }
            )
            await message.reply_text(response.text)

    except Exception as e:
        await message.reply_text(f"خطأ تقني أثناء المعالجة: {e}")

def main():
    t = threading.Thread(target=run_health_check)
    t.daemon = True
    t.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # استخدام فلتر عام شامل لالتقاط كل الرسائل بدون استثناء
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
