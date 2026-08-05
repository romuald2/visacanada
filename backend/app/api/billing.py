"""Billing API: invoices, payments, reminders, financial dashboard."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_role
from app.core.database import get_db
from app.models.billing import (
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    LineItemKind,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from app.models.candidate import Candidate
from app.models.user import User, UserRole
from app.services.billing_service import billing_service
from app.services.smtp_sender import smtp_sender

router = APIRouter(prefix="/billing", tags=["billing"])

_roles = require_role(UserRole.admin, UserRole.consultant)


class LineItemInput(BaseModel):
    kind: str = "service_fee"
    description: str
    quantity: int = 1
    unit_price: float


class CreateInvoiceRequest(BaseModel):
    candidate_id: int
    dossier_id: int | None = None
    line_items: list[LineItemInput]
    due_date: datetime | None = None
    notes: str | None = None


class RecordPaymentRequest(BaseModel):
    amount: float
    method: str = "manual"


async def _serialize_invoice(invoice: Invoice, db: AsyncSession) -> dict:
    items_result = await db.execute(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice.id)
    )
    items = items_result.scalars().all()
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "candidate_id": invoice.candidate_id,
        "dossier_id": invoice.dossier_id,
        "status": invoice.status.value,
        "currency": invoice.currency,
        "subtotal": invoice.subtotal,
        "tax": invoice.tax,
        "total": invoice.total,
        "amount_paid": invoice.amount_paid,
        "balance": round(invoice.total - invoice.amount_paid, 2),
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "notes": invoice.notes,
        "line_items": [
            {
                "id": it.id,
                "kind": it.kind.value,
                "description": it.description,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "amount": it.amount,
            }
            for it in items
        ],
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
    }


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Create an invoice with line items; totals are computed automatically."""
    cand = await db.execute(select(Candidate).where(Candidate.id == body.candidate_id))
    if cand.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Candidat non trouve")

    if not body.line_items:
        raise HTTPException(status_code=400, detail="Au moins une ligne requise")

    # Validate line item kinds
    items_data = []
    for li in body.line_items:
        try:
            kind = LineItemKind(li.kind)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Type de ligne invalide: {li.kind}")
        items_data.append(
            {"kind": kind.value, "quantity": li.quantity, "unit_price": li.unit_price}
        )

    totals = billing_service.compute_totals(items_data)

    # Sequence number
    count_result = await db.execute(select(func.count()).select_from(Invoice))
    seq = (count_result.scalar() or 0) + 1

    invoice = Invoice(
        invoice_number=billing_service.generate_invoice_number(seq),
        candidate_id=body.candidate_id,
        dossier_id=body.dossier_id,
        created_by=current_user.id,
        status=InvoiceStatus.draft,
        currency=billing_service._currency,
        subtotal=totals["subtotal"],
        tax=totals["tax"],
        total=totals["total"],
        due_date=body.due_date,
        notes=body.notes,
    )
    db.add(invoice)
    await db.flush()

    for li in body.line_items:
        db.add(
            InvoiceLineItem(
                invoice_id=invoice.id,
                kind=LineItemKind(li.kind),
                description=li.description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                amount=round(li.quantity * li.unit_price, 2),
            )
        )
    await db.commit()
    await db.refresh(invoice)
    return await _serialize_invoice(invoice, db)


@router.get("/invoices")
async def list_invoices(
    candidate_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """List invoices with optional candidate/status filters."""
    stmt = select(Invoice)
    if candidate_id is not None:
        stmt = stmt.where(Invoice.candidate_id == candidate_id)
    if status_filter is not None:
        try:
            stmt = stmt.where(Invoice.status == InvoiceStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Statut invalide")
    stmt = stmt.order_by(Invoice.created_at.desc())
    result = await db.execute(stmt)
    invoices = result.scalars().all()
    return [await _serialize_invoice(inv, db) for inv in invoices]


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Get a single invoice with line items."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture non trouvee")
    return await _serialize_invoice(invoice, db)


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Mark a draft invoice as sent."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture non trouvee")
    if invoice.status == InvoiceStatus.draft:
        invoice.status = InvoiceStatus.sent
        await db.commit()
    return {"detail": "Facture envoyee", "status": invoice.status.value}


@router.post("/invoices/{invoice_id}/payment-intent")
async def create_payment_intent(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Create a Stripe payment intent for the invoice balance (or mock)."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture non trouvee")

    balance = round(invoice.total - invoice.amount_paid, 2)
    if balance <= 0:
        raise HTTPException(status_code=400, detail="Facture deja reglee")

    intent = await billing_service.create_payment_intent(
        balance,
        invoice.currency,
        metadata={"invoice_id": invoice.id, "invoice_number": invoice.invoice_number},
    )
    return intent


