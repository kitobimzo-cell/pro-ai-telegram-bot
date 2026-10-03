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

threading.Thread(target=run_flask, daemon=True).start()

database.init_db()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None

GREETING_WORDS = [
    "salom", "салом", "salom hammaga", "салом хаммага", 
    "xayrli tong", "хайрли тонг", "xayrli kun", "хайрли кун", 
    "xayrli kech", "хайрли кеч", "xayrli tun", "хайрли тун", 
    "privet", "привет", "assalomu alaykum", "ассалому алайкум"
]

if bot:
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Webhook error: {e}")

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        user_name = message.from_user.first_name or "Foydalanuvchi"
        database.save_user(message.chat.id, message.from_user.id, message.from_user.username, user_name)
        bot.reply_to(
            message, 
            f"Salom, {user_name}! 😊\nMen guruh va shaxsiy chatlar uchun sun'iy intellekt yordamchisiman.\n\n"
            "💬 Menga savol bering yoki rasm yuboring!"
        )

    # Rasmlar bilan ishlash
    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        user_name = message.from_user.first_name or "Foydalanuvchi"
        user_id = message.from_user.id
        database.save_user(message.chat.id, user_id, message.from_user.username, user_name)
        
        try:
            msg = bot.reply_to(message, "🔍 Rasm tahlil qilinmoqda, kuting...")
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            temp_path = f"temp_{message.message_id}.jpg"
            with open(temp_path, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            caption = message.caption if message.caption else ""
            reply_text = ai_engine.generate_ai_response(
                message.chat.id,
                user_id,
                user_name,
                caption, 
                image_path=temp_path
            )
            
            bot.edit_message_text(reply_text, message.chat.id, msg.message_id)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            bot.reply_to(message, f"Rasm tahlilida xatolik: {e}")

    # Matnli xabarlar
    @bot.message_handler(func=lambda message: True)
    def handle_text(message):
        if not message.text:
            return

        user_name = message.from_user.first_name or "Foydalanuvchi"
        user_id = message.from_user.id
        database.save_user(message.chat.id, user_id, message.from_user.username, user_name)
        
        text_lower = message.text.strip().lower()
        is_greeting = any(word in text_lower for word in GREETING_WORDS)
        
        if message.chat.type in ['group', 'supergroup']:
            bot_info = bot.get_me()
            is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id
            is_mentioned = f"@{bot_info.username}" in message.text
            
            # Guruhda oddiy salomlashuv bo'lsa
            if is_greeting and not (is_reply_to_bot or is_mentioned):
                bot.send_chat_action(message.chat.id, 'typing')
                prompt = f"Foydalanuvchi guruhga ushbu xabarni yozdi: '{message.text}'. Unga ismini aytib ({user_name}), juda xushmuomala va samimiy tarzda, chiroyli smayliklar (😊, 👋, ✨) bilan qisqa javob bering."
                reply_text = ai_engine.generate_ai_response(message.chat.id, user_id, user_name, prompt)
                bot.reply_to(message, reply_text)
                return

            if not (is_reply_to_bot or is_mentioned):
                return

        bot.send_chat_action(message.chat.id, 'typing')
        reply_text = ai_engine.generate_ai_response(message.chat.id, user_id, user_name, message.text)
        
        bot.reply_to(message, reply_text)

    print("Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
else:
    print("XATO: BOT_TOKEN o'rnatilmagan!")
