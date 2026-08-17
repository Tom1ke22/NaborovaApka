"""
Pridanie novej firmy + admin účtu.

Spustenie:
    docker compose exec backend python scripts/create_company.py

Alebo s argumentmi:
    docker compose exec backend python scripts/create_company.py \
        --name "Firma s.r.o." --slug firma-sro \
        --admin-email admin@firma.sk --admin-password HesloTu123
"""
import asyncio
import sys
import argparse

sys.path.insert(0, "/app")

from sqlalchemy import select
from app.core.security import hash_password
from app.db.base import AsyncSessionLocal
from app.models.company import Company
from app.models.admin import AdminUser


async def main(name: str, slug: str, admin_email: str, admin_password: str, role: str = "recruiter"):
    async with AsyncSessionLocal() as db:
        # Overenie unikátnosti slug
        existing = await db.execute(select(Company).where(Company.slug == slug))
        if existing.scalar_one_or_none():
            print(f"[CHYBA] Firma so slug '{slug}' už existuje.")
            return

        # Overenie unikátnosti emailu
        existing_user = await db.execute(select(AdminUser).where(AdminUser.email == admin_email))
        if existing_user.scalar_one_or_none():
            print(f"[CHYBA] Admin s emailom '{admin_email}' už existuje.")
            return

        company = Company(name=name, slug=slug)
        db.add(company)
        await db.flush()

        admin = AdminUser(
            company_id=company.id,
            email=admin_email,
            password_hash=hash_password(admin_password),
            role=role,
        )
        db.add(admin)
        await db.commit()

        print(f"[OK] Firma '{name}' vytvorená (slug: {slug})")
        print(f"[OK] Admin účet: {admin_email} / {admin_password}")
        print(f"[OK] Verejná URL: /<host>/{slug}/positions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vytvorenie firmy a admin účtu")
    parser.add_argument("--name", required=True, help="Názov firmy")
    parser.add_argument("--slug", required=True, help="URL slug (napr. firma-sro)")
    parser.add_argument("--admin-email", required=True, help="Email admin účtu")
    parser.add_argument("--admin-password", required=True, help="Heslo admin účtu")
    parser.add_argument("--role", default="recruiter", help="Rola admin účtu (default: recruiter)")
    args = parser.parse_args()

    asyncio.run(main(
        name=args.name,
        slug=args.slug,
        admin_email=args.admin_email,
        admin_password=args.admin_password,
        role=args.role,
    ))
