"""
Vodiy Kameralar — buyurtmalarni saytdan qabul qilib, Telegram bot orqali
adminga yuboradigan kichik server.

ISHLASH TARTIBI:
1) BotFather orqali bot yarating -> BOT_TOKEN oling
2) O'zingizning Telegram chat ID'ingizni oling (pastdagi "Chat ID olish" bo'limini o'qing)
3) Shu ikkalasini muhit o'zgaruvchisi (environment variable) sifatida joylang
4) Serverni Render.com (yoki Railway) FREE tarifda joylashtiring
5) Saytdagi kamera-shop.html faylida TELEGRAM_BACKEND_URL ni shu serverning
   manziliga o'zgartiring (masalan: https://vodiy-kameralar.onrender.com)

CHAT ID OLISH:
- Botingizga Telegram'da /start deb yozing (bot avval sizga xabar yubora olmaydi,
  Telegram qoidasiga ko'ra, siz birinchi bo'lib botga yozishingiz kerak)
- Keyin brauzerda oching: https://api.telegram.org/bot<TOKEN>/getUpdates
- Javobdagi "chat":{"id": 123456789, ...} qismidan raqamni oling — shu sizning
  ADMIN_CHAT_IDS qiymatingiz
- Bir nechta admin bo'lsa, har biri botga /start yozadi, ID'larni vergul bilan
  ajratib yozasiz: ADMIN_CHAT_IDS=111111111,222222222
"""

import os
import logging
from datetime import datetime

from aiohttp import web, ClientSession

# .env faylini oddiy usulda o'qish (qo'shimcha kutubxonasiz).
# Lokal ishga tushirishda qulay; Render.com'da esa Environment bo'limidan
# to'g'ridan-to'g'ri o'zgaruvchilar keladi, .env kerak bo'lmaydi.
def _load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

_load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vodiy-order-server")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_CHAT_IDS = [c.strip() for c in os.environ.get("ADMIN_CHAT_IDS", "").split(",") if c.strip()]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TELEGRAM_SET_WEBHOOK = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

# Render.com bu o'zgaruvchini avtomatik beradi (masalan
# https://vodiy-kameralar-bot.onrender.com). Boshqa hostingda ishlatsangiz,
# PUBLIC_URL nomli environment variable qo'shib, shu manzilni qo'lda bering.
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("PUBLIC_URL", "")
WEBHOOK_PATH = "/telegram-webhook"

# Saytingiz qaysi domendan so'rov yuborishiga ruxsat berish (xavfsizlik uchun).
# Ishlab chiqarishda "*" o'rniga aniq domeningizni yozing, masalan:
# ALLOWED_ORIGIN = "https://sizning-saytingiz.pages.dev"
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")


