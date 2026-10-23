import re
import sys
import asyncio
import logging

# Windows konsolida emojilar va belgilarni to'g'ri chiqarish (CP1251 / UTF-8 muammosi uchun)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.enums import ChatAction

from config import BOT_TOKEN
from downloader import download_media, cleanup_file
from ai_service import get_ai_response, clear_history

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Instagram havolalarini aniqlash uchun regex
INSTAGRAM_REGEX = re.compile(
    r'(https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv|share/[a-zA-Z0-9]+)/[A-Za-z0-9_\-\.]+/?(?:\?[^\s]*)?)'
)

# YouTube va YouTube Shorts havolalarini aniqlash uchun regex
YOUTUBE_REGEX = re.compile(
    r'(https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/|live/|embed/)[A-Za-z0-9_\-]+|youtu\.be/[A-Za-z0-9_\-]+)(?:[^\s]*)?)'
)

# AI Chat holatidagi foydalanuvchilar ID ro'yxati
AI_CHAT_USERS = set()

# Dispatcher yaratish
dp = Dispatcher()
cached_bot_username = "instagrammssaqlabot"


# --- Klaviaturalar (Keyboards) ---
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu tugmalari"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤖 AI Chat bilan suhbat")],
            [KeyboardButton(text="📥 Video Yuklash"), KeyboardButton(text="ℹ️ Yordam")]
        ],
        resize_keyboard=True
    )


def get_ai_keyboard() -> ReplyKeyboardMarkup:
    """AI Chat bo'limi tugmalari"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧹 Suhbatni tozalash")],
            [KeyboardButton(text="❌ AI Chatdan chiqish")]
        ],
        resize_keyboard=True
    )


# --- Buyruqlar (Commands) ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    /start buyrug'i uchun handler
    """
    first_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    text = (
        f"👋 Assalomu alaykum, <b>{first_name}</b>!\n\n"
        "Men ko'p funksiyali botman:\n"
        "• 📥 <b>Instagram & YouTube</b> dan video yuklab beraman.\n"
        "• 🤖 <b>AI Chat:</b> Sun'iy intellekt bilan istalgan mavzuda suhbatlashishingiz mumkin.\n\n"
        "Quyidagi tugmalardan birini tanlang yoki to'g'ridan-to'g'ri video havolasini yuboring!"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())


@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: types.Message):
    """
    /help buyrug'i uchun handler
    """
    text = (
        "💡 <b>Bot imkoniyatlari:</b>\n\n"
        "1. 📥 <b>Video yuklash:</b>\n"
        "   - Instagram (Reels, Post) yoki YouTube (Shorts, Video) havolasini shunchaki botga yuboring.\n"
        "   - Bot uni yuqori sifatda video qilib jo'natadi.\n\n"
        "2. 🤖 <b>AI Chat:</b>\n"
        "   - <b>'🤖 AI Chat bilan suhbat'</b> tugmasini bosing va istalgan savolingizni yozing.\n"
        "   - AI sizga o'zbek tilida batafsil javob beradi."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())


