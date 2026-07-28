"""Letter generation API router."""

import io

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.candidate import Candidate
from app.models.generated_letter import GeneratedLetter
from app.models.user import User, UserRole
from app.services.letter_generator import LETTER_TEMPLATES, letter_generator

router = APIRouter(prefix="/letters", tags=["letters"])


class GenerateLetterRequest(BaseModel):
    candidate_id: int
    letter_type: str
    program: str | None = None
    candidate_data: dict = {}
    custom_instructions: str | None = None


class UpdateLetterRequest(BaseModel):
    content: str


@router.get("/templates")
async def list_templates(
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """List available letter templates."""
    return letter_generator.get_available_templates()


@router.post("/generate")
async def generate_letter(
    body: GenerateLetterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Generate a new letter for a candidate."""
    # Verify candidate exists
    result = await db.execute(
        select(Candidate).where(Candidate.id == body.candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat non trouve")

    if body.letter_type not in [lt.value for lt in LETTER_TEMPLATES.keys()]:
        raise HTTPException(
            status_code=400,
            detail=f"Type de lettre invalide: {body.letter_type}",
        )

    # Merge candidate DB data with provided data
    merged_data = {
        "full_name": f"{candidate.first_name} {candidate.last_name}",
        "email": candidate.email,
        "phone": candidate.phone or "",
        "nationality": candidate.nationality or "",
        "passport_number": candidate.passport_number or "",
        "current_city": candidate.current_city or "",
        **body.candidate_data,
    }

    # Generate
    result = await letter_generator.generate(
        letter_type=body.letter_type,
        candidate_data=merged_data,
        program=body.program,
        custom_instructions=body.custom_instructions,
    )

    title = LETTER_TEMPLATES.get(body.letter_type, {}).get("title", "Lettre")

    # Save
    letter = GeneratedLetter(
        candidate_id=body.candidate_id,
        created_by=current_user.id,
        letter_type=body.letter_type,
        title=title,
        content=result["content"],
        program=body.program,
        generation_method=result["method"],
        input_data=merged_data,
    )
    db.add(letter)
    await db.commit()
    await db.refresh(letter)

    return {
        "id": letter.id,
        "title": letter.title,
        "content": letter.content,
        "letter_type": letter.letter_type,
        "generation_method": letter.generation_method,
        "program": letter.program,
        "created_at": letter.created_at.isoformat() if letter.created_at else None,
    }


@router.get("/candidate/{candidate_id}")
async def list_candidate_letters(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """List all letters generated for a candidate."""
    result = await db.execute(
        select(GeneratedLetter)
        .where(GeneratedLetter.candidate_id == candidate_id)
        .order_by(GeneratedLetter.created_at.desc())
    )
    letters = result.scalars().all()
    return [
        {
            "id": letter.id,
            "title": letter.title,
            "letter_type": letter.letter_type,
            "generation_method": letter.generation_method,
            "program": letter.program,
            "is_edited": letter.is_edited,
            "version": letter.version,
            "created_at": letter.created_at.isoformat() if letter.created_at else None,
        }
        for letter in letters
    ]


@router.get("/{letter_id}")
async def get_letter(
    letter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Get a single generated letter with full content."""
    result = await db.execute(
        select(GeneratedLetter).where(GeneratedLetter.id == letter_id)
    )
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(status_code=404, detail="Lettre non trouvee")

    return {
        "id": letter.id,
        "candidate_id": letter.candidate_id,
        "title": letter.title,
        "content": letter.content,
        "letter_type": letter.letter_type,
        "generation_method": letter.generation_method,
        "program": letter.program,
        "is_edited": letter.is_edited,
        "version": letter.version,
        "input_data": letter.input_data,
        "created_at": letter.created_at.isoformat() if letter.created_at else None,
        "updated_at": letter.updated_at.isoformat() if letter.updated_at else None,
    }


@router.put("/{letter_id}")
async def update_letter(
    letter_id: int,
    body: UpdateLetterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Edit a letter's content manually before export."""
    result = await db.execute(
        select(GeneratedLetter).where(GeneratedLetter.id == letter_id)
    )
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(status_code=404, detail="Lettre non trouvee")

    letter.content = body.content
    letter.is_edited = True
    letter.version += 1
    await db.commit()
    await db.refresh(letter)

    return {
        "id": letter.id,
        "title": letter.title,
        "content": letter.content,
        "is_edited": letter.is_edited,
        "version": letter.version,
        "updated_at": letter.updated_at.isoformat() if letter.updated_at else None,
    }


@router.get("/{letter_id}/pdf")
async def export_letter_pdf(
    letter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Export a letter as a professionally formatted PDF."""
    result = await db.execute(
        select(GeneratedLetter).where(GeneratedLetter.id == letter_id)
    )
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(status_code=404, detail="Lettre non trouvee")

    pdf_bytes = _render_letter_pdf(letter.title, letter.content)

    filename = f"lettre_{letter.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{letter_id}")
async def delete_letter(
    letter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.consultant)),
):
    """Delete a generated letter."""
    result = await db.execute(
        select(GeneratedLetter).where(GeneratedLetter.id == letter_id)
    )
    letter = result.scalar_one_or_none()
    if not letter:
        raise HTTPException(status_code=404, detail="Lettre non trouvee")

    await db.delete(letter)
    await db.commit()
    return {"detail": "Lettre supprimee"}


def _render_letter_pdf(title: str, content: str) -> bytes:
    """Render letter content to a professional PDF layout."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "LetterTitle",
        parent=styles["Heading1"],
        fontSize=14,
        spaceAfter=20,
    )
    body_style = ParagraphStyle(
        "LetterBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
    )

    flowables = [Paragraph(title, title_style), Spacer(1, 0.5 * cm)]
    for paragraph in content.split("\n"):
        if paragraph.strip():
            # Escape XML special chars for reportlab
            safe = (
                paragraph.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            flowables.append(Paragraph(safe, body_style))
        else:
            flowables.append(Spacer(1, 0.3 * cm))

    doc.build(flowables)
    return buffer.getvalue()
