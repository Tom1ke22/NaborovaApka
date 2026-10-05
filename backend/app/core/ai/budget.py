"""Denný strop na počet volaní Gemini.

Záchranná brzda, nie účtovníctvo. Keby chyba v kóde alebo útok prešli rate
limitom, tento counter zastaví volania po `AI_DAILY_CALL_LIMIT` za deň a
chatbot sa prepne do záložného režimu (uchádzač dostane zrozumiteľnú vetu,
nie chybu).

Obmedzenia, s ktorými treba počítať:
- counter je v pamäti procesu, takže pri viacerých instanciách platí strop na
  instanciu a po restarte sa nuluje,
- preto NENAHRADZUJE billing budget a kvótu requests/min a requests/deň
  nastavenú v Google Cloud na projekte alebo kľúči. Tá je jediná skutočne
  tvrdá hranica.

Default je 0 = bez stropu, aby sa appka sama neudusila bez toho, aby si to
niekto vedome nastavil.
"""

from __future__ import annotations

import logging
from datetime import date
from threading import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)

_lock = Lock()
_day: date | None = None
_calls = 0


def try_consume() -> bool:
    """Zaznač jedno volanie modelu. False = denný strop je vyčerpaný."""
    limit = settings.ai_daily_call_limit
    if limit <= 0:
        return True

    global _day, _calls
    today = date.today()
    with _lock:
        if _day != today:
            _day = today
            _calls = 0

        if _calls >= limit:
            logger.error(
                "Denný strop volaní AI je vyčerpaný (%s/%s). Volania sa zastavujú "
                "do zajtra; chatbot beží v záložnom režime a uchádzači ostanú bez skóre.",
                _calls,
                limit,
            )
            return False

        _calls += 1
        if _calls == limit:
            logger.warning("Posledné povolené volanie AI pre dnešný deň (%s/%s)", _calls, limit)
        return True


def usage() -> tuple[int, int]:
    """Vráť (počet volaní dnes, strop). Strop 0 znamená bez stropu."""
    with _lock:
        used = _calls if _day == date.today() else 0
    return used, settings.ai_daily_call_limit


def reset() -> None:
    """Vynuluj counter. Slúži testom."""
    global _day, _calls
    with _lock:
        _day = None
        _calls = 0
