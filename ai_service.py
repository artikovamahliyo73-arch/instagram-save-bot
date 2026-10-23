import os
import asyncio
import logging
from typing import Dict, List
import aiohttp

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Foydalanuvchilar suhbat tarixi: user_id -> [ {"role": "user"|"assistant", "content": "..."}, ... ]
USER_HISTORIES: Dict[int, List[Dict[str, str]]] = {}

# Gemini sozlamalari
_gemini_model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-3.8-flash")
        logger.info("Google Gemini 3.8 Flash AI muvaffaqiyatli ulandi.")
    except Exception as e:
        logger.error(f"Gemini AI ni sozlashda xatolik: {e}")


def clear_history(user_id: int):
    """
    Foydalanuvchining AI bilan suhbat tarixini tozalash
    """
    USER_HISTORIES.pop(user_id, None)


async def _ask_gemini(user_id: int, prompt: str) -> str:
    """
    Google Gemini 1.5 Flash orqali javob olish
    """
    system_instruction = (
        "Sen Telegram bot ichidagi aqlli va do'stona AI yordamchisan. "
        "Foydalanuvchining savollariga o'zbek tilida aniq, tushunarli va muloyim javob ber. "
        "Javoblarni chiroyli formatda taqdim et."
    )
    history = USER_HISTORIES.setdefault(user_id, [])

    # Gemini formati
    gemini_history = []
    for msg in history[-6:]:  # Oxirgi 6 ta xabar
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    def sync_gemini_call():
        chat = _gemini_model.start_chat(history=gemini_history)
        response = chat.send_message(f"[Tizim ko'rsatmasi: {system_instruction}]\nFoydalanuvchi: {prompt}")
        return response.text

    return await asyncio.to_thread(sync_gemini_call)


async def _ask_free_ai(user_id: int, prompt: str) -> str:
    """
    Bepul AI provayderi (API key talab qilinmaydi)
    """
    system_prompt = (
        "Sen aqlli, bilimdon va samimiy AI yordamchisan. "
        "Foydalanuvchining savollariga o'zbek tilida aniq va to'liq javob ber."
    )
    history = USER_HISTORIES.setdefault(user_id, [])
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-6:]:
        messages.append(msg)
    messages.append({"role": "user", "content": prompt})

    payload = {
        "messages": messages,
        "model": "openai",
        "jsonMode": False
    }

    url = "https://text.pollinations.ai/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=25)) as resp:
            if resp.status == 200:
                text = await resp.text()
                if text and "Free limit reached" not in text:
                    return text.strip()

    # Agar limit yoki xatolik bo'lsa, muqobil model bilan sinab ko'ramiz
    fallback_url = f"https://text.pollinations.ai/{prompt}?system={system_prompt}"
    async with aiohttp.ClientSession() as session:
        async with session.get(fallback_url, headers=headers, timeout=aiohttp.ClientTimeout(total=25)) as resp:
            if resp.status == 200:
                return (await resp.text()).strip()

    raise RuntimeError("AI xizmatiga ulanib bo'lmadi. Iltimos, birozdan so'ng qayta urinib ko'ring.")


async def get_ai_response(user_id: int, prompt: str) -> str:
    """
    Foydalanuvchi savoliga AI dan javob olish
    """
    prompt = prompt.strip()
    if not prompt:
        return "Iltimos, biror savol yoki xabar yozing."

    # Tarixni olish
    history = USER_HISTORIES.setdefault(user_id, [])

    response_text = ""
    # 1. Agar GEMINI_API_KEY bo'lsa, birinchi o'rinda undan foydalanamiz
    if _gemini_model:
        try:
            response_text = await _ask_gemini(user_id, prompt)
        except Exception as e:
            logger.warning(f"Gemini xatosi, bepul AI ga o'tmoqda: {e}")

    # 2. Agar Gemini bo'lmasa yoki xato bersa, bepul AI dan foydalanamiz
    if not response_text:
        try:
            response_text = await _ask_free_ai(user_id, prompt)
        except Exception as e:
            logger.error(f"Bepul AI xatosi: {e}")
            return "Hozirda AI xizmatida yuqori yuklanish kuzatilmoqda. Iltimos, bir necha soniyadan so'ng qayta urinib ko'ring."

    # Tarixga qo'shish (oxirgi 10 ta xabar saqlanadi)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response_text})
    if len(history) > 10:
        USER_HISTORIES[user_id] = history[-10:]

    return response_text
