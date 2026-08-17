#!/bin/sh
set -e

echo "[startup] Čakám na databázu..."
python - << 'PYEOF'
import asyncio, os, sys

async def wait_for_db():
    import asyncpg
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    for attempt in range(30):
        try:
            conn = await asyncpg.connect(url)
            await conn.close()
            print("[startup] Databáza je ready.")
            return
        except Exception as e:
            print(f"[startup] Pokus {attempt + 1}/30: {e}")
            await asyncio.sleep(1)
    print("[startup] Databáza nedostupná po 30s.")
    sys.exit(1)

asyncio.run(wait_for_db())
PYEOF

echo "[startup] Spúšťam migrácie..."
alembic upgrade head
echo "[startup] Migrácie hotové."

exec "$@"
