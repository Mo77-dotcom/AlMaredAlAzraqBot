import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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
        # معالجة الصور بالطريقة الصحيحة والآمنة
        if message.photo:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="upload_photo")
            photo = message.photo[-1]
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            
            prompt_text = message.caption if message.caption else "حلل هذه الصورة بالتفصيل وباختصار."
            
            # رفع الصورة كجزء بايتات مباشر بالطريقة المتوافقة تماماً مع الـ SDK الجديد
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=[
                    prompt_text,
                    client.types.Part.from_bytes(
                        data=bytes(file_bytes),
                        mime_type="image/jpeg",
                    ),
                ],
                config={'system_instruction': 'أنت مساعد ذكي متعدد الوسائط. قدم إجابات دقيقة ومفيدة.'}
            )
            
            if response and response.text:
                await message.reply_text(response.text[:3500])
            else:
                await message.reply_text("عذراً، لم أتمكن من تحليل الصورة.")
            return

        # معالجة النصوص العادية
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
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