@dp.message(F.text == "📥 Video Yuklash")
async def btn_video_guide(message: types.Message):
    text = (
        "📥 <b>Video yuklash bo'yicha ko'rsatma:</b>\n\n"
        "1. Instagram yoki YouTube ilovasidan videoni oching.\n"
        "2. <b>Ulashish (Share)</b> -> <b>Havolani nusxalash (Copy Link)</b> ni bosing.\n"
        "3. Nusxalangan havolani shu yerga yuboring.\n\n"
        "⚡️ Bot darhol videoni yuklab beradi!"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🤖 AI Chat bilan suhbat")
async def enter_ai_chat(message: types.Message):
    user_id = message.from_user.id
    AI_CHAT_USERS.add(user_id)
    text = (
        "🤖 <b>AI Chat bo'limiga xush kelibsiz!</b>\n\n"
        "Menga istalgan savolingizni yozing yoki suhbatlashing. Men sun'iy intellekt yordamida javob beraman!\n\n"
        "<i>Chiqish uchun '❌ AI Chatdan chiqish' tugmasini bosing.</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_ai_keyboard())


@dp.message(F.text == "❌ AI Chatdan chiqish")
async def exit_ai_chat(message: types.Message):
    user_id = message.from_user.id
    AI_CHAT_USERS.discard(user_id)
    text = "🔙 <b>AI Chatdan chiqdingiz.</b>\nAsosiy menyuga qaytdingiz."
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())


@dp.message(F.text == "🧹 Suhbatni tozalash")
async def clear_ai_chat(message: types.Message):
    user_id = message.from_user.id
    clear_history(user_id)
    text = "🧹 <b>Suhbat xotirasi tozalandi!</b>\nYangi savolingizni yozishingiz mumkin."
    await message.answer(text, parse_mode="HTML", reply_markup=get_ai_keyboard())


# --- Asosiy xabar qabul qiluvchi handler ---
@dp.message(F.text)
async def handle_message(message: types.Message, bot: Bot):
    text = message.text or ""
    user_id = message.from_user.id

    # 1. Instagram yoki YouTube havolasi bormi? (Har doim ustuvor!)
    match = INSTAGRAM_REGEX.search(text) or YOUTUBE_REGEX.search(text)
    if match:
        url = match.group(0)
        is_yt = "youtube.com" in url.lower() or "youtu.be" in url.lower()
        platform_name = "YouTube" if is_yt else "Instagram"
        platform_icon = "🔴" if is_yt else "📸"

        status_msg = await message.reply(
            f"⏳ <b>{platform_icon} {platform_name} videosi yuklanmoqda...</b>\n<i>Iltimos, biroz kuting.</i>",
            parse_mode="HTML"
        )

        file_path = None
        try:
            asyncio.create_task(bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO))

            media_data = await download_media(url)
            file_path = media_data.get('file_path')

            if not file_path:
                raise FileNotFoundError("Video fayli topilmadi.")

            title = media_data.get('title', f'{platform_name} Video')
            uploader = media_data.get('uploader')

            caption_lines = [f"{platform_icon} <b>{title}</b>"]
            if uploader:
                caption_lines.append(f"👤 <i>Kanal/Muallif:</i> {uploader}")
            caption_lines.append(f"\n📥 <i>Yuklab berildi: @{cached_bot_username}</i>")

            caption = "\n".join(caption_lines)
            if len(caption) > 1024:
                caption = caption[:1020] + "..."

            video_input = FSInputFile(file_path)

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"🔗 {platform_name} da ko'rish", url=url)]
                ]
            )

            await message.answer_video(
                video=video_input,
                caption=caption,
                parse_mode="HTML",
                duration=media_data.get('duration') or 0,
                width=media_data.get('width'),
                height=media_data.get('height'),
                supports_streaming=True,
                reply_markup=keyboard
            )

            try:
                await status_msg.delete()
            except Exception:
                pass

        except PermissionError as pe:
            await status_msg.edit_text(f"❌ <b>Xatolik:</b> {pe}", parse_mode="HTML")
        except ValueError as ve:
            await status_msg.edit_text(f"⚠️ <b>Xatolik:</b> {ve}", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Xatolik yuz berdi: {e}", exc_info=True)
            await status_msg.edit_text(
                f"❌ <b>Kechirasiz, {platform_name} videosini yuklab olishning iloji bo'lmadi.</b>\n"
                "Havola to'g'riligini yoki video ommaga ochiq (public) ekanligini tekshiring.",
                parse_mode="HTML"
            )
        finally:
            if file_path:
                cleanup_file(file_path)
        return

    # 2. Agar foydalanuvchi AI Chat holatida bo'lsa
    if user_id in AI_CHAT_USERS:
        # Telegram chatida 'yozmoqda...' (typing) statusi
        asyncio.create_task(bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING))

        # AI dan javob olamiz
        ai_reply = await get_ai_response(user_id, text)

        # Xabarni yuboramiz
        try:
            await message.answer(ai_reply, parse_mode="Markdown")
        except Exception:
            await message.answer(ai_reply)
        return

    # 3. Agar oddiy xabar bo'lsa va AI rejimida bo'lmasa
    if any(domain in text.lower() for domain in ["instagram.com", "youtube.com", "youtu.be"]):
        await message.reply("⚠️ Havola noto'g'ri ko'rinmoqda. Iltimos, to'liq Instagram yoki YouTube havolasini yuboring.")
    else:
        info_text = (
            "📥 Video yuklash uchun Instagram yoki YouTube havolasini yuboring.\n\n"
            "🤖 Sun'iy intellekt bilan suhbatlashish uchun <b>'🤖 AI Chat bilan suhbat'</b> tugmasini bosing!"
        )
        await message.reply(info_text, parse_mode="HTML", reply_markup=get_main_keyboard())


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n" + "=" * 60)
        print("❌ XATOLIK: BOT_TOKEN ko'rsatilmagan!")
        print("1. Telegramda @BotFather ga kiring va yangi bot yarating.")
        print("2. Berilgan tokenni .env faylidagi BOT_TOKEN o'rniga yozing.")
        print("   Masalan: BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
        print("=" * 60 + "\n")
        return

    bot = Bot(token=BOT_TOKEN)
    me = await bot.get_me()
    global cached_bot_username
    cached_bot_username = me.username
    print(f"✅ Bot muvaffaqiyatli ishga tushdi: @{me.username}")
    print("Xabarlar kutilmoqda (Instagram, YouTube & AI Chat)...")

    # Eski xabarlarni o'tkazib yuborish
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
