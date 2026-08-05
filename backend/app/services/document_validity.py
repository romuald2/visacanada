"""Document validity rules and expiry computation.

Populates ``Document.expires_at`` automatically so the alert engine has
material to scan. Two paths:

1. If OCR (or a manual correction) extracted an explicit expiry date
   (e.g. a passport's DateOfExpiration), use it directly.
2. Otherwise, derive an expiry from the document's issue date plus a
   validity window that depends on the document type (e.g. a language
   test is valid 24 months, an ECA 60 months, a medical exam 12 months).

All datetimes are naive UTC to match the rest of the codebase.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.models.document import DocumentType

# Validity windows in days, keyed by document type. A type absent from this
# map has no derivable validity (expiry can still come from an explicit
# extracted date).
VALIDITY_DAYS: dict[DocumentType, int] = {
    # IELTS / CELPIP / TEF language results: valid 2 years.
    DocumentType.language_test: 730,
    # Educational Credential Assessment (ECA): valid 5 years.
    DocumentType.education_credential: 1825,
    # Upfront medical exam (IME): valid 12 months.
    DocumentType.medical_exam: 365,
    # Police / security certificate: commonly treated as valid ~6 months
    # for immigration purposes.
    DocumentType.police_certificate: 180,
}

# Keys under an extracted payload that may hold an explicit expiry date.
_EXPIRY_KEYS = ("expiry_date", "date_of_expiration", "expiration_date", "expires_at")
# Keys that may hold an issue / emission date to derive expiry from.
_ISSUE_KEYS = ("issue_date", "date_of_issue", "issued_at", "statement_date", "test_date")

# Accepted date formats, tried in order.
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def parse_date(value: Any) -> datetime | None:
    """Best-effort parse of a date from OCR/manual values. Returns naive UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _naive_utc(value)
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    # Handle trailing Z on ISO strings.
    candidate = text[:-1] if text.endswith("Z") else text
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def _unwrap(field: Any) -> Any:
    """OCR fields are often {"value": ..., "confidence": ...}; unwrap them."""
    if isinstance(field, dict) and "value" in field:
        return field.get("value")
    return field


def _search_keys(fields: dict, keys: tuple[str, ...]) -> datetime | None:
    for key in keys:
        if key in fields:
            parsed = parse_date(_unwrap(fields[key]))
            if parsed is not None:
                return parsed
    return None


def extract_dates(extracted_data: Any) -> tuple[datetime | None, datetime | None]:
    """Pull (issue_date, expiry_date) out of an extracted payload.

    Accepts either a dict or a JSON string (as stored on the model). Looks in
    the top level and under a nested ``fields`` object.
    """
    if extracted_data is None:
        return None, None
    if isinstance(extracted_data, str):
        try:
            extracted_data = json.loads(extracted_data)
        except (json.JSONDecodeError, ValueError):
            return None, None
    if not isinstance(extracted_data, dict):
        return None, None

    # Merge top-level and nested "fields" for searching.
    search_space: dict[str, Any] = {}
    fields = extracted_data.get("fields")
    if isinstance(fields, dict):
        search_space.update(fields)
    search_space.update(
        {k: v for k, v in extracted_data.items() if k != "fields"}
    )

    issue = _search_keys(search_space, _ISSUE_KEYS)
    expiry = _search_keys(search_space, _EXPIRY_KEYS)
    return issue, expiry


def compute_expiry(
    document_type: DocumentType,
    issue_date: datetime | None,
    explicit_expiry: datetime | None = None,
) -> datetime | None:
    """Compute a document's expiry (naive UTC).

    Precedence: an explicit expiry date always wins; otherwise derive from
    ``issue_date`` + the type's validity window. Returns None when neither
    is available or the type has no known validity window.
    """
    if explicit_expiry is not None:
        return _naive_utc(explicit_expiry)

    if issue_date is None:
        return None

    days = VALIDITY_DAYS.get(document_type)
    if days is None:
        return None

    return _naive_utc(issue_date) + timedelta(days=days)


def compute_expiry_from_extraction(
    document_type: DocumentType,
    extracted_data: Any,
) -> datetime | None:
    """Convenience: derive expiry directly from an extracted payload."""
    issue, expiry = extract_dates(extracted_data)
    return compute_expiry(document_type, issue, explicit_expiry=expiry)
