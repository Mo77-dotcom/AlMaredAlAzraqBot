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

    try:
        # إذا أرسل المستخدم صورة، نقوم بتحليلها وإرسال الجواب فوراً
        if message.photo:
            await message.reply_text("🔍 جاري تحليل الصورة بدقة، دقيقة واحدة...")
            
            photo = message.photo[-1]
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            
            user_caption = message.caption if message.caption else "حلل هذه الصورة بدقة فائقة واستخرج كافة العناصر والتفاصيل الموجودة فيها."

            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[
                    user_caption,
                    {
                        "mime_type": "image/jpeg",
                        "data": bytes(file_bytes)
                    }
                ],
                config={
                    'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. تحلل الصور بدقة فائقة واحترافية.'
                }
            )
            
            await message.reply_text(response.text)
            return

        # إذا أرسل نصاً عادياً (دردشة)
        if message.text:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[message.text],
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
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), handle_message))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
