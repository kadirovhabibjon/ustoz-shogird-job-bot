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


def load_last_id() -> int | None:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())["last_id"]
    return None


def save_last_id(last_id: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_id": last_id}))


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


async def main() -> None:
    async with TelegramClient(StringSession(TG_SESSION), API_ID, API_HASH) as user:
        user.parse_mode = "html"
        owner_id = (await user.get_me()).id
        channel = await user.get_entity(CHANNEL)

        if "--test" in sys.argv:
            async for msg in user.iter_messages(channel, limit=100):
                if is_job_post(msg.raw_text or ""):
                    await copy_post(user, owner_id, msg)
                    print(f"Sinov posti yuborildi: {msg.id}")
                    return
            print("Oxirgi 100 ta postda 'Xodim kerak' topilmadi.")
            return

        last_id = load_last_id()
        if last_id is None:
            # Birinchi ishga tushish: eski postlarni yubormaymiz, faqat joyni belgilaymiz
            latest = await user.get_messages(channel, limit=1)
            save_last_id(latest[0].id if latest else 0)
            print("Birinchi ishga tushish: boshlang'ich nuqta saqlandi.")
            return

        sent = 0
        async for msg in user.iter_messages(channel, min_id=last_id, reverse=True):
            if is_job_post(msg.raw_text or ""):
                await copy_post(user, owner_id, msg)
                sent += 1
            # Har bir postdan keyin saqlaymiz: xato bo'lsa, keyingi safar shu joydan davom etadi
            save_last_id(msg.id)
        print(f"Tekshirildi. Yuborilgan 'Xodim kerak' postlari: {sent}")


if __name__ == "__main__":
    asyncio.run(main())
