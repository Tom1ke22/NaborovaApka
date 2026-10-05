"""Tvrdé stropy na vstupy a výstupy jazykového modelu.

Na jednom mieste, lebo to isté číslo potrebuje validácia requestu (odmietni
skôr, než sa čokoľvek pošle modelu) aj samotné zostavenie promptu (posledná
poistka, keby sa dáta dostali do DB inou cestou).

Dôvod existencie tohto modulu je cena: každý znak, ktorý sem prejde, je token,
ktorý platíme. Stropy sú zámerne nízke — uchádzač sa pýta na mzdu a nástup,
nepotrebuje poslať knihu.
"""

from __future__ import annotations

# --- Chat uchádzača --------------------------------------------------------- #

# Jedna správa uchádzača. Nad tento limit sa request odmietne s 422, model sa
# nevolá vôbec.
MAX_CHAT_MESSAGE_CHARS = 2_000

# Koľko posledných správ ide modelu ako história.
MAX_CHAT_HISTORY_MESSAGES = 20

# Koľko správ session vôbec načítame z DB. Širšie ako okno pre model, aby sa
# history dalo trimovať v Pythone, ale stále ohraničené — session s 10 000
# správami nesmie vytiahnuť celú tabuľku do pamäti.
MAX_CHAT_HISTORY_FETCH = 60

# Koľko správ smie jedna session poslať za minútu.
MAX_CHAT_MESSAGES_PER_SESSION_PER_MINUTE = 30

# Strop na odpoveď chatbota. Dve až štyri vety sa zmestia do 600 tokenov.
CHAT_MAX_OUTPUT_TOKENS = 600


# --- Extrakcia z CV --------------------------------------------------------- #

# Koľko znakov textu zo životopisu pošleme modelu.
MAX_CV_CHARS = 15_000

# Koľko strán PDF vôbec otvoríme. 10 MB PDF môže mať tisíce strán a samotné
# čítanie textu by zožralo CPU ešte pred akýmkoľvek volaním modelu.
MAX_CV_PDF_PAGES = 40

# Koľko odstavcov DOCX prečítame, kým to zabalíme.
MAX_CV_DOCX_BLOCKS = 5_000

# Koľko znakov prepisu chatu pošleme hodnotiacemu modelu. Session môže mať
# stovky správ po 2 000 znakov, čo by bez stropu bol prompt za milióny tokenov.
MAX_CHAT_TRANSCRIPT_CHARS = 20_000

# Strop na odpoveď extrakcie. `ExtractedProfile` je JSON s citáciami, takže
# potrebuje viac miesta ako chat, ale nie neobmedzene.
EXTRACTION_MAX_OUTPUT_TOKENS = 4_096

# Po koľkých sekundách v stave „pending" považujeme AI hodnotenie za zlyhané.
# Samotná extrakcia má timeout 90 s; dlhšie čakanie znamená, že proces počas
# behu zomrel (reštart, Cloud Run zastavil CPU po odoslaní odpovede) a stav
# už nikto neprepíše. Admin potom dostane tlačidlo „Skúsiť znova".
AI_EVALUATION_STALE_AFTER_SECONDS = 10 * 60
