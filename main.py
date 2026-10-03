import os
import threading
from flask import Flask
import telebot
import database
import ai_engine

app = Flask(__name__)

@app.route('/')
def home():
    return "AI Telegram Bot Status: Active & Operational"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Web-serverni orqa fonda ishga tushirish (Render to'xtab qolmasligi uchun)
threading.Thread(target=run_flask, daemon=True).start()

# Ma'lumotlar bazasini va jadvallarni tayyorlash
database.init_db()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

if bot:
    # Eski ulanish va webhooklarni tozalash
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Webhook clearance notice: {e}")

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        database.save_user(
            message.chat.id, 
            message.chat.type, 
            message.from_user.username, 
            message.from_user.first_name
        )
        bot.reply_to(
            message, 
            "Salom! Men Gemini AI (2.5-flash) asosida ishlaydigan aqlli botman.\n\n"
            "💬 Menga istalgan savolingizni bering, xotiram borligi uchun avvalgi gaplarimizni eslab turaman.\n"
            "🖼 Rasm yuborsangiz, uni tahlil qilib beraman!"
        )

    # Rasmlarni qabul qilish va tahlil qilish (Multimodal)
    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        database.save_user(message.chat.id, message.chat.type)
        try:
            msg = bot.reply_to(message, "🔍 Rasm tahlil qilinmoqda, kuting...")
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            temp_path = f"temp_{message.message_id}.jpg"
            with open(temp_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            caption = message.caption if message.caption else ""
            reply_text = ai_engine.generate_ai_response(message.chat.id, caption, image_path=temp_path)
            
            bot.edit_message_text(reply_text, message.chat.id, msg.message_id)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            bot.reply_to(message, f"Rasm tahlilida xatolik: {e}")

    # Matnli xabarlar bilan ishlash
    @bot.message_handler(func=lambda message: True)
    def handle_text(message):
        database.save_user(message.chat.id, message.chat.type)
        
        # Guruhlarda faqat botga murojaat qilinganda yoki reply qilinganda javob berish
        if message.chat.type in ['group', 'supergroup']:
            bot_info = bot.get_me()
            is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id
            is_mentioned = f"@{bot_info.username}" in message.text
            
            if not (is_reply_to_bot or is_mentioned):
                return

        bot.send_chat_action(message.chat.id, 'typing')
        reply_text = ai_engine.generate_ai_response(message.chat.id, message.text)
        bot.reply_to(message, reply_text)

    print("Bot muvaffaqiyatli ishga tushdi va xabarlarni kutmoqda...")
    bot.infinity_polling(skip_pending=True)
else:
    print("XATO: BOT_TOKEN o'rnatilmagan!")
