@echo off
chcp 65001 > nul
title Instagram Video Telegram Bot

echo ========================================================
echo        Instagram Video Telegram Bot Ishga Tushmoqda
echo ========================================================

REM Virtual muhitni tekshirish
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Virtual muhit yaratilmoqda (.venv)...
    python -m venv .venv
)

REM Kutubxonalarni o'rnatish
echo [2/3] Kerakli kutubxonalar tekshirilmoqda...
.venv\Scripts\pip install -r requirements.txt --quiet

REM .env faylini tekshirish
if not exist ".env" (
    echo .env fayli topilmadi, .env.example dan nusxalanmoqda...
    copy .env.example .env > nul
)

echo [3/3] Bot ishga tushirilmoqda...
echo.
.venv\Scripts\python.exe bot.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Xatolik yuz berdi! Iltimos, yuqoridagi xabarni o'qing.
)

pause
