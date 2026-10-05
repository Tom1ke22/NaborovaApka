"""Úklid súborov CV, ku ktorým už neexistuje uchádzač.

Súbor ostane bez vlastníka, keď:
- zlyhalo zmazanie súboru pri GDPR výmaze (DB je už čistá),
- prihláška sa po uložení CV neuložila a zlyhal aj okamžitý úklid,
- niekto zmazal uchádzačov priamo v DB.

Spúšťa sa pravidelne cez `scripts/cleanup_orphan_cvs.py` (cron, Cloud
Scheduler + Cloud Run job).
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select

from app.core.storage import StorageBackend
from app.db.base import utcnow
from app.models.applicant import Applicant

logger = logging.getLogger(__name__)

# Čerstvé súbory nechávame. Prihláška ukladá CV skôr než riadok v DB, takže
# súbor bez uchádzača môže byť len prihláška, ktorá sa práve ukladá.
MIN_ORPHAN_AGE = timedelta(hours=1)


@dataclass
class CleanupResult:
    deleted: list[str] = field(default_factory=list)
    kept_recent: int = 0
    failed: list[str] = field(default_factory=list)


async def delete_orphan_cvs(
    db, storage: StorageBackend, *, dry_run: bool = False
) -> CleanupResult:
    """Zmaž CV staršie než MIN_ORPHAN_AGE, na ktoré neukazuje žiadny uchádzač."""
    referenced = set(
        (await db.scalars(
            select(Applicant.cv_storage_path).where(Applicant.cv_storage_path.is_not(None))
        )).all()
    )
    cutoff = utcnow() - MIN_ORPHAN_AGE
    result = CleanupResult()

    for stored in await storage.list_files():
        if stored.path in referenced:
            continue
        if stored.modified_at > cutoff:
            result.kept_recent += 1
            continue
        if dry_run:
            result.deleted.append(stored.path)
            continue
        try:
            await storage.delete(stored.path)
            result.deleted.append(stored.path)
        except Exception:  # noqa: BLE001 — jeden zlý súbor nesmie zastaviť úklid
            logger.warning("Osirelé CV sa nepodarilo zmazať: %s", stored.path, exc_info=True)
            result.failed.append(stored.path)

    logger.info(
        "Úklid CV: zmazaných %s, čerstvých ponechaných %s, zlyhalo %s%s",
        len(result.deleted), result.kept_recent, len(result.failed),
        " (dry run)" if dry_run else "",
    )
    return result
