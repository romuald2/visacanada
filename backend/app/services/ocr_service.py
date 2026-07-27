"""Azure Document Intelligence OCR service.

Extracts structured data from immigration documents:
- Passports (prebuilt-idDocument model)
- Bank statements (prebuilt-receipt / custom)
- Employment letters (prebuilt-document / custom)
"""

import json
from datetime import date
from enum import Enum
from typing import Any

import httpx

from app.core.config import settings


class DocumentExtractionType(str, Enum):
    passport = "passport"
    bank_statement = "bank_statement"
    employment_letter = "employment_letter"
    generic = "generic"


class OCRExtractionError(Exception):
    """Custom exception for OCR extraction failures."""
    pass


# Azure DI model mappings
AZURE_MODELS = {
    DocumentExtractionType.passport: "prebuilt-idDocument",
    DocumentExtractionType.bank_statement: "prebuilt-document",
    DocumentExtractionType.employment_letter: "prebuilt-document",
    DocumentExtractionType.generic: "prebuilt-document",
}


class AzureDocumentIntelligenceService:
    """Service for extracting data from documents using Azure Document Intelligence."""

    def __init__(self):
        self._endpoint = settings.azure_doc_intel_endpoint.rstrip("/")
        self._api_key = settings.azure_doc_intel_key
        self._api_version = "2024-02-29-preview"

    @property
    def is_configured(self) -> bool:
        """Check if Azure DI credentials are set."""
        return bool(self._endpoint and self._api_key)

    async def extract_document(
        self,
        file_content: bytes,
        mime_type: str,
        extraction_type: DocumentExtractionType,
    ) -> dict[str, Any]:
        """Extract structured data from a document.

        Args:
            file_content: Raw file bytes
            mime_type: MIME type of the document
            extraction_type: Type of extraction to perform

        Returns:
            Dict with extracted fields based on document type
        """
        if not self.is_configured:
            raise OCRExtractionError(
                "Azure Document Intelligence non configuré. "
                "Vérifiez AZURE_DOC_INTEL_ENDPOINT et AZURE_DOC_INTEL_KEY."
            )

        model_id = AZURE_MODELS[extraction_type]
        result = await self._analyze_document(file_content, mime_type, model_id)

        # Parse based on extraction type
        if extraction_type == DocumentExtractionType.passport:
            return self._parse_passport_result(result)
        elif extraction_type == DocumentExtractionType.bank_statement:
            return self._parse_bank_statement_result(result)
        elif extraction_type == DocumentExtractionType.employment_letter:
            return self._parse_employment_letter_result(result)
        else:
            return self._parse_generic_result(result)

    async def _analyze_document(
        self, file_content: bytes, mime_type: str, model_id: str
    ) -> dict:
        """Send document to Azure DI for analysis."""
        url = (
            f"{self._endpoint}/documentintelligence/documentModels/{model_id}:analyze"
            f"?api-version={self._api_version}"
        )

        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-Type": mime_type,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Submit analysis request
            response = await client.post(url, headers=headers, content=file_content)

            if response.status_code not in (200, 202):
                raise OCRExtractionError(
                    f"Azure DI error ({response.status_code}): {response.text[:200]}"
                )

            # If 202 Accepted, poll for result
            if response.status_code == 202:
                operation_url = response.headers.get("Operation-Location", "")
                if not operation_url:
                    raise OCRExtractionError("No Operation-Location header in response")

                result = await self._poll_result(client, operation_url)
                return result
            else:
                return response.json()

    async def _poll_result(self, client: httpx.AsyncClient, operation_url: str) -> dict:
        """Poll Azure DI for analysis result."""
        import asyncio

        headers = {"Ocp-Apim-Subscription-Key": self._api_key}
        max_attempts = 30

        for _ in range(max_attempts):
            await asyncio.sleep(2)
            response = await client.get(operation_url, headers=headers)

            if response.status_code != 200:
                raise OCRExtractionError(f"Poll error: {response.status_code}")

            result = response.json()
            status = result.get("status", "")

            if status == "succeeded":
                return result.get("analyzeResult", result)
            elif status == "failed":
                error = result.get("error", {})
                raise OCRExtractionError(
                    f"Analysis failed: {error.get('message', 'Unknown error')}"
                )

        raise OCRExtractionError("Analysis timeout: max poll attempts reached")

    def _parse_passport_result(self, result: dict) -> dict[str, Any]:
        """Parse Azure DI ID document result into structured passport data."""
        extracted = {
            "type": "passport",
            "fields": {},
            "confidence": 0.0,
        }

        documents = result.get("documents", [])
        if not documents:
            return extracted

        doc = documents[0]
        fields = doc.get("fields", {})
        extracted["confidence"] = doc.get("confidence", 0.0)

        # Map Azure DI fields to our structure
        field_mapping = {
            "FirstName": "first_name",
            "LastName": "last_name",
            "DocumentNumber": "document_number",
            "DateOfBirth": "date_of_birth",
            "DateOfExpiration": "expiry_date",
            "Nationality": "nationality",
            "Sex": "sex",
            "CountryRegion": "issuing_country",
            "PlaceOfBirth": "place_of_birth",
            "MachineReadableZone": "mrz",
        }

        for azure_field, our_field in field_mapping.items():
            if azure_field in fields:
                field_data = fields[azure_field]
                value = field_data.get("valueString") or field_data.get("valueDate") or field_data.get("content", "")
                confidence = field_data.get("confidence", 0.0)
                extracted["fields"][our_field] = {
                    "value": str(value) if value else None,
                    "confidence": confidence,
                }

        return extracted

    def _parse_bank_statement_result(self, result: dict) -> dict[str, Any]:
        """Parse bank statement extraction result."""
        extracted = {
            "type": "bank_statement",
            "fields": {},
            "confidence": 0.0,
            "raw_text": "",
        }

        # Extract key-value pairs for bank statements
        kv_pairs = result.get("keyValuePairs", [])
        for pair in kv_pairs:
            key = pair.get("key", {}).get("content", "").lower()
            value = pair.get("value", {}).get("content", "")
            confidence = pair.get("confidence", 0.0)

            if any(term in key for term in ["solde", "balance", "total"]):
                extracted["fields"]["balance"] = {
                    "value": value,
                    "confidence": confidence,
                }
            elif any(term in key for term in ["compte", "account"]):
                extracted["fields"]["account_number"] = {
                    "value": value,
                    "confidence": confidence,
                }
            elif any(term in key for term in ["date", "period", "période"]):
                extracted["fields"]["statement_date"] = {
                    "value": value,
                    "confidence": confidence,
                }
            elif any(term in key for term in ["titulaire", "holder", "nom"]):
                extracted["fields"]["account_holder"] = {
                    "value": value,
                    "confidence": confidence,
                }

        # Get full text content
        pages = result.get("pages", [])
        text_parts = []
        for page in pages:
            for line in page.get("lines", []):
                text_parts.append(line.get("content", ""))
        extracted["raw_text"] = "\n".join(text_parts)

        return extracted

    def _parse_employment_letter_result(self, result: dict) -> dict[str, Any]:
        """Parse employment letter extraction result."""
        extracted = {
            "type": "employment_letter",
            "fields": {},
            "confidence": 0.0,
            "raw_text": "",
        }

        kv_pairs = result.get("keyValuePairs", [])
        for pair in kv_pairs:
            key = pair.get("key", {}).get("content", "").lower()
            value = pair.get("value", {}).get("content", "")
            confidence = pair.get("confidence", 0.0)

            if any(term in key for term in ["poste", "position", "title", "titre"]):
                extracted["fields"]["job_title"] = {
                    "value": value,
                    "confidence": confidence,
                }
            elif any(term in key for term in ["salaire", "salary", "rémunération"]):
                extracted["fields"]["salary"] = {
                    "value": value,
                    "confidence": confidence,
                }
            elif any(term in key for term in ["date d'embauche", "start date", "début"]):
                extracted["fields"]["start_date"] = {
                    "value": value,
                    "confidence": confidence,
                }
            elif any(term in key for term in ["employeur", "employer", "company"]):
                extracted["fields"]["employer_name"] = {
                    "value": value,
                    "confidence": confidence,
                }
            elif any(term in key for term in ["heures", "hours", "temps"]):
                extracted["fields"]["hours_per_week"] = {
                    "value": value,
                    "confidence": confidence,
                }
            elif any(term in key for term in ["noc", "code"]):
                extracted["fields"]["noc_code"] = {
                    "value": value,
                    "confidence": confidence,
                }

        pages = result.get("pages", [])
        text_parts = []
        for page in pages:
            for line in page.get("lines", []):
                text_parts.append(line.get("content", ""))
        extracted["raw_text"] = "\n".join(text_parts)

        return extracted

    def _parse_generic_result(self, result: dict) -> dict[str, Any]:
        """Parse generic document - extract all text and key-value pairs."""
        extracted = {
            "type": "generic",
            "fields": {},
            "confidence": 0.0,
            "raw_text": "",
            "key_value_pairs": [],
        }

        # Key-value pairs
        for pair in result.get("keyValuePairs", []):
            key = pair.get("key", {}).get("content", "")
            value = pair.get("value", {}).get("content", "")
            if key and value:
                extracted["key_value_pairs"].append({"key": key, "value": value})

        # Full text
        pages = result.get("pages", [])
        text_parts = []
        for page in pages:
            for line in page.get("lines", []):
                text_parts.append(line.get("content", ""))
        extracted["raw_text"] = "\n".join(text_parts)

        return extracted


# Singleton
azure_ocr_service = AzureDocumentIntelligenceService()