def esc(text) -> str:
    """Telegram HTML formatida maxsus belgilarni xavfsiz qilish."""
    if text is None:
        return ""
    text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_message(data: dict) -> str:
    lines = []
    lines.append("🆕 <b>YANGI BUYURTMA — Vodiy Kameralar</b>")
    lines.append(f"🧾 Chek No: <b>{esc(data.get('orderNo', '-'))}</b>")
    lines.append(f"🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    lines.append("")
    lines.append("<b>📦 Mahsulotlar:</b>")

    for item in data.get("items", []):
        itype = item.get("type")
        if itype == "cable":
            lines.append(
                f"• Kabel ({esc(item.get('tier'))}) — {esc(item.get('qty'))} m "
                f"x {esc(item.get('pricePerM'))} so'm = <b>{esc(item.get('subtotal'))} so'm</b>"
            )
        else:
            lines.append(
                f"• {esc(item.get('qty'))}x {esc(item.get('name'))} "
                f"— ${esc(item.get('price'))} = <b>${esc(item.get('subtotal'))}</b>"
            )

    lines.append("")
    lines.append(f"💵 <b>JAMI: ${esc(data.get('grandTotal', '0'))}</b>")
    lines.append("")
    lines.append("<b>👤 Mijoz ma'lumotlari:</b>")
    lines.append(f"Ism: {esc(data.get('name', '-'))}")
    lines.append(f"📞 Telefon: <code>{esc(data.get('phone', '-'))}</code>")
    if data.get("homePhone"):
        lines.append(f"☎️ Uy telefoni: <code>{esc(data.get('homePhone'))}</code>")
    lines.append(f"📍 Manzil: {esc(data.get('address', '-'))}")
    lines.append("")
    lines.append("💰 To'lov: <b>qilinmagan</b> — operator mijoz bilan bog'lanishi kerak")
    return "\n".join(lines)


async def send_message(chat_id, text: str):
    async with ClientSession() as session:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        try:
            async with session.post(TELEGRAM_API, json=payload, timeout=10) as resp:
                return await resp.json()
        except Exception as e:
            log.exception("send_message xato: %s", e)
            return {"ok": False, "error": str(e)}


STATUS_MESSAGE = (
    "✅ <b>Bot ishlamoqda!</b>\n\n"
    "Bu bot \"Vodiy Kameralar\" saytidan kelgan yangi buyurtmalarni sizga "
    "avtomatik yuboradi. Hech qanday qo'shimcha amal bajarish shart emas — "
    "mijoz saytda buyurtma bersa, chek shu chatga o'zi keladi.\n\n"
    "Boshqa buyruqlar hozircha yo'q, bot faqat xabar yetkazish uchun ishlaydi."
)


async def handle_telegram_webhook(request: web.Request) -> web.Response:
    """Telegram'dan kelgan yangilanishlarni (masalan /start) qabul qiladi."""
    try:
        update = await request.json()
    except Exception:
        return web.json_response({"ok": False}, status=400)

    message = update.get("message") or update.get("edited_message")
    if message:
        chat_id = message.get("chat", {}).get("id")
        text = (message.get("text") or "").strip()
        if chat_id:
            if text.startswith("/start"):
                await send_message(chat_id, STATUS_MESSAGE)
            else:
                await send_message(
                    chat_id,
                    "ℹ️ Bu bot faqat saytdan kelgan buyurtma xabarlarini yetkazadi, "
                    "yozishma funksiyasi yo'q. Holatni tekshirish uchun /start yozing.",
                )

    return web.json_response({"ok": True})


async def setup_webhook(app: web.Application):
    """Server ishga tushganda Telegram'ga: 'yangilanishlarni shu manzilga yubor' deb aytadi."""
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN yo'q — webhook sozlanmadi.")
        return
    if not PUBLIC_URL:
        log.warning(
            "PUBLIC_URL aniqlanmadi — /start webhook sozlanmadi. "
            "Render'da bu odatda avtomatik keladi (RENDER_EXTERNAL_URL)."
        )
        return
    url = PUBLIC_URL.rstrip("/") + WEBHOOK_PATH
    async with ClientSession() as session:
        try:
            async with session.post(TELEGRAM_SET_WEBHOOK, json={"url": url}, timeout=10) as resp:
                body = await resp.json()
                log.info("setWebhook(%s) -> %s", url, body)
        except Exception as e:
            log.exception("setWebhook xato: %s", e)


async def handle_order(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    if not BOT_TOKEN or not ADMIN_CHAT_IDS:
        log.error("BOT_TOKEN yoki ADMIN_CHAT_IDS sozlanmagan!")
        return web.json_response(
            {"ok": False, "error": "server not configured (BOT_TOKEN / ADMIN_CHAT_IDS)"},
            status=500,
        )

    text = build_message(data)
    results = []
    async with ClientSession() as session:
        for chat_id in ADMIN_CHAT_IDS:
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            try:
                async with session.post(TELEGRAM_API, json=payload, timeout=10) as resp:
                    body = await resp.json()
                    results.append({"chat_id": chat_id, "ok": body.get("ok", False)})
                    if not body.get("ok"):
                        log.warning("Telegram xato (chat_id=%s): %s", chat_id, body)
            except Exception as e:
                log.exception("Yuborishda xato: %s", e)
                results.append({"chat_id": chat_id, "ok": False, "error": str(e)})

    any_ok = any(r["ok"] for r in results)
    return web.json_response({"ok": any_ok, "results": results})


async def handle_root(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "vodiy-kameralar-order-bot"})


def add_cors(response: web.Response) -> web.Response:
    response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        return add_cors(web.Response())
    response = await handler(request)
    return add_cors(response)


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/", handle_root)
    app.router.add_post("/order", handle_order)
    app.router.add_options("/order", lambda r: web.Response())
    app.router.add_post(WEBHOOK_PATH, handle_telegram_webhook)
    app.on_startup.append(setup_webhook)
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    log.info("Server ishga tushdi, port=%s, admin(lar)=%s", port, ADMIN_CHAT_IDS)
    web.run_app(app, host="0.0.0.0", port=port)
