import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# قراءة المفاتيح من بيئة العمل
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# إعداد نموذج جيميناي مع شخصية المساعد لطلاب سوريا
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="أنت المارد الأزرق 🧞، مساعدك الذكي لطلاب الجامعات في سوريا. أجب بأسلوب ذكي وودود ودقيق."
)

# خادم وهمي لإبقاء الخدمة نشطة 24/7 على Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active 24/7!")

def run_health_check():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

# دالة التعامل مع رسائل المستخدم عبر تليجرام
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    try:
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
        except Exception as e:
    print(f"DETAILED AI ERROR: {e}")  # طباعة الخطأ بالحرف في السجلات
    await update.message.reply_text(f"خطأ تقني: {e}") # إرسال الخطأ لتراه مباشرة في تليجرام


def main():
    # تشغيل خادم الفحص الصحي في الخلفية
    t = threading.Thread(target=run_health_check)
    t.daemon = True
    t.start()

    # تشغيل بوت تليجرام
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
