"""Unit tests for document validity / expiry computation (no DB)."""

from datetime import datetime, timedelta

from app.models.document import DocumentType
from app.services.document_validity import (
    compute_expiry,
    compute_expiry_from_extraction,
    extract_dates,
    parse_date,
)


class TestParseDate:
    def test_iso(self):
        assert parse_date("2027-05-01") == datetime(2027, 5, 1)

    def test_iso_with_z(self):
        assert parse_date("2027-05-01T00:00:00Z") == datetime(2027, 5, 1)

    def test_slash_dmy(self):
        assert parse_date("01/05/2027") == datetime(2027, 5, 1)

    def test_textual_month(self):
        assert parse_date("01 Jan 2028") == datetime(2028, 1, 1)

    def test_empty_and_none(self):
        assert parse_date("") is None
        assert parse_date(None) is None

    def test_garbage(self):
        assert parse_date("not a date") is None

    def test_datetime_passthrough(self):
        dt = datetime(2027, 5, 1, 12, 0)
        assert parse_date(dt) == dt


class TestExtractDates:
    def test_nested_fields_expiry(self):
        payload = {
            "type": "passport",
            "fields": {
                "expiry_date": {"value": "2030-06-15", "confidence": 0.97},
            },
        }
        issue, expiry = extract_dates(payload)
        assert expiry == datetime(2030, 6, 15)

    def test_json_string_input(self):
        issue, expiry = extract_dates('{"fields": {"issue_date": {"value": "2024-01-01"}}}')
        assert issue == datetime(2024, 1, 1)

    def test_top_level_keys(self):
        issue, expiry = extract_dates({"issue_date": "2024-01-01", "expiry_date": "2026-01-01"})
        assert issue == datetime(2024, 1, 1)
        assert expiry == datetime(2026, 1, 1)

    def test_no_dates(self):
        assert extract_dates({"fields": {"first_name": {"value": "Alan"}}}) == (None, None)

    def test_bad_json(self):
        assert extract_dates("{not json") == (None, None)


class TestComputeExpiry:
    def test_explicit_expiry_wins(self):
        explicit = datetime(2030, 1, 1)
        issue = datetime(2024, 1, 1)
        # passport has no validity window, but explicit expiry still used
        assert compute_expiry(DocumentType.passport, issue, explicit) == explicit

    def test_language_test_derived_24_months(self):
        issue = datetime(2025, 1, 1)
        result = compute_expiry(DocumentType.language_test, issue)
        assert result == issue + timedelta(days=730)

    def test_medical_exam_derived_12_months(self):
        issue = datetime(2025, 1, 1)
        result = compute_expiry(DocumentType.medical_exam, issue)
        assert result == issue + timedelta(days=365)

    def test_eca_derived_5_years(self):
        issue = datetime(2025, 1, 1)
        result = compute_expiry(DocumentType.education_credential, issue)
        assert result == issue + timedelta(days=1825)

    def test_no_issue_no_explicit_returns_none(self):
        assert compute_expiry(DocumentType.language_test, None) is None

    def test_type_without_window_returns_none(self):
        # cv_resume has no validity window and no explicit expiry
        assert compute_expiry(DocumentType.cv_resume, datetime(2025, 1, 1)) is None


class TestComputeFromExtraction:
    def test_passport_explicit_expiry(self):
        payload = {"fields": {"expiry_date": {"value": "2031-12-31"}}}
        result = compute_expiry_from_extraction(DocumentType.passport, payload)
        assert result == datetime(2031, 12, 31)

    def test_language_test_from_issue(self):
        payload = {"fields": {"issue_date": {"value": "2025-03-01"}}}
        result = compute_expiry_from_extraction(DocumentType.language_test, payload)
        assert result == datetime(2025, 3, 1) + timedelta(days=730)

    def test_empty_payload(self):
        assert compute_expiry_from_extraction(DocumentType.passport, {}) is None
