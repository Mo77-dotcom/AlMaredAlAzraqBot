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
        # إذا أرسل المستخدم صورة
        if message.photo:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="upload_photo")
            
            photo = message.photo[-1]
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            
            user_caption = message.caption if message.caption else "عطني خلاصة تحليل هذه الصورة بختصار."

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    user_caption,
                    {
                        "mime_type": "image/jpeg",
                        "data": bytes(file_bytes)
                    }
                ],
                config={
                    'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. قدم إجابات مركزة، مختصرة جداً، ومباشرة بدون إطالة أو حشو لكي تظهر في رسالة واحدة قصيرة.'
                }
            )
            
            if response and response.text:
                # اقتطاع الرد إجباريًا إذا زاد عن 3500 حرف لمنع أي خطأ نهائياً
                final_text = response.text[:3500]
                await message.reply_text(final_text)
            else:
                await message.reply_text("عذراً، لم أتمكن من استخراج نتيجة من الصورة.")
            return

        # إذا أرسل نصاً عادياً
        if message.text:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[message.text],
                config={
                    'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. أجب باختصار.'
                }
            )
            
            if response and response.text:
                final_text = response.text[:3500]
                await message.reply_text(final_text)
            return

    except Exception as e:
        await message.reply_text(f"حدث خطأ تقني أثناء المعالجة: {e}")

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
