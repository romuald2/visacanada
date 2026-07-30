"""Document Fraud Detection Service.

Multi-criteria analysis to detect potentially falsified documents:
- PDF metadata analysis (creation/modification timestamps, producer)
- MRZ (Machine Readable Zone) verification for passports/visas
- Logical inconsistency detection (impossible dates, mismatched data)
- Cross-reference with known official document patterns
- Confidence scoring with anomaly explanations

IMPORTANT: Never auto-rejects. Always flags for human review.
"""

import re
from datetime import date, datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    """Naive UTC timestamp (matches the rest of the codebase)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FraudAlert:
    """Represents a single fraud indicator."""

    def __init__(
        self,
        category: str,
        severity: str,
        description: str,
        confidence: float,
        details: dict[str, Any] | None = None,
    ):
        self.category = category  # metadata, mrz, logical, visual, pattern
        self.severity = severity  # high, medium, low
        self.description = description
        self.confidence = confidence  # 0.0 - 1.0
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "confidence": self.confidence,
            "details": self.details,
        }


class FraudDetectionService:
    """Multi-criteria document fraud detection."""

    # MRZ check digit weights
    MRZ_WEIGHTS = [7, 3, 1]

    # Known PDF producers for official documents
    TRUSTED_PDF_PRODUCERS = [
        "adobe",
        "microsoft",
        "libreoffice",
        "openoffice",
        "government",
        "ircc",
        "canada",
    ]

    # Suspicious PDF producers
    SUSPICIOUS_PRODUCERS = [
        "photoshop",
        "gimp",
        "paint",
        "canva",
        "figma",
    ]

    def analyze_document(
        self,
        document_type: str,
        extracted_data: dict[str, Any] | None = None,
        pdf_metadata: dict[str, Any] | None = None,
        file_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run full fraud analysis on a document.

        Args:
            document_type: Type of document (passport, bank_statement, etc.)
            extracted_data: OCR-extracted fields
            pdf_metadata: PDF internal metadata (creator, producer, dates)
            file_metadata: File system metadata (size, creation date)

        Returns:
            Fraud analysis report with score and alerts
        """
        alerts: list[FraudAlert] = []

        # Run all checks
        if pdf_metadata:
            alerts.extend(self._analyze_metadata(pdf_metadata))

        if extracted_data:
            alerts.extend(self._check_logical_consistency(document_type, extracted_data))

            if document_type in ("passport", "visa", "travel_document"):
                alerts.extend(self._verify_mrz(extracted_data))

        if file_metadata:
            alerts.extend(self._analyze_file_metadata(file_metadata))

        alerts.extend(self._check_document_patterns(document_type, extracted_data or {}))

        # Calculate fraud score
        fraud_score = self._calculate_fraud_score(alerts)
        requires_review = fraud_score >= 30.0 or any(a.severity == "high" for a in alerts)

        return {
            "fraud_score": round(fraud_score, 1),
            "risk_level": self._get_risk_level(fraud_score),
            "requires_human_review": requires_review,
            "alerts": [a.to_dict() for a in alerts],
            "alerts_count": {
                "high": sum(1 for a in alerts if a.severity == "high"),
                "medium": sum(1 for a in alerts if a.severity == "medium"),
                "low": sum(1 for a in alerts if a.severity == "low"),
                "total": len(alerts),
            },
            "summary": self._build_summary(alerts, fraud_score),
            "analyzed_at": _utcnow().isoformat(),
        }

    def _analyze_metadata(self, pdf_metadata: dict[str, Any]) -> list[FraudAlert]:
        """Analyze PDF metadata for suspicious patterns."""
        alerts = []

        creator = (pdf_metadata.get("creator") or "").lower()
        producer = (pdf_metadata.get("producer") or "").lower()
        creation_date = pdf_metadata.get("creation_date")
        modification_date = pdf_metadata.get("modification_date")

        # Check for suspicious producer/creator tools
        for suspicious in self.SUSPICIOUS_PRODUCERS:
            if suspicious in creator or suspicious in producer:
                alerts.append(
                    FraudAlert(
                        category="metadata",
                        severity="high",
                        description=f"Document créé avec un outil de retouche d'image: {creator or producer}",
                        confidence=0.8,
                        details={"creator": creator, "producer": producer},
                    )
                )
                break

        # Check modification after creation (tampering indicator)
        if creation_date and modification_date:
            try:
                created = self._parse_date(creation_date)
                modified = self._parse_date(modification_date)
                if created and modified:
                    delta = (modified - created).days
                    if delta > 30:
                        alerts.append(
                            FraudAlert(
                                category="metadata",
                                severity="medium",
                                description=f"Document modifié {delta} jours après sa création",
                                confidence=0.6,
                                details={
                                    "creation_date": str(creation_date),
                                    "modification_date": str(modification_date),
                                    "days_between": delta,
                                },
                            )
                        )
            except (ValueError, TypeError):
                pass

        # Check if creation date is in the future
        if creation_date:
            try:
                created = self._parse_date(creation_date)
                if created and created.date() > date.today():
                    alerts.append(
                        FraudAlert(
                            category="metadata",
                            severity="high",
                            description="Date de création du PDF dans le futur",
                            confidence=0.9,
                            details={"creation_date": str(creation_date)},
                        )
                    )
            except (ValueError, TypeError):
                pass

        # Missing metadata (official docs usually have it)
        if not creator and not producer:
            alerts.append(
                FraudAlert(
                    category="metadata",
                    severity="low",
                    description="Métadonnées PDF manquantes (créateur/producteur)",
                    confidence=0.3,
                    details={},
                )
            )

        return alerts

    def _verify_mrz(self, extracted_data: dict[str, Any]) -> list[FraudAlert]:
        """Verify MRZ (Machine Readable Zone) check digits."""
        alerts = []
        mrz_lines = extracted_data.get("mrz_lines") or extracted_data.get("mrz")

        if not mrz_lines:
            return alerts

        # Handle both string and list formats
        if isinstance(mrz_lines, str):
            lines = mrz_lines.strip().split("\n")
        elif isinstance(mrz_lines, list):
            lines = mrz_lines
        else:
            return alerts

        # Clean lines
        lines = [line.strip().upper() for line in lines if line.strip()]

        if len(lines) < 2:
            return alerts

        # TD3 format (passports): 2 lines of 44 chars
        if len(lines) == 2 and all(len(line) == 44 for line in lines):
            alerts.extend(self._verify_td3_mrz(lines))
        # TD1 format (ID cards): 3 lines of 30 chars
        elif len(lines) == 3 and all(len(line) == 30 for line in lines):
            alerts.extend(self._verify_td1_mrz(lines))

        return alerts

    def _verify_td3_mrz(self, lines: list[str]) -> list[FraudAlert]:
        """Verify TD3 (passport) MRZ check digits."""
        alerts = []
        line2 = lines[1]

        # Passport number: positions 0-8, check digit at 9
        passport_num = line2[0:9]
        passport_check = line2[9]
        if not self._verify_check_digit(passport_num, passport_check):
            alerts.append(
                FraudAlert(
                    category="mrz",
                    severity="high",
                    description="Chiffre de contrôle MRZ invalide pour le numéro de passeport",
                    confidence=0.95,
                    details={"field": "passport_number", "value": passport_num},
                )
            )

        # Date of birth: positions 13-18, check digit at 19
        dob = line2[13:19]
        dob_check = line2[19]
        if not self._verify_check_digit(dob, dob_check):
            alerts.append(
                FraudAlert(
                    category="mrz",
                    severity="high",
                    description="Chiffre de contrôle MRZ invalide pour la date de naissance",
                    confidence=0.95,
                    details={"field": "date_of_birth", "value": dob},
                )
            )

        # Expiry date: positions 21-26, check digit at 27
        expiry = line2[21:27]
        expiry_check = line2[27]
        if not self._verify_check_digit(expiry, expiry_check):
            alerts.append(
                FraudAlert(
                    category="mrz",
                    severity="high",
                    description="Chiffre de contrôle MRZ invalide pour la date d'expiration",
                    confidence=0.95,
                    details={"field": "expiry_date", "value": expiry},
                )
            )

        return alerts

    def _verify_td1_mrz(self, lines: list[str]) -> list[FraudAlert]:
        """Verify TD1 (ID card) MRZ check digits."""
        alerts = []
        line1 = lines[0]

        # Document number: positions 5-13, check digit at 14
        doc_num = line1[5:14]
        doc_check = line1[14]
        if not self._verify_check_digit(doc_num, doc_check):
            alerts.append(
                FraudAlert(
                    category="mrz",
                    severity="high",
                    description="Chiffre de contrôle MRZ invalide pour le numéro de document",
                    confidence=0.95,
                    details={"field": "document_number", "value": doc_num},
                )
            )

        return alerts

    def _verify_check_digit(self, data: str, expected_check: str) -> bool:
        """Verify an MRZ check digit using ICAO 9303 algorithm."""
        if not expected_check.isdigit():
            return False

        total = 0
        for i, char in enumerate(data):
            if char.isdigit():
                value = int(char)
            elif char.isalpha():
                value = ord(char) - ord("A") + 10
            elif char == "<":
                value = 0
            else:
                value = 0
            weight = self.MRZ_WEIGHTS[i % 3]
            total += value * weight

        return (total % 10) == int(expected_check)

    def _check_logical_consistency(
        self, document_type: str, extracted_data: dict[str, Any]
    ) -> list[FraudAlert]:
        """Check for logical inconsistencies in extracted data."""
        alerts = []
        fields = extracted_data.get("fields", extracted_data)

        # Check date of birth validity
        dob_value = self._get_field_value(fields, "date_of_birth")
        if dob_value:
            try:
                dob = date.fromisoformat(str(dob_value))
                age = (date.today() - dob).days / 365.25

                if age < 0:
                    alerts.append(
                        FraudAlert(
                            category="logical",
                            severity="high",
                            description="Date de naissance dans le futur",
                            confidence=0.99,
                            details={"date_of_birth": str(dob_value)},
                        )
                    )
                elif age > 150:
                    alerts.append(
                        FraudAlert(
                            category="logical",
                            severity="high",
                            description=f"Âge impossible: {age:.0f} ans",
                            confidence=0.99,
                            details={"date_of_birth": str(dob_value), "calculated_age": round(age)},
                        )
                    )
                elif age < 16 and document_type == "passport":
                    alerts.append(
                        FraudAlert(
                            category="logical",
                            severity="medium",
                            description=f"Candidat mineur ({age:.0f} ans) - vérification requise",
                            confidence=0.7,
                            details={"age": round(age)},
                        )
                    )
            except (ValueError, TypeError):
                pass

        # Check expiry before issue date
        issue_value = self._get_field_value(fields, "issue_date")
        expiry_value = self._get_field_value(fields, "expiry_date")
        if issue_value and expiry_value:
            try:
                issue = date.fromisoformat(str(issue_value))
                expiry = date.fromisoformat(str(expiry_value))
                if expiry <= issue:
                    alerts.append(
                        FraudAlert(
                            category="logical",
                            severity="high",
                            description="Date d'expiration antérieure ou égale à la date d'émission",
                            confidence=0.95,
                            details={
                                "issue_date": str(issue_value),
                                "expiry_date": str(expiry_value),
                            },
                        )
                    )
                # Passport validity > 10 years is suspicious
                elif document_type == "passport" and (expiry - issue).days > 3660:
                    alerts.append(
                        FraudAlert(
                            category="logical",
                            severity="medium",
                            description="Durée de validité du passeport supérieure à 10 ans",
                            confidence=0.7,
                            details={"validity_days": (expiry - issue).days},
                        )
                    )
            except (ValueError, TypeError):
                pass

        # Bank statement: check for negative balance or unrealistic amounts
        if document_type == "bank_statement":
            balance = self._get_field_value(fields, "balance")
            if balance is not None:
                try:
                    bal = float(str(balance).replace(",", "").replace("$", "").replace(" ", ""))
                    if bal > 50_000_000:
                        alerts.append(
                            FraudAlert(
                                category="logical",
                                severity="medium",
                                description=f"Solde bancaire inhabituellement élevé: {bal:,.0f}",
                                confidence=0.6,
                                details={"balance": bal},
                            )
                        )
                except (ValueError, TypeError):
                    pass

        # Employment letter: check dates
        if document_type == "employment_letter":
            start_date_value = self._get_field_value(fields, "start_date")
            if start_date_value:
                try:
                    start = date.fromisoformat(str(start_date_value))
                    if start > date.today():
                        alerts.append(
                            FraudAlert(
                                category="logical",
                                severity="medium",
                                description="Date de début d'emploi dans le futur",
                                confidence=0.7,
                                details={"start_date": str(start_date_value)},
                            )
                        )
                except (ValueError, TypeError):
                    pass

        return alerts

    def _analyze_file_metadata(self, file_metadata: dict[str, Any]) -> list[FraudAlert]:
        """Analyze file-level metadata."""
        alerts = []

        file_size = file_metadata.get("file_size_bytes", 0)

        # Suspiciously small PDF (likely just an image wrapper)
        if file_size and file_size < 5000:
            alerts.append(
                FraudAlert(
                    category="metadata",
                    severity="low",
                    description="Fichier PDF anormalement petit (possible image convertie)",
                    confidence=0.4,
                    details={"file_size_bytes": file_size},
                )
            )

        # Very large file for a simple document
        if file_size and file_size > 50_000_000:
            alerts.append(
                FraudAlert(
                    category="metadata",
                    severity="low",
                    description="Fichier anormalement volumineux",
                    confidence=0.3,
                    details={"file_size_bytes": file_size},
                )
            )

        return alerts

    def _check_document_patterns(
        self, document_type: str, extracted_data: dict[str, Any]
    ) -> list[FraudAlert]:
        """Cross-reference with known official document patterns."""
        alerts = []
        fields = extracted_data.get("fields", extracted_data)

        # Canadian passport number format: 2 letters + 6 digits
        if document_type == "passport":
            passport_num = self._get_field_value(fields, "passport_number")
            if passport_num:
                passport_str = str(passport_num).strip()
                # Canadian passport: 2 alpha + 6 digits
                if not re.match(r"^[A-Z]{2}\d{6}$", passport_str):
                    # Could be other country format, low severity
                    if not re.match(r"^[A-Z0-9]{6,9}$", passport_str):
                        alerts.append(
                            FraudAlert(
                                category="pattern",
                                severity="medium",
                                description="Format de numéro de passeport non reconnu",
                                confidence=0.5,
                                details={"passport_number": passport_str},
                            )
                        )

            # Check issuing country consistency
            country = self._get_field_value(fields, "issuing_country")
            nationality = self._get_field_value(fields, "nationality")
            if country and nationality and str(country).upper() != str(nationality).upper():
                alerts.append(
                    FraudAlert(
                        category="pattern",
                        severity="low",
                        description="Pays émetteur différent de la nationalité",
                        confidence=0.4,
                        details={"issuing_country": country, "nationality": nationality},
                    )
                )

        # Bank statement patterns
        if document_type == "bank_statement":
            institution = self._get_field_value(fields, "institution_name")
            if institution:
                inst_lower = str(institution).lower()
                # Check for obvious fake institution names
                fake_indicators = ["test", "fake", "example", "demo", "sample"]
                for indicator in fake_indicators:
                    if indicator in inst_lower:
                        alerts.append(
                            FraudAlert(
                                category="pattern",
                                severity="high",
                                description=f"Nom d'institution bancaire suspect: {institution}",
                                confidence=0.9,
                                details={"institution_name": institution},
                            )
                        )
                        break

        return alerts

    def _calculate_fraud_score(self, alerts: list[FraudAlert]) -> float:
        """Calculate overall fraud risk score (0-100)."""
        if not alerts:
            return 0.0

        # Weighted scoring by severity
        severity_weights = {"high": 30.0, "medium": 15.0, "low": 5.0}
        total = 0.0

        for alert in alerts:
            weight = severity_weights.get(alert.severity, 5.0)
            total += weight * alert.confidence

        # Cap at 100
        return min(100.0, total)

    def _get_risk_level(self, score: float) -> str:
        """Determine risk level from fraud score."""
        if score >= 70:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 30:
            return "medium"
        elif score >= 10:
            return "low"
        return "negligible"

    def _build_summary(self, alerts: list[FraudAlert], score: float) -> str:
        """Build human-readable fraud analysis summary."""
        if not alerts:
            return "Aucune anomalie détectée. Document conforme."

        high_count = sum(1 for a in alerts if a.severity == "high")
        medium_count = sum(1 for a in alerts if a.severity == "medium")

        parts = [f"Score de risque: {score:.0f}/100."]

        if high_count:
            parts.append(f"{high_count} alerte(s) critique(s).")
        if medium_count:
            parts.append(f"{medium_count} alerte(s) moyenne(s).")

        if score >= 50:
            parts.append("Revue humaine fortement recommandée.")
        elif score >= 30:
            parts.append("Revue humaine requise.")

        return " ".join(parts)

    def _get_field_value(self, fields: dict[str, Any], key: str) -> Any:
        """Extract field value, handling nested dict format."""
        value = fields.get(key)
        if isinstance(value, dict):
            return value.get("value")
        return value

    def _parse_date(self, value: Any) -> datetime | None:
        """Parse various date formats."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())

        str_val = str(value).strip()
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "D:%Y%m%d%H%M%S",  # PDF date format
        ]
        for fmt in formats:
            try:
                return datetime.strptime(str_val[: len(fmt) + 5], fmt)
            except (ValueError, TypeError):
                continue
        return None


# Singleton
fraud_detection_service = FraudDetectionService()
