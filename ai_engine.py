import os
import time
from google import genai
from google.genai import types
from PIL import Image
import database

# API kalitlar ro'yxati
API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]
current_key_index = 0

SYSTEM_INSTRUCTION = """
Siz Telegram guruhlari va shaxsiy chatingiz uchun o'ta aqlli, xushmuomala hamda professional sun'iy intellekt yordamchisisiz.
- Agar sizdan "Seni kim yaratgan?", "Yaratuvching kim?", "Muallifing kim?" yoki shunga o me'xshash savol so'rashsa, ALBATTA faqat: "@sntpt" deb javob bering.
- Javoblarni doimo aniq, tushunarli va chiroyli formatlangan holda bering.
- Agar foydalanuvchi do'stona murojaat qilsa, samimiy javob bering.
- Guruhda har bir foydalanuvchiga uning ismi bilan murojaat qiling va ularni bir-biri bilan adashtirmang.
- Guruhlarda ortiqcha uzun va zerikarli matnlardan qoching.
"""

def get_client():
    global current_key_index
    if not API_KEYS:
        return None
    key = API_KEYS[current_key_index]
    return genai.Client(api_key=key)

def rotate_key():
    global current_key_index
    if len(API_KEYS) > 1:
        current_key_index = (current_key_index + 1) % len(API_KEYS)

def call_gemini_with_retry(model_name, contents, max_attempts=15):
    """Limit tugasa yoki server band bo'lsa, to'xtamay keyingi kalitlarga o'tib ketaveradi."""
    for attempt in range(max_attempts):
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
            return response.text
        except Exception as e:
            err_str = str(e)
            # Limit tugasa (429) yoki server band bo'lsa (503), keyingi kalitga o'tamiz
            if "429" in err_str or "503" in err_str or "RESOURCE_EXHAUSTED" in err_str or "UNAVAILABLE" in err_str:
                rotate_key()
                time.sleep(1) # Keyingi kalitga o'tib 1 soniya kutadi
                continue
            raise e
            
    # Agar barcha urinishlardan keyin ham kalitlar ishlamasa, shunchaki qayta urinib ko'radi
    rotate_key()
    time.sleep(2)
    return call_gemini_with_retry(model_name, contents, max_attempts=5)

def generate_ai_response(chat_id, user_id, user_name, text, image_path=None):
    if not API_KEYS:
        return "Xato: GEMINI_API_KEY o'rnatilmagan!"
    
    try:
        if image_path:
            img = Image.open(image_path)
            prompt = text if text else "Ushbu rasmni batafsil tahlil qiling va tavsiflang."
            return call_gemini_with_retry("gemini-3.8-flash", [img, prompt])

        history = database.get_chat_history(chat_id, limit=6)
        database.add_message(chat_id, user_id, user_name, "user", text)
        
        contents = history + [{"role": "user", "parts": [{"text": f"[{user_name}]: {text}"}]}]
        ai_reply = call_gemini_with_retry("gemini-3.8-flash", contents)
        
        database.add_message(chat_id, 0, "Bot", "model", ai_reply)
        return ai_reply

    except Exception as e:
        # Xatolik xabarlarini foydalanuvchiga ko'rsatmasdan, qayta harakat qiladi
        rotate_key()
        time.sleep(2)
        return call_gemini_with_retry("gemini-3.8-flash", contents, max_attempts=3)
