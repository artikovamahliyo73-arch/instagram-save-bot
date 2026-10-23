# 📥 Instagram, YouTube & AI Chat Telegram Bot

Instagram (Reels, Post) va YouTube (Shorts, Video) videolarini tezkor yuklab beruvchi hamda **Sun'iy Intellekt (AI Chat)** bilan to'liq suhbatlashish imkonini beruvchi ko'p funksiyali Telegram bot.

---

## 🚀 Asosiy imkoniyatlari

- 🤖 **AI Chat bo'limi:** Foydalanuvchilar sun'iy intellekt bilan o'zbek tilida erkin suhbatlasha oladi, savollariga javob oladi. Suhbat xotirasi saqlanadi.
- ⚡️ **Instagram & YouTube yuklovchi:**
  - 📸 **Instagram:** Reels, postlar va videolar.
  - 🔴 **YouTube:** YouTube Shorts va 720p HD videolari.
  - 🚀 **aria2c:** 8 ta parallel oqim orqali maksimal yuklash tezligi.
- 🔄 **Asinxron ishlash:** Bot `aiogram 3.x` va `asyncio` asosida qurilgan.
- 🧹 **Avtomatik tozalash:** Yuklangan videolar Telegramga jo'natilgach, server diskini band qilmasligi uchun darhol o'chiriladi.

---

## 📁 Loyiha tarkibi

```
instagram/
│
├── bot.py             # Asosiy Telegram bot kodi, menyular va handlerlar
├── ai_service.py      # Sun'iy intellekt (AI Chat) xizmati va suhbat xotirasi
├── downloader.py      # Instagram va YouTube yuklab oluvchi modul (yt-dlp + aria2)
├── config.py          # Sozlamalar va muhit o'zgaruvchilari
├── requirements.txt   # Kerakli Python kutubxonalari
├── run.bat            # Windows uchun bitta bosishda ishga tushirish fayli
├── .env.example       # Sozlamalar namunasi
├── .env               # Telegram Bot tokeningiz va sozlamalar
└── README.md          # Qo'llanma
```

---

## 🛠 O'rnatish va Ishga tushirish

### 1-qadam: Bot tokenini olish
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrug'ini yuboring va botingizga nom hamda username bering.
3. `@BotFather` sizga quyidagiga o'xshash token beradi:
   `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`

### 2-qadam: Tokenni sozlash
Loyihaning `.env` faylini oching va bot tokeningizni kiriting:
```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

### 3-qadam: Botni ishga tushirish

#### Usul 1 (Eng oson - Windows uchun):
Papka ichidagi `run.bat` fayliga sichqoncha bilan ikki marta bosing. U avtomatik tarzda barcha kutubxonalarni tekshirib, botni ishga tushiradi!

#### Usul 2 (Buyruqlar paneli orqali):
```bash
# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Botni yurgizish
python bot.py
```

---

## 💡 Foydalanish bo'yicha ko'rsatma

1. Telegramda o'z botingizga kiring va `/start` bosing.
2. Instagram'dan istalgan video havolasini botga yuboring:
   *Masalan:* `https://www.instagram.com/reel/C8xxxxxxxx/`
3. Bot videoni yuklab, sizga video ko'rinishida yuboradi.
