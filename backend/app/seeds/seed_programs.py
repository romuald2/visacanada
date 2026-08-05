"""Script to seed IRCC immigration programs into the database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.program import Program
from app.seeds import PROGRAMS_SEED


async def seed_programs(session: AsyncSession) -> int:
    """Insert or update IRCC programs from seed data.

    Returns the number of programs created.
    """
    created = 0

    for data in PROGRAMS_SEED:
        code = data["code"]
        stmt = select(Program).where(Program.code == code)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            program = Program(
                code=code,
                name=data["name"],
                category=data["category"],
                description=data["description"],
                processing_time_days=data["processing_time_days"],
                government_fee=data["government_fee"],
                documents_required=data["documents_required"],
                eligibility_criteria=data["eligibility_criteria"],
                is_active=True,
            )
            session.add(program)
            created += 1
        else:
            existing.name = data["name"]
            existing.category = data["category"]
            existing.description = data["description"]
            existing.processing_time_days = data["processing_time_days"]
            existing.government_fee = data["government_fee"]
            existing.documents_required = data["documents_required"]
            existing.eligibility_criteria = data["eligibility_criteria"]

    await session.commit()
    return created


async def main():
    """Run the seed script."""
    async with async_session_factory() as session:
        created = await seed_programs(session)
        print(f"Seeding terminé: {created} programmes créés, "
              f"{len(PROGRAMS_SEED) - created} programmes mis à jour.")


if __name__ == "__main__":
    asyncio.run(main())
