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
        # 1. إذا أرسل المستخدم صورة (سواء مع تعليق أو بدون)
        if message.photo:
            photo = message.photo[-1]
            file_obj = await context.bot.get_file(photo.file_id)
            file_bytes = await file_obj.download_as_bytearray()
            
            # حفظ الصورة في ذاكرة المستخدم المؤقتة
            context.user_data['last_image'] = bytes(file_bytes)
            
            # إذا كتب نصاً مع الصورة مباشرة، نقوم بتحليلها فوراً
            if user_text:
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[
                        user_text,
                        {"mime_type": "image/jpeg", "data": bytes(file_bytes)}
                    ],
                    config={'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. تحلل الصور بدقة فائقة.'}
                )
                await message.reply_text(response.text)
            else:
                await message.reply_text("📥 تم استلام الصورة بنجاح! اكتب الآن أمرك (مثل: حلل الصورة) وسأقوم بذلك فوراً.")
            return

        # 2. إذا أرسل المستخدم نصاً (مثل "حلل الصورة")
        if user_text:
            # التحقق مما إذا كانت هناك صورة محفوظة مسبقاً في ذاكرته
            if 'last_image' in context.user_data:
                image_bytes = context.user_data['last_image']
                
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[
                        user_text,
                        {"mime_type": "image/jpeg", "data": image_bytes}
                    ],
                    config={'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا. تحلل الصور بدقة فائقة.'}
                )
                await message.reply_text(response.text)
                return
            else:
                # إذا لم تكن هناك صورة محفوظة، يرد رد عادي
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[user_text],
                    config={'system_instruction': 'أنت المارد الأزرق 🧞، مساعد ذكي لطلاب الجامعات في سوريا.'}
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
