"""Testy orchestrácie hodnotenia. Bez DB, bez AI."""

from types import SimpleNamespace

from tests.conftest import run

from app.core.ai import evaluate as evaluate_module
from app.core.ai.evaluate import _read_cv_text, evaluate_applicant


class FakeStorage:
    def __init__(self, data: bytes | None = None, *, fail: bool = False) -> None:
        self._data = data
        self._fail = fail

    async def load(self, storage_path: str) -> bytes | None:
        if self._fail:
            raise OSError("úložisko je nedostupné")
        return self._data


def use_storage(monkeypatch, storage) -> None:
    monkeypatch.setattr(evaluate_module, "get_storage", lambda: storage)


# --------------------------------------------------------------------------- #
# Načítanie CV
# --------------------------------------------------------------------------- #

def test_missing_path_gives_empty_text():
    assert run(_read_cv_text(None)) == ""
    assert run(_read_cv_text("")) == ""


def test_missing_file_gives_empty_text(monkeypatch):
    use_storage(monkeypatch, FakeStorage(None))
    assert run(_read_cv_text("cvs/chyba.pdf")) == ""


def test_broken_storage_gives_empty_text_instead_of_raising(monkeypatch):
    use_storage(monkeypatch, FakeStorage(fail=True))
    assert run(_read_cv_text("cvs/nieco.pdf")) == ""


def test_unsupported_format_gives_empty_text(monkeypatch):
    use_storage(monkeypatch, FakeStorage(b"obsah"))
    assert run(_read_cv_text("cvs/zivotopis.txt")) == ""


def test_corrupt_pdf_gives_empty_text(monkeypatch):
    use_storage(monkeypatch, FakeStorage(b"toto nie je PDF"))
    assert run(_read_cv_text("cvs/zivotopis.pdf")) == ""


def test_real_docx_is_read(monkeypatch):
    from tests.test_cv_text import build_docx

    use_storage(monkeypatch, FakeStorage(build_docx(["Kuchár, 3 roky praxe"])))
    assert "Kuchár, 3 roky praxe" in run(_read_cv_text("cvs/zivotopis.docx"))


# --------------------------------------------------------------------------- #
# Hlavná funkcia
# --------------------------------------------------------------------------- #

def test_disabled_ai_skips_evaluation_without_touching_db(monkeypatch):
    """Bez kľúča sa nesmie ani otvoriť databázová relácia."""
    def explode():
        raise AssertionError("databáza sa nemala otvoriť")

    monkeypatch.setattr(evaluate_module, "AsyncSessionLocal", explode)
    run(evaluate_applicant("11111111-1111-1111-1111-111111111111"))


def test_errors_are_swallowed_so_the_application_is_never_lost(monkeypatch):
    """Hodnotenie beží na pozadí po odoslaní prihlášky a nesmie nič vyhodiť."""
    monkeypatch.setattr(
        evaluate_module.settings.__class__,
        "ai_available",
        property(lambda self: True),
    )

    def explode():
        raise RuntimeError("databáza je nedostupná")

    monkeypatch.setattr(evaluate_module, "AsyncSessionLocal", explode)
    run(evaluate_applicant("11111111-1111-1111-1111-111111111111"))


def test_evaluation_stores_score_reasoning_and_breakdown(monkeypatch):
    """Celý reťazec: fakty od modelu → deterministické skóre → uložené polia."""
    from app.core.ai.schemas import Answer, ExperienceFact, ExtractedProfile, Fact, Source

    applicant = SimpleNamespace(
        id="a", position_id="p", cv_storage_path=None,
        ai_score=None, ai_score_reasoning=None, qualification_answers={},
    )
    requirements = SimpleNamespace(
        hygiene_minimum_required=True,
        health_certificate_required=False,
        experience_required=True,
        experience_years=2,
        education_level=None,
        slovak_language_level=None,
        foreign_language_level=None,
    )
    position = SimpleNamespace(id="p", requirements=requirements, ai_bot_instructions=None)

    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *exc): return False
        async def scalar(self, stmt):
            # Prvé volanie vráti uchádzača, druhé pozíciu.
            self._calls = getattr(self, "_calls", 0) + 1
            return applicant if self._calls == 1 else position
        async def scalars(self, stmt):
            return SimpleNamespace(all=lambda: [])
        async def commit(self): self.committed = True

    profile = ExtractedProfile(
        hygiene_minimum=Fact(value=Answer.yes, source=Source.cv, evidence="osvedčenie"),
        experience=ExperienceFact(years=3, source=Source.cv),
        overall_fit=8,
    )

    async def fake_extract(**kwargs):
        return profile

    monkeypatch.setattr(
        evaluate_module.settings.__class__, "ai_available", property(lambda self: True)
    )
    monkeypatch.setattr(evaluate_module, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(evaluate_module, "extract_profile", fake_extract)

    run(evaluate_applicant("a"))

    assert applicant.ai_score is not None and 1 <= applicant.ai_score <= 10
    assert applicant.ai_score >= 8  # spĺňa obe zapnuté požiadavky
    assert "hygienické minimum" in applicant.ai_score_reasoning
    assert applicant.qualification_answers["score"]["score"] == applicant.ai_score
    assert applicant.qualification_answers["profile"]["overall_fit"] == 8


def test_missing_profile_leaves_applicant_unscored(monkeypatch):
    applicant = SimpleNamespace(
        id="a", position_id="p", cv_storage_path=None,
        ai_score=None, ai_score_reasoning=None, qualification_answers={},
    )
    position = SimpleNamespace(id="p", requirements=None, ai_bot_instructions=None)

    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *exc): return False
        async def scalar(self, stmt):
            self._calls = getattr(self, "_calls", 0) + 1
            return applicant if self._calls == 1 else position
        async def scalars(self, stmt):
            return SimpleNamespace(all=lambda: [])
        async def commit(self):
            raise AssertionError("bez faktov sa nemá nič ukladať")

    async def no_profile(**kwargs):
        return None

    monkeypatch.setattr(
        evaluate_module.settings.__class__, "ai_available", property(lambda self: True)
    )
    monkeypatch.setattr(evaluate_module, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(evaluate_module, "extract_profile", no_profile)

    run(evaluate_applicant("a"))
    assert applicant.ai_score is None
