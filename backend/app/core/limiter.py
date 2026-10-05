"""Rate limiting.

Dve veci:

1. `limiter` — slowapi limiter pre dekorátory na endpointoch. Kľúčuje na
   skutočnú IP klienta, nie na IP reverznej proxy. Bez toho by za nginx alebo
   Cloud Run všetci uchádzači zdieľali jeden limit (jeden robot zavrie formulár
   všetkým) a útočník by sa skryl za IP proxy.

2. `WindowRateLimiter` — počítadlo v pamäti procesu pre limity, ktoré sa nedajú
   kľúčovať z requestu synchrónne. Konkrétne session_id chatu je v tele
   requestu a slowapi `key_func` telo nevidí.

Obe sú v pamäti procesu. Pri viacerých instanciách (Cloud Run) teda platia
na instanciu, nie globálne. Pre náš účel — zabrániť tomu, aby jedna session
alebo jedna IP vyčerpala Gemini kredit — to stačí; globálny strop rieši
kvóta na strane Google (pozri `app/core/ai/budget.py`).
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock

from slowapi import Limiter
from starlette.requests import Request

from app.core.config import settings


def client_ip(request: Request) -> str:
    """Skutočná IP klienta.

    Bez `TRUST_PROXY_HEADERS=true` berieme peer adresu spojenia. To je správne
    pri lokálnom vývoji aj vždy, keď appka visí na internete priamo: hlavičku
    `X-Forwarded-For` si totiž môže poslať ktokoľvek, a keby sme jej verili,
    útočník by si limit obišiel jednou náhodnou hlavičkou.

    S `TRUST_PROXY_HEADERS=true` čítame `X-Forwarded-For` sprava a zahodíme
    `TRUSTED_PROXY_HOPS` záznamov, ktoré do hlavičky dopísali naše proxy.
    Prvý zostávajúci záznam od konca je posledná adresa, ktorú nám vyplnila
    proxy, ktorej veríme — teda tá, ktorú klient nemohol podvrhnúť.

        XFF: "1.2.3.4"                 hops=0  ->  1.2.3.4   (nginx, Cloud Run)
        XFF: "podvrh, 1.2.3.4"         hops=0  ->  1.2.3.4   (podvrh sa ignoruje)
        XFF: "1.2.3.4, 35.191.0.1"     hops=1  ->  1.2.3.4   (Cloud Run za LB)
    """
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        hops = max(settings.trusted_proxy_hops, 0)
        if len(parts) > hops:
            return parts[len(parts) - 1 - hops]

    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)


class WindowRateLimiter:
    """Počítadlo udalostí na kľúč v posuvnom okne.

    `hit()` vráti False, keď kľúč v okne limit prekročil. Staré kľúče sa
    priebežne zahadzujú, aby pamäť nerástla s počtom session.
    """

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()
        self._last_cleanup = 0.0

    def hit(self, key: str) -> bool:
        """Zaznač udalosť. False = limit je vyčerpaný a udalosť sa nezaznačila."""
        now = time.monotonic()
        with self._lock:
            self._cleanup(now)

            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self._window:
                hits.popleft()

            if len(hits) >= self._limit:
                return False

            hits.append(now)
            return True

    def reset(self) -> None:
        """Zahoď všetko. Slúži testom."""
        with self._lock:
            self._hits.clear()
            self._last_cleanup = 0.0

    def _cleanup(self, now: float) -> None:
        """Zahoď kľúče, ktoré sú celé mimo okna. Nanajvýš raz za okno."""
        if now - self._last_cleanup < self._window:
            return
        self._last_cleanup = now
        self._hits = {
            key: hits
            for key, hits in self._hits.items()
            if hits and now - hits[-1] <= self._window
        }
