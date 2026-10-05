"""
Zmaže súbory CV, ku ktorým už neexistuje uchádzač (pozri app/core/cv_cleanup.py).

Spustenie:
    docker compose exec backend python scripts/cleanup_orphan_cvs.py --dry-run
    docker compose exec backend python scripts/cleanup_orphan_cvs.py

Na produkcii ho spúšťaj pravidelne (napr. raz denne cez Cloud Scheduler +
Cloud Run job s tým istým image a env premennými ako backend).
"""
import argparse
import asyncio
import sys

sys.path.insert(0, "/app")

from app.core.cv_cleanup import delete_orphan_cvs
from app.core.storage import get_storage
from app.db.base import AsyncSessionLocal


async def main(dry_run: bool) -> int:
    async with AsyncSessionLocal() as db:
        result = await delete_orphan_cvs(db, get_storage(), dry_run=dry_run)

    label = "Na zmazanie" if dry_run else "Zmazané"
    print(f"{label}: {len(result.deleted)}")
    for path in result.deleted:
        print(f"  {path}")
    print(f"Ponechané (mladšie ako hodina): {result.kept_recent}")
    if result.failed:
        print(f"Zlyhalo: {len(result.failed)}")
        for path in result.failed:
            print(f"  {path}")
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="len vypíš, nič nemaž")
    sys.exit(asyncio.run(main(parser.parse_args().dry_run)))
