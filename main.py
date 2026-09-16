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

# قاموس لتخزين آخر ملف أرسله المستخدم مؤقتاً لحين طلب تحليله أو تعديله
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

        # 1. التقاط الصور المرفقة وحفظها في الذاكرة المؤقتة للمستخدم
        if message.photo:
            photo = message.photo[-1]
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            mime_type = "image/jpeg"
            user_last_file[user_id] = {"data": bytes(file_bytes), "mime_type": mime_type}
            await message.reply_text("📥 تم استلام الصورة بنجاح! أنا بانتظار أمرك (مثل: حلل الصورة، أو عدل عليها...).")
            return

        # 2. التقاط مستندات PDF أو الملفات وحفظها مؤقتاً
        elif message.document:
            file_obj = await context.bot.get_file(message.document.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            mime_type = message.document.mime_type or "application/pdf"
            user_last_file[user_id] = {"data": bytes(file_bytes), "mime_type": mime_type}
            await message.reply_text("📥 تم استلام الملف (PDF) بنجاح! تفضل بأمرني بما تريد فعله به (تليخيص، تحليل، استخراج...).")
            return

        # 3. التقاط الفيديوهات أو الصوتيات وحفظها مؤقتاً
        elif message.video or message.audio or message.effective_attachment:
            attachment = message.video or message.audio or message.effective_attachment
            if hasattr(attachment, 'file_id'):
                file_obj = await context.bot.get_file(attachment.file_id)
                file_bytes = await file_obj.download_as_bytearray()
                mime_type = getattr(attachment, 'mime_type', 'video/mp4')
                user_last_file[user_id] = {"data": bytes(file_bytes), "mime_type": mime_type}
                await message.reply_text("📥 تم استلام الفيديو بنجاح! اكتب لي الآن أمرك (مثل: حلله، استخرج أفكاره...).")
                return

        # 4. إذا أرسل المستخدم نصاً (مثل "حلله" أو "ما رأيك") بعد إرسال الملف
        if user_text:
            contents = [user_text]
            
            # التحقق إذا كان هناك ملف مرفق مسبقاً في الذاكرة المؤقتة لهذا المستخدم
            if user_id in user_last_file:
                contents.append({
                    "mime_type": user_last_file[user_id]["mime_type"],
                    "data": user_last_file[user_id]["data"]
                })

            # إرسال الطلب لنموذج gemini-3.6-flash
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=contents,
                config={
                    'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. تحلل بدقة فائقة الملفات، الصور، والفيديوهات المستلمة وتجيب باحترافية.'
                }
            )
            
            await message.reply_text(response.text)
            
    except Exception as e:
        await message.reply_text(f"خطأ تقني أثناء معالجة الطلب: {e}")

def main():
    t = threading.Thread(target=run_health_check)
    t.daemon = True
    t.start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # فلتر شامل لالتقاط كل أنواع الرسائل والملفات
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.ATTACHMENT) & (~filters.COMMAND), handle_message))
    
    print("Bot is polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