@router.post("/invoices/{invoice_id}/payments", status_code=status.HTTP_201_CREATED)
async def record_payment(
    invoice_id: int,
    body: RecordPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Record a payment against an invoice and update its status."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture non trouvee")

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Montant invalide")

    try:
        method = PaymentMethod(body.method)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Methode invalide: {body.method}")

    payment = Payment(
        invoice_id=invoice.id,
        amount=body.amount,
        currency=invoice.currency,
        method=method,
        status=PaymentStatus.succeeded,
        recorded_by=current_user.id,
    )
    db.add(payment)

    invoice.amount_paid = round(invoice.amount_paid + body.amount, 2)
    invoice.status = InvoiceStatus(
        billing_service.apply_payment_status(invoice.total, invoice.amount_paid)
    )
    await db.commit()
    await db.refresh(invoice)
    return {
        "payment_id": payment.id,
        "invoice_status": invoice.status.value,
        "amount_paid": invoice.amount_paid,
        "balance": round(invoice.total - invoice.amount_paid, 2),
    }


@router.get("/reminders")
async def payment_reminders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """List invoices needing a payment reminder (sent/overdue with a balance).

    Marks past-due sent invoices as overdue.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Invoice).where(
            Invoice.status.in_(
                [InvoiceStatus.sent, InvoiceStatus.partially_paid, InvoiceStatus.overdue]
            )
        )
    )
    invoices = result.scalars().all()

    reminders = []
    for inv in invoices:
        balance = round(inv.total - inv.amount_paid, 2)
        if balance <= 0:
            continue
        is_overdue = False
        if inv.due_date is not None:
            due = inv.due_date.replace(tzinfo=None) if inv.due_date.tzinfo else inv.due_date
            if due < now:
                is_overdue = True
                if inv.status != InvoiceStatus.overdue:
                    inv.status = InvoiceStatus.overdue
        reminders.append(
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "candidate_id": inv.candidate_id,
                "balance": balance,
                "is_overdue": is_overdue,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
            }
        )
    await db.commit()
    return reminders


def _reminder_subject(invoice_number: str, is_overdue: bool) -> str:
    """Subject line for a payment reminder (candidate-facing, accented)."""
    if is_overdue:
        return f"Facture {invoice_number} en retard de paiement"
    return f"Rappel de paiement - facture {invoice_number}"


def _reminder_body(
    first_name: str, invoice: Invoice, balance: float, is_overdue: bool
) -> str:
    """Reminder body. Carries no dossier detail beyond the amount due."""
    due = invoice.due_date.date().isoformat() if invoice.due_date else "non precisee"
    opening = (
        f"La facture {invoice.invoice_number} est arrivée à échéance le {due} "
        "et demeure impayée."
        if is_overdue
        else f"La facture {invoice.invoice_number} est payable au plus tard le {due}."
    )
    return (
        f"Bonjour {first_name},\n\n"
        f"{opening}\n\n"
        f"Solde à régler : {balance:.2f} {invoice.currency.upper()}\n\n"
        "Si le paiement a déjà été effectué, vous pouvez ignorer ce message.\n\n"
        "Cordialement,\n"
        "L'équipe VisaCanada"
    )


@router.post("/reminders/send")
async def send_payment_reminders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Email a payment reminder for every invoice with an outstanding balance.

    Kept separate from ``GET /billing/reminders``: listing what is due must stay
    free of side effects, so the actual sending is its own explicit action.

    Best-effort per invoice — one unreachable address does not stop the rest.
    Without a configured SMTP relay nothing is sent and the response says so.
    """
    if not smtp_sender.is_configured:
        return {
            "detail": "SMTP non configure, aucun rappel envoye",
            "sent": 0,
            "failed": 0,
            "skipped": 0,
        }

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Invoice).where(
            Invoice.status.in_(
                [InvoiceStatus.sent, InvoiceStatus.partially_paid, InvoiceStatus.overdue]
            )
        )
    )
    invoices = result.scalars().all()

    sent = failed = skipped = 0
    for inv in invoices:
        balance = round(inv.total - inv.amount_paid, 2)
        if balance <= 0:
            continue

        cres = await db.execute(select(Candidate).where(Candidate.id == inv.candidate_id))
        candidate = cres.scalar_one_or_none()
        if candidate is None or not candidate.email:
            skipped += 1
            continue

        is_overdue = False
        if inv.due_date is not None:
            due = inv.due_date.replace(tzinfo=None) if inv.due_date.tzinfo else inv.due_date
            is_overdue = due < now

        res = await smtp_sender.send(
            to=candidate.email,
            subject=_reminder_subject(inv.invoice_number, is_overdue),
            body=_reminder_body(candidate.first_name, inv, balance, is_overdue),
        )
        if res.get("status") == "sent":
            sent += 1
        else:
            failed += 1

    return {"detail": "Rappels traites", "sent": sent, "failed": failed, "skipped": skipped}


@router.get("/dashboard")
async def financial_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_roles),
):
    """Financial overview: totals invoiced, collected, outstanding, by status."""
    result = await db.execute(select(Invoice))
    invoices = result.scalars().all()

    total_invoiced = round(sum(i.total for i in invoices), 2)
    total_collected = round(sum(i.amount_paid for i in invoices), 2)
    outstanding = round(total_invoiced - total_collected, 2)

    by_status: dict[str, int] = {}
    for i in invoices:
        by_status[i.status.value] = by_status.get(i.status.value, 0) + 1

    return {
        "total_invoiced": total_invoiced,
        "total_collected": total_collected,
        "outstanding": outstanding,
        "invoice_count": len(invoices),
        "by_status": by_status,
        "stripe_enabled": billing_service.stripe_available,
    }
