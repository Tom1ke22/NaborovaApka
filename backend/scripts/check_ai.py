"""Overenie, či AI naozaj funguje: kľúč, názov modelu, chat aj extrakcia.

Spustenie v Dockeri:
    docker compose exec backend python scripts/check_ai.py

Alebo lokálne z priečinka backend:
    python scripts/check_ai.py

Databázu nepotrebuje. Robí dve skutočné volania na Gemini, takže minie
nepatrný počet tokenov. Ak niečo nesedí, vypíše čo presne.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

# Funguje v kontajneri (/app) aj lokálne (priečinok backend).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.ai.chat import FALLBACK_REPLY, generate_response
from app.core.ai.extraction import extract_profile
from app.core.config import settings

OK = "  [OK]"
FAIL = "  [CHYBA]"

POSITION = SimpleNamespace(
    title="Kuchár",
    work_area="Gastro",
    location="Bratislava",
    contract_type="neuricity_cas",
    working_hours="8 hodín denne",
    shift_type=None,
    break_info=None,
    work_regime=None,
    salary_amount=1500,
    salary_period="monthly",
    vacation_days=25,
    meal_allowance=None,
    start_date=None,
    open_slots=1,
    contact_person=None,
    description="Príprava jedál v školskej jedálni.",
    additional_info=None,
    ai_bot_instructions=None,
)

REQUIREMENTS = SimpleNamespace(
    hygiene_minimum_required=True,
    health_certificate_required=True,
    experience_required=True,
    experience_years=2,
    education_level=None,
    slovak_language_level=None,
    foreign_language_level=None,
)

CV = """\
Marek Novák
Kuchár, 3 roky praxe v školskej jedálni v Bratislave.
Výučný list v odbore kuchár.
Mám platný zdravotný preukaz aj osvedčenie o hygienickom minime.
"""

CHAT = "Uchádzač: Dobrý deň, mám 3 roky praxe ako kuchár a oba doklady mám platné."


def check_config() -> bool:
    print("1. Konfigurácia")
    print(f"   AI_ENABLED               = {settings.ai_enabled}")
    print(f"   GEMINI_API_KEY nastavený = {bool(settings.gemini_api_key)}")
    print(f"   GEMINI_CHAT_MODEL        = {settings.gemini_chat_model}")
    print(f"   GEMINI_EXTRACTION_MODEL  = {settings.gemini_extraction_model}")

    if not settings.ai_available:
        print(f"{FAIL} AI je vypnutá. Doplň GEMINI_API_KEY a nastav AI_ENABLED=true v .env")
        return False

    print(f"{OK} konfigurácia vyzerá v poriadku")
    return True


async def check_chat() -> bool:
    print("\n2. Chatbot (skutočné volanie modelu)")
    answer = ""
    async for chunk in generate_response(
        POSITION, [], "Dobrý deň, aká je mzda a koľko je dovolenky?", "Marek",
        requirements=REQUIREMENTS,
    ):
        answer += chunk

    if not answer.strip() or answer.strip() == FALLBACK_REPLY.strip():
        print(f"{FAIL} model neodpovedal. Skontroluj kľúč a názov modelu v logoch vyššie.")
        return False

    print(f"   Odpoveď: {answer.strip()}")
    if "1500" in answer or "25" in answer:
        print(f"{OK} model čerpá z údajov o pozícii")
    else:
        print("  [POZOR] odpoveď neobsahuje mzdu ani dovolenku, skontroluj ju očami")
    return True


async def check_extraction() -> bool:
    print("\n3. Extrakcia faktov zo životopisu a chatu")
    profile = await extract_profile(POSITION, REQUIREMENTS, CV, CHAT)

    if profile is None:
        print(f"{FAIL} fakty sa nepodarilo získať. Detail je v logoch vyššie.")
        return False

    print(f"   prax              : {profile.experience.years} rokov")
    print(f"   hygienické minimum: {profile.hygiene_minimum.value.value}")
    print(f"   zdravotný preukaz : {profile.health_certificate.value.value}")
    print(f"   celkový odhad     : {profile.overall_fit}/10")
    print(f"   zhrnutie          : {profile.summary}")

    from app.core.ai.scoring import Requirements, compute_score

    result = compute_score(Requirements.from_orm(REQUIREMENTS), profile)
    print(f"\n   VÝSLEDNÉ SKÓRE: {result.score}/10")
    print(f"   Zdôvodnenie: {result.reasoning}")

    if result.score < 7:
        print("  [POZOR] modelový uchádzač spĺňa všetko, čakalo by sa skóre 8 a viac")
    else:
        print(f"{OK} celý reťazec CV → fakty → skóre funguje")
    return True


async def main() -> None:
    print("=" * 70)
    print("Kontrola AI vrstvy náborovej aplikácie")
    print("=" * 70)

    if not check_config():
        sys.exit(1)

    chat_ok = await check_chat()
    extraction_ok = await check_extraction()

    print("\n" + "=" * 70)
    if chat_ok and extraction_ok:
        print("Všetko funguje. AI je pripravená na produkciu.")
    else:
        print("Niečo nefunguje, pozri chyby vyššie.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
