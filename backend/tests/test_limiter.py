"""Testy rate limitingu.

Dve veci, ktoré musia držať:
- kľúč limitu je skutočná IP klienta, nie IP reverznej proxy (inak limit buď
  nechytí útočníka, alebo zavrie formulár všetkým uchádzačom naraz),
- hlavičke X-Forwarded-For sa neverí, kým to niekto vedome nezapne.
"""

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.limiter import WindowRateLimiter, client_ip


def request_with(headers: dict | None = None, peer: str | None = "10.0.0.1"):
    """Minimálna napodobenina Request — key_func potrebuje len hlavičky a peer."""
    return SimpleNamespace(
        headers={k.lower(): v for k, v in (headers or {}).items()},
        client=SimpleNamespace(host=peer) if peer else None,
    )


@pytest.fixture
def proxy(monkeypatch):
    """Zapni dôveru proxy hlavičkám s daným počtom hopov."""

    def configure(hops: int = 0, trust: bool = True):
        monkeypatch.setattr(settings, "trust_proxy_headers", trust)
        monkeypatch.setattr(settings, "trusted_proxy_hops", hops)

    return configure


# --------------------------------------------------------------------------- #
# Zistenie IP klienta
# --------------------------------------------------------------------------- #

def test_without_proxy_trust_the_peer_address_is_used(proxy):
    proxy(trust=False)
    request = request_with({"X-Forwarded-For": "1.2.3.4"}, peer="10.0.0.1")
    assert client_ip(request) == "10.0.0.1"


def test_forwarded_header_is_ignored_when_not_trusted(proxy):
    """Bez TRUST_PROXY_HEADERS si limit nesmie obísť ktokoľvek hlavičkou."""
    proxy(trust=False)
    first = client_ip(request_with({"X-Forwarded-For": "1.1.1.1"}, peer="10.0.0.1"))
    second = client_ip(request_with({"X-Forwarded-For": "2.2.2.2"}, peer="10.0.0.1"))
    assert first == second == "10.0.0.1"


def test_trusted_proxy_gives_the_real_client_ip(proxy):
    """Za nginx alebo priamym Cloud Run URL je klient jediný záznam v XFF."""
    proxy(hops=0)
    request = request_with({"X-Forwarded-For": "1.2.3.4"}, peer="10.0.0.1")
    assert client_ip(request) == "1.2.3.4"


def test_spoofed_entries_in_front_are_ignored(proxy):
    """Proxy dopisuje svojho peera na konec, takže zľava sa dá podvrhnúť."""
    proxy(hops=0)
    request = request_with({"X-Forwarded-For": "9.9.9.9, 1.2.3.4"}, peer="10.0.0.1")
    assert client_ip(request) == "1.2.3.4"


def test_one_trusted_hop_is_skipped(proxy):
    """Cloud Run za externým load balancerom: posledný záznam je LB."""
    proxy(hops=1)
    request = request_with({"X-Forwarded-For": "1.2.3.4, 35.191.0.1"}, peer="10.0.0.1")
    assert client_ip(request) == "1.2.3.4"


def test_short_forwarded_header_falls_back_to_the_peer(proxy):
    proxy(hops=2)
    request = request_with({"X-Forwarded-For": "1.2.3.4"}, peer="10.0.0.1")
    assert client_ip(request) == "10.0.0.1"


def test_missing_forwarded_header_falls_back_to_the_peer(proxy):
    proxy(hops=0)
    assert client_ip(request_with({}, peer="10.0.0.1")) == "10.0.0.1"


def test_missing_client_does_not_crash(proxy):
    proxy(trust=False)
    assert client_ip(request_with({}, peer=None)) == "unknown"


def test_two_clients_behind_one_proxy_do_not_share_a_limit(proxy):
    """Toto je dôvod, prečo to riešime: inak jeden robot zavrie chat všetkým."""
    proxy(hops=0)
    first = client_ip(request_with({"X-Forwarded-For": "1.2.3.4"}, peer="10.0.0.1"))
    second = client_ip(request_with({"X-Forwarded-For": "5.6.7.8"}, peer="10.0.0.1"))
    assert first != second


# --------------------------------------------------------------------------- #
# Počítadlo v okne
# --------------------------------------------------------------------------- #

def test_hits_are_allowed_up_to_the_limit():
    limiter = WindowRateLimiter(limit=3, window_seconds=60)
    assert [limiter.hit("a") for _ in range(4)] == [True, True, True, False]


def test_keys_are_counted_separately():
    limiter = WindowRateLimiter(limit=1, window_seconds=60)
    assert limiter.hit("a") is True
    assert limiter.hit("b") is True
    assert limiter.hit("a") is False


def test_blocked_hit_does_not_extend_the_window():
    """Zamietnutý pokus sa nesmie zaznačiť, inak by sa okno predlžovalo navždy."""
    limiter = WindowRateLimiter(limit=1, window_seconds=0.05)
    assert limiter.hit("a") is True
    assert limiter.hit("a") is False
    import time

    time.sleep(0.06)
    assert limiter.hit("a") is True


def test_window_slides():
    limiter = WindowRateLimiter(limit=2, window_seconds=0.05)
    assert limiter.hit("a") is True
    assert limiter.hit("a") is True
    assert limiter.hit("a") is False

    import time

    time.sleep(0.06)
    assert limiter.hit("a") is True


def test_reset_clears_everything():
    limiter = WindowRateLimiter(limit=1, window_seconds=60)
    limiter.hit("a")
    limiter.reset()
    assert limiter.hit("a") is True


def test_old_keys_are_dropped_so_memory_does_not_grow():
    limiter = WindowRateLimiter(limit=1, window_seconds=0.01)
    for i in range(50):
        limiter.hit(f"session-{i}")

    import time

    time.sleep(0.02)
    limiter.hit("novy")

    # Po vyčistení ostane len kľúč z aktuálneho okna.
    assert list(limiter._hits) == ["novy"]
