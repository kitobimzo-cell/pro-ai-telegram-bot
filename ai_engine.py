import os
import time
from google import genai
from google.genai import types
from PIL import Image
import database

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SYSTEM_INSTRUCTION = """
Siz Telegram guruhlari va shaxsiy chatingiz uchun o'ta aqlli, xushmuomala hamda professional sun'iy intellekt yordamchisisiz.
- Agar sizdan "Seni kim yaratgan?", "Yaratuvching kim?", "Muallifing kim?" yoki shunga o'xshash savol so'rashsa, ALBATTA faqat: "@sntpt" deb javob bering.
- Javoblarni doimo aniq, tushunarli va chiroyli formatlangan holda bering.
- Agar foydalanuvchi do'stona murojaat qilsa, samimiy javob bering.
- Guruhlarda ortiqcha uzun va zerikarli matnlardan qoching.
"""

def call_gemini_with_retry(model_name, contents, max_retries=3):
    """Server band bo'lganida (503) qayta urinish mantig'i."""
    for attempt in range(max_retries):
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
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
            raise e

def generate_ai_response(chat_id, text, image_path=None):
    if not client:
        return "Xato: GEMINI_API_KEY o'rnatilmagan!"
    
    try:
        # Rasm bo'lsa (Multimodal)
        if image_path:
            img = Image.open(image_path)
            prompt = text if text else "Ushbu rasmni batafsil tahlil qiling va tavsiflang."
            return call_gemini_with_retry("gemini-3.8-flash", [img, prompt])

        # Matnli suhbat (Xotira bilan)
        history = database.get_chat_history(chat_id, limit=6)
        database.add_message(chat_id, "user", text)
        
        contents = history + [{"role": "user", "parts": [{"text": text}]}]
        ai_reply = call_gemini_with_retry("gemini-3.8-flash", contents)
        
        database.add_message(chat_id, "model", ai_reply)
        return ai_reply

    except Exception as e:
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            return "Google AI serverlari hozirda juda band. Iltimos, 1 daqiqadan so'ng qayta urinib ko'ring."
        return f"AI bilan ulanishda xatolik: {e}"
