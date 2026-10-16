"""
Ustoz-Shogird kanalidagi "Xodim kerak" e'lonlarini kuzatib,
ularni bot orqali faqat egasiga (sizga) yuboradi.

Ishlash tartibi:
  * userbot (sizning Telegram akkauntingiz) kanalni o'qiydi;
  * bot esa topilgan e'lonni sizga yuboradi.
"""

import asyncio
import io
import logging
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

import matcher

load_dotenv()

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.getenv("CHANNEL", "UstozShogird")
KEYWORDS = [
    k.strip().lower()
    for k in os.getenv("KEYWORDS", "xodim kerak,ходим керак").split(",")
    if k.strip()
]

BASE_DIR = Path(__file__).resolve().parent
MAX_MESSAGE_LEN = 4096
MAX_CAPTION_LEN = 1024

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
log = logging.getLogger("job-bot")


def normalize(text: str) -> str:
    # "Xodim  kerak", "XODIM KERAK", "#xodim_kerak" kabi variantlarni bir xil qiladi
    return re.sub(r"[\s_]+", " ", text.lower())


def is_job_post(text: str) -> bool:
    # E'lon turi birinchi qatorda yoziladi: "Xodim kerak:", "Ish joyi kerak:" ...
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    first_line = normalize(first_line)
    return any(k in first_line for k in KEYWORDS)


def is_wanted(text: str) -> tuple[bool, str]:
    """"Xodim kerak" e'loni va profile.json ga mos bo'lsa True."""
    if not is_job_post(text):
        return False, "xodim kerak emas"
    return matcher.match(text)


def post_link(chat, msg_id: int) -> str:
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{msg_id}"
    return f"https://t.me/c/{chat.id}/{msg_id}"


async def main() -> None:
    user = TelegramClient(str(BASE_DIR / "user"), API_ID, API_HASH)
    bot = TelegramClient(str(BASE_DIR / "bot"), API_ID, API_HASH)

    await user.start()  # birinchi marta telefon raqam va kodni so'raydi
    await bot.start(bot_token=BOT_TOKEN)

    owner_id = (await user.get_me()).id
    channel = await user.get_entity(CHANNEL)
    log.info("Egasi: %s | Kanal: %s | Kalit so'zlar: %s", owner_id, CHANNEL, KEYWORDS)

    @bot.on(events.NewMessage(pattern=r"^/start"))
    async def on_start(event):
        if event.sender_id != owner_id:
            return  # begonalarga javob bermaydi
        await event.respond(
            "✅ Bot ishlayapti. Ustoz-Shogird kanalida yangi "
            "\"Xodim kerak\" e'loni chiqishi bilan sizga yuboraman."
        )

    @user.on(events.NewMessage(chats=channel))
    async def on_channel_post(event):
        text = event.raw_text or ""
        if not is_job_post(text):
            return
        ok, reason = matcher.match(text)
        if not ok:
            log.info("O'tkazib yuborildi (%s): %s", reason, post_link(event.chat, event.id))
            return

        log.info("Yangi 'Xodim kerak' e'loni: %s", post_link(event.chat, event.id))

        try:
            await copy_post(event.message)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            await copy_post(event.message)
        except Exception:
            log.exception(
                "Xabar yuborilmadi. Botga /start bosganingizni tekshiring."
            )

    async def copy_post(msg) -> None:
        # Postni asl ko'rinishida (formatlash, rasm/fayl bilan) nusxalaydi.
        # Bot kanalga a'zo emas, shuning uchun forward qilib bo'lmaydi:
        # media userbot orqali yuklab olinib, bot orqali qayta yuboriladi.
        text, entities = msg.message or "", msg.entities
        if msg.media and not msg.web_preview:
            file = io.BytesIO(await user.download_media(msg, file=bytes))
            file.name = msg.file.name or f"file{msg.file.ext or '.jpg'}"
            fits_caption = len(text) <= MAX_CAPTION_LEN
            await bot.send_file(
                owner_id,
                file,
                caption=text if fits_caption else None,
                formatting_entities=entities if fits_caption else None,
                attributes=getattr(msg.document, "attributes", None),
            )
            if fits_caption:
                return
        await bot.send_message(
            owner_id,
            text[:MAX_MESSAGE_LEN],
            formatting_entities=entities,
            link_preview=bool(msg.web_preview),
        )

    if "--test" in sys.argv:
        # Sinov: kanaldagi eng oxirgi "Xodim kerak" postini darhol yuboradi
        async for msg in user.iter_messages(channel, limit=100):
            if is_wanted(msg.raw_text or "")[0]:
                await copy_post(msg)
                log.info("Sinov posti yuborildi: %s", post_link(channel, msg.id))
                break
        else:
            log.info("Oxirgi 100 ta postda 'Xodim kerak' topilmadi.")

    log.info("Bot ishga tushdi. Kanal kuzatilmoqda...")
    await asyncio.gather(
        user.run_until_disconnected(), bot.run_until_disconnected()
    )


if __name__ == "__main__":
    asyncio.run(main())
