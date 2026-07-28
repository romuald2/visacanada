"""Billing service: invoice math, Stripe abstraction, payment reconciliation.

Stripe is optional: when no secret key is configured, payment intents fall back
to a manual/mock flow so the rest of the billing workflow remains fully usable
(mirrors the AI/WhatsApp graceful-degradation pattern).
"""

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

# Quebec-style default sales tax (GST+QST ~14.975%); configurable per deployment.
DEFAULT_TAX_RATE = 0.14975


class BillingService:
    def __init__(self):
        self._stripe_key = settings.stripe_secret_key
        self._currency = settings.stripe_currency or "cad"

    @property
    def stripe_available(self) -> bool:
        return bool(self._stripe_key)

    def generate_invoice_number(self, seq: int) -> str:
        """Human-readable invoice number: INV-YYYY-000123."""
        year = datetime.now(timezone.utc).year
        return f"INV-{year}-{seq:06d}"

    def compute_totals(
        self, line_items: list[dict[str, Any]], tax_rate: float = DEFAULT_TAX_RATE
    ) -> dict[str, float]:
        """Compute subtotal, tax, and total from line items.

        Government fees (IRCC) are not taxable; service fees are.
        Each line item: {"kind": str, "quantity": int, "unit_price": float}.
        """
        subtotal = 0.0
        taxable_base = 0.0
        for item in line_items:
            qty = item.get("quantity", 1)
            amount = round(qty * float(item["unit_price"]), 2)
            subtotal += amount
            if item.get("kind") != "government_fee":
                taxable_base += amount

        tax = round(taxable_base * tax_rate, 2)
        total = round(subtotal + tax, 2)
        return {
            "subtotal": round(subtotal, 2),
            "tax": tax,
            "total": total,
        }

    async def create_payment_intent(
        self, amount: float, currency: str | None = None, metadata: dict | None = None
    ) -> dict[str, Any]:
        """Create a Stripe PaymentIntent, or a mock when Stripe isn't configured."""
        currency = currency or self._currency
        amount_cents = int(round(amount * 100))

        if not self.stripe_available:
            return {
                "provider": "mock",
                "id": f"pi_mock_{int(datetime.now(timezone.utc).timestamp())}",
                "client_secret": None,
                "amount": amount_cents,
                "currency": currency,
                "status": "requires_payment_method",
            }

        data = {
            "amount": str(amount_cents),
            "currency": currency,
        }
        for key, value in (metadata or {}).items():
            data[f"metadata[{key}]"] = str(value)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.stripe.com/v1/payment_intents",
                headers={"Authorization": f"Bearer {self._stripe_key}"},
                data=data,
            )
            response.raise_for_status()
            body = response.json()
            return {
                "provider": "stripe",
                "id": body["id"],
                "client_secret": body.get("client_secret"),
                "amount": body["amount"],
                "currency": body["currency"],
                "status": body["status"],
            }

    def apply_payment_status(
        self, total: float, amount_paid: float
    ) -> str:
        """Derive an invoice status from amounts paid."""
        if amount_paid <= 0:
            return "sent"
        if amount_paid >= total:
            return "paid"
        return "partially_paid"


# Singleton
billing_service = BillingService()
