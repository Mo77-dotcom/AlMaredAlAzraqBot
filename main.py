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
    user_text = message.caption or message.text or "حلل هذا الملف بدقة واستخرج أبرز النقاط."
    
    try:
        contents = [user_text]
        
        # التقاط الملف المرفق (PDF أو مستند) بطريقة صحيحة ودقيقة
        if message.document:
            file = await context.bot.get_file(message.document.file_id)
            file_bytes = await file.download_as_bytearray()
            
            contents.append({
                "mime_type": message.document.mime_type or "application/pdf",
                "data": bytes(file_bytes)
            })

        # إرسال المحتوى والملف إلى نموذج gemini-3.6-flash
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=contents,
            config={
                'system_instruction': 'أنت المارد الأزرق 🧞، مساعدك الذكي لطلاب الجامعات في سوريا. قم بتحليل الملفات والأسئلة بدقة واحترافية.'
            }
        )
        
        await message.reply_text(response.text)
        
    except Exception as e:
        await message.reply_text(f"خطأ تقني أثناء معالجة الملف: {e}")

def main():
    t = threading.Thread(target=run_health_check)
    t.daemon = True
    t.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # فلتر شامل يلتقط النصوص والملفات والمستندات بكافة أنواعها
    app.add_handler(MessageHandler((filters.TEXT | filters.Document.ALL) & (~filters.COMMAND), handle_message))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
