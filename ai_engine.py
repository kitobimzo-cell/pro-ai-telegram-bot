import os
import time
from google import genai
from google.genai import types
from PIL import Image
import database

# API kalitlarni Environment Variables'dan yuklab olamiz
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
    """Hozirgi aktiv API kalit bilan mijoz yaratadi"""
    global current_key_index
    if not API_KEYS:
        return None
    key = API_KEYS[current_key_index]
    return genai.Client(api_key=key, http_options={'timeout': 15.0})

def rotate_key():
    """Avtomatik ravishda keyingi API kalitga o'tadi"""
    global current_key_index
    if len(API_KEYS) > 1:
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        print(f"🔄 API Kalit almashdi! Yangi kalit indeksi: {current_key_index + 1}/{len(API_KEYS)}")

def call_gemini_with_retry(contents):
    """
    Limit (429) yoki xatolik bo'lsa, avtomatik keyingi API kalitga o'tib
    ishlaydigan javob olguncha qayta urinadi.
    """
    model_name = "gemini-3.8-flash"
    max_attempts = len(API_KEYS) * 2 if API_KEYS else 3
    
    for attempt in range(max_attempts):
        client = get_client()
        if not client:
            return "Xato: GEMINI_API_KEY Environment Variables'da topilmadi!"
        
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
            err_msg = str(e)
            print(f"⚠️ Xatolik yuz berdi (Kalit {current_key_index + 1}): {err_msg[:120]}")
            
            # API limit tugaganini ko'rsatuvchi kalit so'zlar
            limit_errors = ["429", "RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED", "UNAVAILABLE", "503", "API_KEY_INVALID"]
            
            if any(err_code in err_msg for err_code in limit_errors):
                rotate_key()  # Limit tugagani uchun keyingi kalitga o'tamiz
                time.sleep(0.5)  # Kichik kutilma bilan darhol qayta harakat qiladi
            else:
                # Boshqa kutilmagan xatolik bo'lsa ham kalitni almashtirib ko'ramiz
                rotate_key()
                time.sleep(1)

    return "Hozirda barcha API kalitlarda kunlik limit tugagan. Birozdan so'ng qayta yozib ko'ring."

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
        rotate_key()
        return "Tizimda kichik uzilish bo'ldi. Qayta yuborib ko'ring."
