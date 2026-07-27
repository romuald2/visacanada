"""Script to seed IMM checklists into the database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.program import Program
from app.models.program_requirement import ProgramRequirement, RequirementPriority
from app.seeds.requirements import REQUIREMENTS_SEED


async def seed_requirements(session: AsyncSession) -> int:
    """Insert requirements from seed data.

    Returns the number of requirements created.
    """
    created = 0

    for program_code, requirements in REQUIREMENTS_SEED.items():
        # Find the program by code
        stmt = select(Program).where(Program.code == program_code)
        result = await session.execute(stmt)
        program = result.scalar_one_or_none()

        if program is None:
            print(f"  Programme '{program_code}' non trouvé, skip.")
            continue

        for req_data in requirements:
            # Check if requirement already exists
            stmt = select(ProgramRequirement).where(
                ProgramRequirement.program_id == program.id,
                ProgramRequirement.document_name == req_data["document_name"],
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is None:
                requirement = ProgramRequirement(
                    program_id=program.id,
                    document_type=req_data["document_type"],
                    document_name=req_data["document_name"],
                    description=req_data["description"],
                    priority=RequirementPriority(req_data["priority"]),
                    imm_form_reference=req_data["imm_form_reference"],
                    sort_order=req_data["sort_order"],
                    is_active=True,
                )
                session.add(requirement)
                created += 1

    await session.commit()
    return created


async def main():
    """Run the seed script."""
    async with async_session_factory() as session:
        created = await seed_requirements(session)
        total = sum(len(reqs) for reqs in REQUIREMENTS_SEED.values())
        print(
            f"Seeding terminé: {created} exigences créées "
            f"sur {total} définies ({len(REQUIREMENTS_SEED)} programmes)."
        )


if __name__ == "__main__":
    asyncio.run(main())
