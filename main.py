import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import google.generativeai as genai

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="أنت المارد الأزرق، مساعد ذكي لطلاب الجامعات في سوريا. أجب بأسلوب متعاون ودقيق."
)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running 24/7!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "أهلاً بك! أنا المارد الأزرق 🧞‍♂️، مساعدك الذكي لطلاب الجامعات في سوريا.\n\n"
        "أنا هنا لمساعدتك في استفساراتك الجامعية والأكاديمية. تفضل بطرح سؤالك!"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        response = model.generate_content(user_text)
        bot_reply = response.text if response.text else "عذراً، لم أستطع معالجة الإجابة حالياً."
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        bot_reply = "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي، يرجى المحاولة لاحقاً."
    
    await update.message.reply_text(bot_reply)

if __name__ == '__main__':
    Thread(target=run_health_check_server, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Al-Mared Al-Azraq Bot is running...")
    app.run_polling()
