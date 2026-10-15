"""
Bir martalik tekshiruv (GitHub Actions uchun).

Oxirgi tekshiruvdan beri kanalda chiqqan "Xodim kerak" postlarini topadi,
ularni Bot API orqali egasiga yuboradi va oxirgi ko'rilgan post ID sini
state.json ga yozadi. Doimiy ishlaydigan versiya: main.py.

  python check.py          # yangi postlarni tekshirish
  python check.py --test   # oxirgi "Xodim kerak" postini darhol yuborish
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

from main import CHANNEL, MAX_CAPTION_LEN, MAX_MESSAGE_LEN, is_job_post

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
TG_SESSION = os.environ["TG_SESSION"]

STATE_FILE = Path(os.getenv("STATE_FILE", "state.json"))
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
ERROR_NOTICE_INTERVAL = 6 * 60 * 60  # xato haqida 6 soatda ko'pi bilan bir marta xabar


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def bot_call(method: str, data: dict, files: dict | None = None) -> None:
    r = requests.post(f"{BOT_API}/{method}", data=data, files=files, timeout=60)
    if not r.ok:
        raise RuntimeError(f"{method} xatosi: {r.status_code} {r.text}")


async def copy_post(user: TelegramClient, chat_id: int, msg) -> None:
    try:
        # msg.text HTML ko'rinishida (user.parse_mode = "html"), Bot API ham HTML qabul qiladi
        await send_post(user, chat_id, msg, msg.text or "", "HTML")
    except RuntimeError as e:
        # Bot API biror formatlashni qabul qilmasa, oddiy matn sifatida yuboramiz
        print(f"HTML bilan yuborilmadi, oddiy matnda yuborilmoqda: {e}")
        await send_post(user, chat_id, msg, msg.message or "", None)


async def send_post(user: TelegramClient, chat_id: int, msg, html: str, parse_mode) -> None:
    fmt = {"parse_mode": parse_mode} if parse_mode else {}
    fits_caption = len(msg.message or "") <= MAX_CAPTION_LEN

    if msg.media and not msg.web_preview:
        data = await user.download_media(msg, file=bytes)
        if msg.photo:
            method, field, name = "sendPhoto", "photo", "photo.jpg"
        else:
            method, field = "sendDocument", "document"
            name = msg.file.name or f"file{msg.file.ext or ''}"
        payload = {"chat_id": chat_id}
        if fits_caption and html:
            payload.update(caption=html, **fmt)
        bot_call(method, payload, files={field: (name, data)})
        if fits_caption:
            return

    bot_call(
        "sendMessage",
        {"chat_id": chat_id, "text": html[:MAX_MESSAGE_LEN], **fmt},
    )


async def check(state: dict) -> None:
    async with TelegramClient(StringSession(TG_SESSION), API_ID, API_HASH) as user:
        user.parse_mode = "html"
        owner_id = (await user.get_me()).id
        state["owner_id"] = owner_id  # xato haqida xabar berish uchun eslab qolamiz
        channel = await user.get_entity(CHANNEL)

        if "--test" in sys.argv:
            async for msg in user.iter_messages(channel, limit=100):
                if is_job_post(msg.raw_text or ""):
                    await copy_post(user, owner_id, msg)
                    print(f"Sinov posti yuborildi: {msg.id}")
                    return
            print("Oxirgi 100 ta postda 'Xodim kerak' topilmadi.")
            return

        if "last_id" not in state:
            # Birinchi ishga tushish: eski postlarni yubormaymiz, faqat joyni belgilaymiz
            latest = await user.get_messages(channel, limit=1)
            state["last_id"] = latest[0].id if latest else 0
            save_state(state)
            print("Birinchi ishga tushish: boshlang'ich nuqta saqlandi.")
            return

        sent = 0
        async for msg in user.iter_messages(channel, min_id=state["last_id"], reverse=True):
            if is_job_post(msg.raw_text or ""):
                await copy_post(user, owner_id, msg)
                sent += 1
            # Har bir postdan keyin saqlaymiz: xato bo'lsa, keyingi safar shu joydan davom etadi
            state["last_id"] = msg.id
            save_state(state)
        print(f"Tekshirildi. Yuborilgan 'Xodim kerak' postlari: {sent}")


async def main() -> None:
    state = load_state()
    try:
        await check(state)
    except Exception as e:
        notify_error(state, e)
        raise
    if state.pop("error_notified_at", None):
        notify_owner(state, "✅ Bot yana ishlayapti.")
    save_state(state)


def notify_owner(state: dict, text: str) -> None:
    if "owner_id" in state:
        try:
            bot_call("sendMessage", {"chat_id": state["owner_id"], "text": text})
        except Exception as e:
            print(f"Egasiga xabar yuborilmadi: {e}")


def notify_error(state: dict, error: Exception) -> None:
    # Bot jimgina to'xtab qolmasligi uchun egasini ogohlantiramiz (6 soatda bir martadan ko'p emas)
    now = time.time()
    if now - state.get("error_notified_at", 0) < ERROR_NOTICE_INTERVAL:
        return
    run_url = os.getenv("RUN_URL", "")
    details = f"{type(error).__name__}: {error}".replace(BOT_TOKEN, "***")
    notify_owner(state, f"⚠️ Xodim kerak boti ishlamay qoldi:\n{details}\n\n{run_url}".strip())
    state["error_notified_at"] = now
    save_state(state)


if __name__ == "__main__":
    asyncio.run(main())
