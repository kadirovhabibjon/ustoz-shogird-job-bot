# ustoz-shogird-job-bot

[Ustoz-Shogird](https://t.me/UstozShogird) kanalida **"Xodim kerak"** e'loni chiqishi bilan uni Telegram bot orqali **faqat sizga** yuboradi.

## Qanday ishlaydi

Oddiy bot begona kanalni o'qiy olmaydi, shuning uchun ikki qism bor:

- **Userbot** (Telethon, sizning akkauntingiz): kanaldagi yangi postlarni o'qiydi va birinchi qatori "Xodim kerak" ekanini tekshiradi.
- **Bot** (@BotFather orqali yaratilgan): topilgan postni asl ko'rinishida (formatlash, rasm/fayl bilan) faqat sizga yuboradi. Sizning ID raqamingiz userbot akkauntidan avtomatik aniqlanadi, begonalarga bot javob bermaydi.

## O'rnatish

1. **API kalitlari:** https://my.telegram.org → *API development tools* bo'limidan `API_ID` va `API_HASH` oling.
2. **Bot:** @BotFather → `/newbot` buyrug'i bilan bot yarating va tokenni oling.
3. **Kanalga obuna:** akkauntingiz Ustoz-Shogird kanaliga obuna bo'lgan bo'lishi kerak.
4. Sozlash:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   cp .env.example .env   # va qiymatlarni to'ldiring
   ```

5. Akkauntga kiring (bir marta). QR kodni telefondagi Telegram → Settings → Devices → Link Desktop Device orqali skanerlang:

   ```bash
   .venv/bin/python login.py
   ```

   `user.session` fayli saqlanadi va keyin boshqa so'ralmaydi.

6. Ishga tushiring:

   ```bash
   .venv/bin/python main.py          # oddiy rejim
   .venv/bin/python main.py --test   # oxirgi "Xodim kerak" postini darhol yuborib sinaydi
   ```

7. Telegramda botingizni oching va bir marta `/start` bosing (Telegram qoidasiga ko'ra bot sizga birinchi bo'lib yoza olmaydi).

## GitHub Actions'da ishlatish (server bo'lmaganda)

`check.py` har 5 daqiqada GitHub Actions'da ishga tushadi ([.github/workflows/check.yml](.github/workflows/check.yml)), oxirgi tekshiruvdan beri chiqqan "Xodim kerak" postlarini yuboradi va o'chadi. E'lonlar 5–15 daqiqa kechikib keladi (GitHub jadvalni ba'zan kechiktiradi). Server olingandan keyin `main.py` ishlatiladi va e'lonlar darhol keladi.

1. GitHub uchun alohida sessiya oling (QR kod orqali):

   ```bash
   .venv/bin/python login.py --string
   ```

   Sessiya `github_session.txt` fayliga yoziladi.

2. Repo → **Settings → Secrets and variables → Actions → New repository secret** orqali 4 ta secret qo'shing:

   | Nomi | Qiymati |
   |------|---------|
   | `API_ID` | `.env` dagi `API_ID` |
   | `API_HASH` | `.env` dagi `API_HASH` |
   | `BOT_TOKEN` | `.env` dagi `BOT_TOKEN` |
   | `TG_SESSION` | `github_session.txt` ichidagi butun matn |

   Keyin `github_session.txt` ni o'chiring.

3. Repo → **Actions → Xodim kerak tekshiruvi → Run workflow** ni bosing. Birinchi ishga tushish boshlang'ich nuqtani saqlaydi. Sinash uchun **test** belgisini qo'yib ishga tushirsangiz, oxirgi "Xodim kerak" posti darhol keladi.

Eslatmalar:

- GitHub va kompyuterdagi `main.py` bir vaqtda ishlasa, e'lonlar ikki marta keladi. Server olganda workflow'ni o'chiring (Actions → workflow → **Disable workflow**).
- Repoda 60 kun hech qanday o'zgarish bo'lmasa, GitHub jadvalni to'xtatadi va email yuboradi. Unda Actions sahifasida qayta yoqing.

## Sozlamalar (`.env`)

| O'zgaruvchi   | Tavsif |
|---------------|--------|
| `CHANNEL`     | Kuzatiladigan kanal (standart: `UstozShogird`) |
| `KEYWORDS`    | Qidiriladigan so'zlar, vergul bilan (masalan `xodim kerak,ходим керак`) |

## Xavfsizlik

`.env` va `*.session` fayllarini hech kimga bermang va gitga yuklamang (ular `.gitignore` da bor). Session fayli orqali akkauntingizga to'liq kirish mumkin.
