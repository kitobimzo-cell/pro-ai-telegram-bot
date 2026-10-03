import os
from google import genai
from google.genai import types
from PIL import Image
import database

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SYSTEM_INSTRUCTION = """
Siz Telegram guruhlari va shaxsiy chatingiz uchun o'ta aqlli, xushmuomala hamda professional sun'iy intellekt yordamchisisiz.
- Javoblarni doimo aniq, tushunarli va chiroyli formatlangan holda bering.
- Agar foydalanuvchi do'stona murojaat qilsa, samimiy javob bering.
- Guruhlarda ortiqcha uzun va zerikarli matnlardan qoching.
"""

def generate_ai_response(chat_id, text, image_path=None):
    if not client:
        return "Xato: GEMINI_API_KEY o'rnatilmagan!"
    
    try:
        # Rasm tahlili (Multimodal)
        if image_path:
            img = Image.open(image_path)
            prompt = text if text else "Ushbu rasmni batafsil tahlil qiling va tavsiflang."
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[img, prompt],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )
            return response.text

        # Matnli suhbat (Xotira bilan)
        history = database.get_chat_history(chat_id, limit=6)
        database.add_message(chat_id, "user", text)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history + [{"role": "user", "parts": [{"text": text}]}],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        ai_reply = response.text
        database.add_message(chat_id, "model", ai_reply)
        return ai_reply

    except Exception as e:
        return f"AI bilan ulanishda xatolik: {e}"
