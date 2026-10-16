"""
"Xodim kerak" e'lonini profile.json dagi bilim, hudud va maoshga solishtiradi.

E'lonlar odatda shunday qolipda bo'ladi:
    📚 Texnologiya: Python, Django
    🌐 Hudud: Toshkent sh
    💰 Maosh: $700+
Maydon topilmasa yoki tushunib bo'lmasa (masalan "Kelishiladi"), e'lon
o'sha shart bo'yicha rad etilmaydi.
"""

import json
import re
from pathlib import Path

PROFILE_FILE = Path(__file__).resolve().parent / "profile.json"

LOCATION_FIELDS = ("hudud", "manzil", "joylashuv", "регион", "адрес")
SALARY_FIELDS = ("maosh", "oylik", "ish haqi", "зарплата", "зп")
USD_WORDS = ("$", "usd", "dollar", "доллар", "у.е")
UZS_WORDS = ("so'm", "so`m", "som", "сум", "uzs", "sum")


def load_profile() -> dict:
    return json.loads(PROFILE_FILE.read_text())


def _contains(text: str, term: str) -> bool:
    # So'z chegarasi bilan qidiradi: "rag" "storage" ichida topilmasin
    return re.search(rf"(?<![\w]){re.escape(term)}(?![\w])", text) is not None


def _found(text: str, groups: dict) -> list[str]:
    return [name for name, terms in groups.items() if any(_contains(text, t) for t in terms)]


def _field(text: str, names: tuple) -> str | None:
    # "💰 Maosh: $700+" -> "$700+"
    for line in text.splitlines():
        low = line.lower()
        if ":" in low and any(n in low.split(":", 1)[0] for n in names):
            return low.split(":", 1)[1].strip()
    return None


def parse_salary_usd(value: str, usd_rate: float) -> tuple[float | None, float | None] | None:
    """Maosh matnidan (min, max) ni dollarda qaytaradi; tushunib bo'lmasa None."""
    # "5 000 000" / "5.000.000" -> "5000000"; "1.5 mln" o'zgarmaydi
    s = re.sub(r"(?<=\d)[  .,](?=\d{3}(?!\d))", "", value)
    tokens = re.findall(r"(\d+(?:[.,]\d+)?)\s*(mln|млн|million|ming|тыс|k)?", s)
    # "15-20 mln": birinchi son ham "mln" ga tegishli
    last_mult = next((m for _, m in reversed(tokens) if m), "")
    nums = []
    for num, mult in tokens:
        n = float(num.replace(",", "."))
        mult = mult or (last_mult if n < 1000 else "")
        if mult in ("mln", "млн", "million"):
            n *= 1_000_000
        elif mult in ("ming", "тыс", "k"):
            n *= 1_000
        nums.append(n)
    if not nums:
        return None

    is_usd = any(w in s for w in USD_WORDS)
    is_uzs = any(w in s for w in UZS_WORDS) or max(nums) >= 100_000
    if is_uzs and not is_usd:
        nums = [n / usd_rate for n in nums]
    elif not is_usd:
        return None  # valyuta noma'lum

    low, high = min(nums), max(nums)
    if len(nums) == 1:
        # "$700+" / "700$ dan" -> kamida 700; "700$ gacha" -> ko'pi bilan 700
        if "gacha" in s or _contains(s, "до"):
            return None, high
        if "+" in s or "dan" in s or _contains(s, "от"):
            return low, None
        return low, high
    return low, high


def match(text: str, profile: dict | None = None) -> tuple[bool, str]:
    """(mos keladimi, sabab)"""
    p = profile or load_profile()
    low = text.lower()

    for word in p.get("exclude_words", []):
        if _contains(low, word.lower()):
            return False, f"istisno so'z: {word}"

    strong = _found(low, p["skills"])
    weak = _found(low, p.get("weak_skills", {}))
    if not strong and len(weak) < p.get("min_weak_skills", 2):
        return False, f"bilim mos emas (yordamchi: {', '.join(weak) or '-'})"

    location = _field(text, LOCATION_FIELDS)
    is_remote = any(_contains(low, w) for w in p["remote_words"])
    if location and not is_remote and not any(loc in location for loc in p["locations"]):
        return False, f"hudud: {location}"

    salary = _field(text, SALARY_FIELDS)
    rng = parse_salary_usd(salary, p["usd_rate"]) if salary else None
    if rng:
        lo, hi = rng
        want = p["salary_usd"]
        if hi is not None and want.get("min") is not None and hi < want["min"]:
            return False, f"maosh past: {salary}"
        if lo is not None and want.get("max") is not None and lo > want["max"]:
            return False, f"maosh yuqori: {salary}"

    return True, "mos: " + ", ".join(strong + weak)
