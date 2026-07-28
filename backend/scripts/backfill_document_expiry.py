"""One-shot backfill: populate Document.expires_at from extracted_data.

For every document that has extraction data but no expiry set, derive an
expiry (explicit extracted date, or issue date + type validity window) and
persist it. Safe to re-run; only fills missing values.

Usage (from backend/):
    python -m scripts.backfill_document_expiry          # apply
    python -m scripts.backfill_document_expiry --dry-run
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.document import Document
from app.services.document_validity import compute_expiry_from_extraction


async def backfill(dry_run: bool = False) -> dict:
    stats = {"scanned": 0, "updated": 0, "skipped_no_data": 0, "no_expiry": 0}

    async with async_session_factory() as session:
        result = await session.execute(
            select(Document).where(Document.expires_at.is_(None))
        )
        documents = result.scalars().all()

        for doc in documents:
            stats["scanned"] += 1
            if not doc.extracted_data:
                stats["skipped_no_data"] += 1
                continue

            expiry = compute_expiry_from_extraction(
                doc.document_type, doc.extracted_data
            )
            if expiry is None:
                stats["no_expiry"] += 1
                continue

            if not dry_run:
                doc.expires_at = expiry
            stats["updated"] += 1

        if not dry_run:
            await session.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Document.expires_at")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing.",
    )
    args = parser.parse_args()

    stats = asyncio.run(backfill(dry_run=args.dry_run))
    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"[{mode}] backfill_document_expiry:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
