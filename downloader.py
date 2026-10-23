import os
import sys
import uuid
import shutil
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp

from config import DOWNLOAD_DIR, COOKIES_FILE, MAX_FILE_SIZE, BASE_DIR

logger = logging.getLogger(__name__)

# Papkalar va ikkilik vositalar (binaries)
SCRIPTS_DIR = BASE_DIR / ".venv" / "Scripts"
FFMPEG_EXE = SCRIPTS_DIR / "ffmpeg.exe"
ARIA2_EXE = SCRIPTS_DIR / "aria2c.exe"

# 1. FFmpeg ni tekshirish va nusxalash
try:
    import imageio_ffmpeg
    _raw_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if os.path.exists(_raw_ffmpeg) and not FFMPEG_EXE.exists():
        shutil.copyfile(_raw_ffmpeg, str(FFMPEG_EXE))
except Exception as e:
    logger.warning(f"FFmpeg tekshirishda ogohlantirish: {e}")

# 2. aria2c ni tekshirish
HAS_ARIA2 = ARIA2_EXE.exists() or bool(shutil.which("aria2c"))

# PATH ga Scripts papkasini qo'shamiz
if str(SCRIPTS_DIR) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(SCRIPTS_DIR) + os.pathsep + os.environ.get("PATH", "")


def _sync_download(url: str) -> Dict[str, Any]:
    """
    Instagram yoki YouTube havolasidan videoni maksimal tezlikda yuklab olish
    """
    unique_id = uuid.uuid4().hex[:10]
    out_tmpl = str(DOWNLOAD_DIR / f"{unique_id}_%(id)s.%(ext)s")

    is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()
    platform_name = "YouTube" if is_youtube else "Instagram"

    # Tezlik uchun: Tayyor birlashgan MP4 (single-stream) ni birinchi navbatda olamiz!
    # Bu FFmpeg qayta ishlash vaqtini tejaydi va 3-5 barobar tezroq yuklaydi.
    if is_youtube:
        format_selector = (
            'best[height<=720][ext=mp4]/'
            'best[height<=720]/'
            'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/'
            'bestvideo[height<=720]+bestaudio/'
            'best'
        )
    else:
        # Instagram uchun tayyor MP4 birinchi o'rinda
        format_selector = (
            'best[ext=mp4]/'
            'best/'
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/'
            'bestvideo+bestaudio'
        )

    ydl_opts = {
        'format': format_selector,
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'socket_timeout': 15,
        'ffmpeg_location': str(SCRIPTS_DIR),
        # Tezlikni oshirish uchun sozlamalar:
        'http_chunk_size': 10485760,          # 10 MB bo'laklarda yuklash (CDN tezlik cheklovini aylanib o'tish)
        'concurrent_fragment_downloads': 8,   # Bir vaqtning o'zida 8 ta bo'lak yuklash
        'buffersize': 1024 * 1024,            # 1 MB bufer
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    # Agar aria2c mavjud bo'lsa, parallel 8 ta ulanish bilan yuklaymiz (maksimal tezlik)
    if HAS_ARIA2:
        ydl_opts['external_downloader'] = 'aria2c'
        ydl_opts['external_downloader_args'] = {
            'aria2c': [
                '-x', '8',                     # Bir serverga 8 ta ulanish
                '-s', '8',                     # 8 ta parallel bo'lak
                '-k', '1M',                    # Bo'lak hajmi 1MB
                '--file-allocation=none',      # Diskda joy ajratishni kutmaslik
                '--summary-interval=0',        # Ortiqcha log chiqarmaslik
                '--quiet=true'
            ]
        }

    # Agar cookies.txt fayli mavjud bo'lsa
    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        ydl_opts['cookiefile'] = str(COOKIES_FILE)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            err_msg = str(e)
            if "login" in err_msg.lower() or "private" in err_msg.lower():
                raise PermissionError(f"Ushbu {platform_name} videosi yopiq (private) yoki kirish cheklangan.")
            raise ValueError(f"{platform_name} videosini yuklab olishda xatolik yuz berdi: {err_msg}")

        if not info:
            raise ValueError(f"{platform_name} tarmog'idan ma'lumot olib bo'lmadi.")

        if 'entries' in info and info['entries']:
            entry = info['entries'][0]
        else:
            entry = info

        filename = ydl.prepare_filename(entry)
        base, _ = os.path.splitext(filename)
        mp4_path = f"{base}.mp4"

        actual_file: Optional[str] = None
        if os.path.exists(mp4_path):
            actual_file = mp4_path
        elif os.path.exists(filename):
            actual_file = filename
        else:
            matched = list(DOWNLOAD_DIR.glob(f"{unique_id}*"))
            if matched:
                actual_file = str(matched[0])

        if not actual_file or not os.path.exists(actual_file):
            raise FileNotFoundError("Yuklangan video fayli topilmadi.")

        file_size = os.path.getsize(actual_file)
        if file_size > MAX_FILE_SIZE:
            try:
                os.remove(actual_file)
            except Exception:
                pass
            raise ValueError(
                f"Video hajmi juda katta ({file_size / (1024*1024):.1f} MB). "
                f"Telegram bot faqat 50 MB gacha video yubora oladi."
            )

        title = entry.get('title') or entry.get('description') or f"{platform_name} Video"
        if title and len(title) > 200:
            title = title[:197] + "..."

        uploader = entry.get('uploader') or entry.get('channel') or ""

        return {
            'file_path': actual_file,
            'title': title,
            'platform': platform_name,
            'uploader': uploader,
            'duration': int(entry.get('duration') or 0),
            'width': entry.get('width'),
            'height': entry.get('height'),
            'filesize': file_size
        }

async def download_media(url: str) -> Dict[str, Any]:
    """
    Instagram va YouTube uchun asinxron yuklab oluvchi funksiya
    """
    return await asyncio.to_thread(_sync_download, url)

download_instagram_video = download_media

def cleanup_file(file_path: Optional[str]):
    """
    Server xotirasini band qilmaslik uchun faylni o'chirish
    """
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Faylni o'chirishda xatolik: {e}")
