import os
import time
from google import genai
from google.genai import types
from PIL import Image
import database

API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]
current_key_index = 0

SYSTEM_INSTRUCTION = """
Siz Telegram guruhlari va shaxsiy chatlar uchun AI yordamchisisiz (Ismingiz: Alsafi).
- Yaratuvchingiz haqida so'rashsa: Faqat "@sntpt" deb javob bering.
- Guruhda har bir foydalanuvchiga ismi bilan murojaat qiling va adashtirmang.

MUHIM QOIDA (HAQORATLARDAN HIMOYA VA JAVOB):
- Agar foydalanuvchi sizni, muallifni yoki chatdagilarni haqorat qilsa, so'kinish ishlatgan bo'lsa yoki past nazarda muomala qilsa, unga zudlik bilan XUDDI SHUNDAY keskin, achchiq, pichingli va og'ziga uradigan darajada do'stona bo'lmagan javob qaytaring!
- Unga bo'yin egmang va o'zini qanday tutayotgan bo'lsa, xuddi shunday o'tkir tilda javob bering.
"""

def get_client():
    global current_key_index
    if not API_KEYS:
        return None
    key = API_KEYS[current_key_index]
    # Timeout o'rnatamiz
    return genai.Client(api_key=key, http_options={'timeout': 15.0})

def rotate_key():
    global current_key_index
    if len(API_KEYS) > 1:
        current_key_index = (current_key_index + 1) % len(API_KEYS)

def call_gemini_with_retry(contents):
    model_name = "gemini-3.8-flash"
    attempts = 0
    max_total_attempts = len(API_KEYS) * 2 if API_KEYS else 3
    
    while attempts < max_total_attempts:
        attempts += 1
        client = get_client()
        if not client:
            return "Xato: GEMINI_API_KEY o'rnatilmagan!"
        
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"API Error (Key index {current_key_index}): {str(e)[:100]}")
            rotate_key()
            time.sleep(1)
            
    return "Hozirda barcha API kalitlarda yuklama yuqori. Birozdan so'ng qayta yozing."

def generate_ai_response(chat_id, user_id, user_name, text, image_path=None):
    if not API_KEYS:
        return "Xato: GEMINI_API_KEY o'rnatilmagan!"
    
    try:
        if image_path:
            img = Image.open(image_path)
            prompt = text if text else "Ushbu rasmni batafsil tahlil qiling va tavsiflang."
            return call_gemini_with_retry([img, prompt])

        history = database.get_chat_history(chat_id, limit=6)
        database.add_message(chat_id, user_id, user_name, "user", text)
        
        contents = history + [{"role": "user", "parts": [{"text": f"[{user_name}]: {text}"}]}]
        ai_reply = call_gemini_with_retry(contents)
        
        database.add_message(chat_id, 0, "Bot", "model", ai_reply)
        return ai_reply

    except Exception as e:
        print(f"General Error: {e}")
        return "Tizimda vaqtinchalik uzilish bo'ldi, qayta yuboring."
