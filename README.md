# Vodiy Kameralar — Buyurtma boti (backend)

Bu kichik server saytdagi "Buyurtmani rasmiylashtirish" bosilganda chekni
avtomatik ravishda sizning Telegram chatingizga yuboradi.

## 1-qadam: Bot yaratish

1. Telegram'da **@BotFather** ni oching
2. `/newbot` yozing, botga nom va username bering
3. Sizga **BOT_TOKEN** beriladi (masalan: `7123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
   — buni hech kimga bermang, bu botingizning "paroli"

## 2-qadam: O'z Chat ID'ingizni olish

1. Yaratgan botingizga Telegram'da o'zingiz `/start` deb yozing
   (Telegram qoidasiga ko'ra, bot birinchi bo'lib sizga yoza olmaydi —
   avval siz botga yozishingiz shart)
2. Brauzerda shu manzilni oching (TOKEN o'rniga o'zingiznikini qo'ying):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Chiqqan javobda `"chat":{"id":123456789,...}` qismini toping — shu raqam
   sizning **Chat ID**ingiz

Bir nechta admin (masalan siz + yordamchingiz) bo'lsa — har biri botga
`/start` yozadi, ID'larni vergul bilan ajratib yozasiz:
`111111111,222222222`

## 3-qadam: Serverni bepul joylashtirish (Render.com)

1. https://render.com da ro'yxatdan o'ting (GitHub akkaunt bilan kirish qulay)
2. Bu papkadagi fayllarni (server.py, requirements.txt) GitHub'ga yuklang
   (yangi repo yarating, masalan `vodiy-kameralar-bot`)
3. Render'da **New + → Web Service** tanlang, shu repo'ni ulang
4. Sozlamalar:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python server.py`
   - **Plan:** Free
5. **Environment** bo'limida quyidagilarni qo'shing:
   - `BOT_TOKEN` = (2-qadamdagi token)
   - `ADMIN_CHAT_IDS` = (2-qadamdagi chat ID, yoki bir nechtasi vergul bilan)
   - `ALLOWED_ORIGIN` = saytingiz manzili (masalan `https://vodiykameralar.pages.dev`),
     hozircha sinov uchun `*` qoldirsa ham bo'ladi
6. Deploy tugagach, sizga manzil beriladi, masalan:
   `https://vodiy-kameralar-bot.onrender.com`

> **Eslatma:** Render Free tarifda server 15 daqiqa ishlatilmasa "uxlab qoladi"
> va keyingi so'rovda 20-30 soniya uyg'onadi. Bu demo/kichik biznes uchun
> yetarli, lekin katta oqim bo'lsa pullik tarifga o'tish tavsiya etiladi.

## 4-qadam: Saytni ulash

`kamera-shop.html` faylida quyidagi qatorni toping:
```js
const TELEGRAM_BACKEND_URL = ""; // bo'sh bo'lsa, faqat WhatsApp/nusxalash ishlaydi
```
va Render bergan manzilga o'zgartiring:
```js
const TELEGRAM_BACKEND_URL = "https://vodiy-kameralar-bot.onrender.com";
```

Shundan keyin "Chekni shakllantirish" bosilganda, chek **avtomatik** sizning
Telegram'ingizga boradi — WhatsApp/nusxalash tugmalari ham qo'shimcha imkoniyat
sifatida ishlab turadi.

## Sinab ko'rish (lokal kompyuterda)

```bash
pip install -r requirements.txt
export BOT_TOKEN="sizning_tokeningiz"
export ADMIN_CHAT_IDS="sizning_chat_id"
python server.py
```

Keyin boshqa terminalda:
```bash
curl -X POST http://localhost:8080/order \
  -H "Content-Type: application/json" \
  -d '{"orderNo":"4573","name":"Aziz Karimov","phone":"+998901234567","address":"Andijon, Shahrixon","grandTotal":"133","items":[{"type":"product","name":"Hikvision DS-2CD 6MP Dome","qty":1,"price":48,"subtotal":48}]}'
```
Agar hammasi to'g'ri sozlangan bo'lsa, Telegram'da darhol xabar kelishi kerak.
