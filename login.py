"""
Userbot akkauntiga bir martalik kirish (user.session yaratadi).
Kod qayerga yuborilganini (ilova, SMS, email, qo'ng'iroq) ko'rsatadi.
"""

import asyncio
import os
import sys
from getpass import getpass
from pathlib import Path

import qrcode
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SESSION_FILE = BASE_DIR / "github_session.txt"
CODE_TYPES = {
    "SentCodeTypeApp": "Telegram ilovasidagi \"Telegram\" chatiga",
    "SentCodeTypeSms": "SMS orqali telefoningizga",
    "SentCodeTypeCall": "qo'ng'iroq orqali",
    "SentCodeTypeFlashCall": "qo'ng'iroq orqali (raqamning oxirgi xonalari)",
    "SentCodeTypeMissedCall": "javobsiz qo'ng'iroq orqali (raqamning oxirgi xonalari)",
    "SentCodeTypeEmailCode": "EMAIL manzilingizga",
    "SentCodeTypeFragmentSms": "fragment.com orqali",
    "SentCodeTypeFirebaseSms": "SMS orqali telefoningizga",
    "SentCodeTypeSmsWord": "SMS orqali (so'z ko'rinishida)",
    "SentCodeTypeSmsPhrase": "SMS orqali (ibora ko'rinishida)",
}


def describe(sent) -> str:
    name = type(sent.type).__name__
    where = CODE_TYPES.get(name, name)
    pattern = getattr(sent.type, "email_pattern", None)
    return f"{where}{f' ({pattern})' if pattern else ''}"


async def main() -> None:
    # --string: GitHub Actions uchun alohida sessiya (TG_SESSION secret)
    as_string = "--string" in sys.argv
    session = StringSession() if as_string else str(BASE_DIR / "user")
    client = TelegramClient(session, int(os.environ["API_ID"]), os.environ["API_HASH"])
    await client.connect()

    if not as_string and await client.is_user_authorized():
        me = await client.get_me()
        print(f"Allaqachon kirilgan: {me.first_name} (+{me.phone}). main.py ni ishga tushiring.")
        await client.disconnect()
        return

    choice = input("Kirish usuli: 1 - QR kod (tavsiya), 2 - telefon kodi [1]: ").strip()
    if choice != "2":
        await qr_login(client)
    else:
        await code_login(client)

    me = await client.get_me()
    if as_string:
        SESSION_FILE.write_text(client.session.save())
        print(
            f"\n✅ Muvaffaqiyatli kirildi: {me.first_name}.\n"
            f"Sessiya {SESSION_FILE.name} fayliga yozildi. Uni GitHub'ga "
            "TG_SESSION secret sifatida qo'ying va faylni o'chiring."
        )
    else:
        print(f"\n✅ Muvaffaqiyatli kirildi: {me.first_name}. Endi main.py ni ishga tushiring.")
    await client.disconnect()


async def qr_login(client: TelegramClient) -> None:
    print(
        "\nTelefoningizda: Telegram → Sozlamalar → Qurilmalar → "
        "\"Kompyuterni ulash\" (Link Desktop Device) → QR kodni skanerlang.\n"
    )
    qr = await client.qr_login()
    while True:
        code = qrcode.QRCode(border=1)
        code.add_data(qr.url)
        code.print_ascii(invert=True)
        try:
            await qr.wait(timeout=30)
            return
        except asyncio.TimeoutError:
            print("\nQR kod eskirdi, yangisi:\n")
            await qr.recreate()
        except SessionPasswordNeededError:
            await client.sign_in(password=getpass("Ikki bosqichli parol: "))
            return


async def code_login(client: TelegramClient) -> None:
    phone = input("Telefon raqam (+998...): ").strip()
    sent = await client.send_code_request(phone)
    print(f"\nKod yuborildi: {describe(sent)}")

    while True:
        code = input("Kodni kiriting (qayta yuborish uchun bo'sh qoldirib Enter): ").strip()
        if not code:
            sent = await client.send_code_request(phone, force_sms=True)
            print(f"Kod qayta yuborildi: {describe(sent)}")
            continue
        try:
            await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
            break
        except SessionPasswordNeededError:
            await client.sign_in(password=getpass("Ikki bosqichli parol: "))
            break
        except Exception as e:
            print(f"Xato: {type(e).__name__}. Qayta urinib ko'ring.")


if __name__ == "__main__":
    asyncio.run(main())
