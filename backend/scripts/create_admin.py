"""
Spustenie: docker compose exec backend python scripts/create_admin.py
"""
import asyncio
import sys

from sqlalchemy import select

sys.path.insert(0, "/app")

from app.core.security import hash_password
from app.db.base import AsyncSessionLocal
from app.models.admin import AdminUser


async def main():
    email = input("Email: ").strip()
    password = input("Heslo: ").strip()
    role = input("Rola [recruiter]: ").strip() or "recruiter"

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(AdminUser).where(AdminUser.email == email))
        if existing.scalar_one_or_none():
            print(f"Admin s emailom {email} už existuje.")
            return

        user = AdminUser(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        await db.commit()
        print(f"Admin {email} ({role}) bol vytvorený.")


asyncio.run(main())
