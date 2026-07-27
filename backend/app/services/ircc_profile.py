"""IRCC Profile Pre-fill Service.

Maps OCR-extracted document data to IRCC form fields per program.
Validates formats, detects missing mandatory fields, and generates
pre-filled profiles for admin submission assistance.
"""

import re
from datetime import date, datetime
from typing import Any


# IRCC form field mappings per program
IRCC_FIELD_MAPPINGS = {
    "express_entry": {
        "personal_info": [
            {"ircc_field": "family_name", "source": "last_name", "required": True, "label": "Nom de famille"},
            {"ircc_field": "given_name", "source": "first_name", "required": True, "label": "Prenom"},
            {"ircc_field": "date_of_birth", "source": "date_of_birth", "required": True, "label": "Date de naissance", "format": "YYYY-MM-DD"},
            {"ircc_field": "country_of_birth", "source": "country_of_birth", "required": True, "label": "Pays de naissance"},
            {"ircc_field": "country_of_citizenship", "source": "nationality", "required": True, "label": "Pays de citoyennete"},
            {"ircc_field": "sex", "source": "sex", "required": True, "label": "Sexe"},
            {"ircc_field": "marital_status", "source": "marital_status", "required": True, "label": "Etat civil"},
            {"ircc_field": "email", "source": "email", "required": True, "label": "Adresse courriel"},
            {"ircc_field": "phone", "source": "phone", "required": False, "label": "Telephone"},
        ],
        "passport_info": [
            {"ircc_field": "passport_number", "source": "passport_number", "required": True, "label": "Numero de passeport"},
            {"ircc_field": "passport_country", "source": "issuing_country", "required": True, "label": "Pays de delivrance"},
            {"ircc_field": "passport_issue_date", "source": "issue_date", "required": True, "label": "Date de delivrance", "format": "YYYY-MM-DD"},
            {"ircc_field": "passport_expiry_date", "source": "expiry_date", "required": True, "label": "Date d'expiration", "format": "YYYY-MM-DD"},
        ],
        "education": [
            {"ircc_field": "highest_education_level", "source": "education_level", "required": True, "label": "Niveau d'etudes"},
            {"ircc_field": "field_of_study", "source": "field_of_study", "required": False, "label": "Domaine d'etudes"},
            {"ircc_field": "institution_name", "source": "institution_name", "required": False, "label": "Etablissement"},
            {"ircc_field": "education_country", "source": "education_country", "required": False, "label": "Pays des etudes"},
            {"ircc_field": "graduation_date", "source": "graduation_date", "required": False, "label": "Date d'obtention", "format": "YYYY-MM-DD"},
        ],
        "language": [
            {"ircc_field": "first_language_test_type", "source": "test_type", "required": True, "label": "Type de test"},
            {"ircc_field": "listening_score", "source": "listening", "required": True, "label": "Score ecoute"},
            {"ircc_field": "reading_score", "source": "reading", "required": True, "label": "Score lecture"},
            {"ircc_field": "writing_score", "source": "writing", "required": True, "label": "Score ecriture"},
            {"ircc_field": "speaking_score", "source": "speaking", "required": True, "label": "Score expression orale"},
            {"ircc_field": "test_date", "source": "test_date", "required": True, "label": "Date du test", "format": "YYYY-MM-DD"},
        ],
        "work_experience": [
            {"ircc_field": "noc_code", "source": "noc_code", "required": True, "label": "Code CNP/NOC"},
            {"ircc_field": "job_title", "source": "job_title", "required": True, "label": "Titre du poste"},
            {"ircc_field": "employer_name", "source": "employer_name", "required": True, "label": "Employeur"},
            {"ircc_field": "work_start_date", "source": "start_date", "required": True, "label": "Date de debut", "format": "YYYY-MM-DD"},
            {"ircc_field": "work_end_date", "source": "end_date", "required": False, "label": "Date de fin", "format": "YYYY-MM-DD"},
            {"ircc_field": "work_country", "source": "work_country", "required": False, "label": "Pays de travail"},
        ],
    },
    "study_permit": {
        "personal_info": [
            {"ircc_field": "family_name", "source": "last_name", "required": True, "label": "Nom de famille"},
            {"ircc_field": "given_name", "source": "first_name", "required": True, "label": "Prenom"},
            {"ircc_field": "date_of_birth", "source": "date_of_birth", "required": True, "label": "Date de naissance", "format": "YYYY-MM-DD"},
            {"ircc_field": "country_of_citizenship", "source": "nationality", "required": True, "label": "Pays de citoyennete"},
            {"ircc_field": "sex", "source": "sex", "required": True, "label": "Sexe"},
            {"ircc_field": "email", "source": "email", "required": True, "label": "Adresse courriel"},
        ],
        "passport_info": [
            {"ircc_field": "passport_number", "source": "passport_number", "required": True, "label": "Numero de passeport"},
            {"ircc_field": "passport_expiry_date", "source": "expiry_date", "required": True, "label": "Date d'expiration", "format": "YYYY-MM-DD"},
        ],
        "study_info": [
            {"ircc_field": "dli_number", "source": "dli_number", "required": True, "label": "Numero DLI"},
            {"ircc_field": "program_name", "source": "program_name", "required": True, "label": "Nom du programme"},
            {"ircc_field": "program_start_date", "source": "start_date", "required": True, "label": "Date de debut", "format": "YYYY-MM-DD"},
            {"ircc_field": "program_end_date", "source": "end_date", "required": True, "label": "Date de fin", "format": "YYYY-MM-DD"},
        ],
        "financial": [
            {"ircc_field": "proof_of_funds_amount", "source": "balance", "required": True, "label": "Montant preuve de fonds"},
            {"ircc_field": "bank_name", "source": "institution_name", "required": False, "label": "Institution bancaire"},
        ],
    },
    "work_permit": {
        "personal_info": [
            {"ircc_field": "family_name", "source": "last_name", "required": True, "label": "Nom de famille"},
            {"ircc_field": "given_name", "source": "first_name", "required": True, "label": "Prenom"},
            {"ircc_field": "date_of_birth", "source": "date_of_birth", "required": True, "label": "Date de naissance", "format": "YYYY-MM-DD"},
            {"ircc_field": "country_of_citizenship", "source": "nationality", "required": True, "label": "Pays de citoyennete"},
            {"ircc_field": "current_country", "source": "current_country", "required": True, "label": "Pays de residence actuel"},
        ],
        "passport_info": [
            {"ircc_field": "passport_number", "source": "passport_number", "required": True, "label": "Numero de passeport"},
            {"ircc_field": "passport_expiry_date", "source": "expiry_date", "required": True, "label": "Date d'expiration", "format": "YYYY-MM-DD"},
        ],
        "employment_info": [
            {"ircc_field": "lmia_number", "source": "lmia_number", "required": True, "label": "Numero EIMT/LMIA"},
            {"ircc_field": "employer_name", "source": "employer_name", "required": True, "label": "Nom de l'employeur"},
            {"ircc_field": "job_title", "source": "job_title", "required": True, "label": "Titre du poste"},
            {"ircc_field": "noc_code", "source": "noc_code", "required": True, "label": "Code CNP/NOC"},
            {"ircc_field": "work_start_date", "source": "start_date", "required": True, "label": "Date de debut", "format": "YYYY-MM-DD"},
            {"ircc_field": "salary", "source": "salary", "required": False, "label": "Salaire"},
        ],
    },
}

# Step-by-step submission guides per program
SUBMISSION_GUIDES = {
    "express_entry": [
        {"step": 1, "title": "Creer un compte GCKey", "url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/demande/compte.html"},
        {"step": 2, "title": "Remplir le profil Entree express", "description": "Entrer les informations personnelles, education, experience de travail et competences linguistiques."},
        {"step": 3, "title": "Soumettre le profil au bassin", "description": "Apres soumission, le profil recoit un score CRS et entre dans le bassin de candidats."},
        {"step": 4, "title": "Recevoir une ITA", "description": "Si selectionne lors d'un tirage, une Invitation a Presenter une Demande (ITA) est emise."},
        {"step": 5, "title": "Soumettre la demande complete", "description": "60 jours pour soumettre tous les documents requis apres reception de l'ITA."},
    ],
    "study_permit": [
        {"step": 1, "title": "Obtenir une lettre d'acceptation", "description": "Recevoir une lettre d'acceptation d'un etablissement designe (DLI)."},
        {"step": 2, "title": "Creer un compte en ligne", "url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/etudier-canada/permis-etudes.html"},
        {"step": 3, "title": "Remplir le formulaire IMM 1294", "description": "Formulaire de demande de permis d'etudes."},
        {"step": 4, "title": "Joindre les documents requis", "description": "Passeport, lettre d'acceptation, preuves financieres, photos."},
        {"step": 5, "title": "Payer les frais", "description": "Frais de traitement et donnees biometriques."},
        {"step": 6, "title": "Soumettre la demande", "description": "Soumettre en ligne et attendre la decision."},
    ],
    "work_permit": [
        {"step": 1, "title": "Obtenir une EIMT/LMIA approuvee", "description": "L'employeur doit obtenir une Etude d'Impact sur le Marche du Travail positive."},
        {"step": 2, "title": "Creer un compte en ligne", "url": "https://www.canada.ca/fr/immigration-refugies-citoyennete/services/travailler-canada/permis.html"},
        {"step": 3, "title": "Remplir le formulaire IMM 1295", "description": "Formulaire de demande de permis de travail."},
        {"step": 4, "title": "Joindre les documents", "description": "Passeport, offre d'emploi, EIMT, qualifications."},
        {"step": 5, "title": "Payer et soumettre", "description": "Payer les frais et soumettre la demande."},
    ],
}


# PLACEHOLDER_SERVICE_CLASS


class IRCCProfileService:
    """Service for generating pre-filled IRCC profiles from extracted data."""

    # Validation patterns
    DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    POSTAL_CODE_PATTERN = re.compile(r"^[A-Z]\d[A-Z]\s?\d[A-Z]\d$", re.IGNORECASE)
    EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    PHONE_PATTERN = re.compile(r"^[\d\s\-\+\(\)]{7,20}$")

    def generate_profile(
        self,
        program_category: str,
        candidate_data: dict[str, Any],
        extracted_documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a pre-filled IRCC profile.

        Args:
            program_category: Program type (express_entry, study_permit, work_permit)
            candidate_data: Basic candidate info from database
            extracted_documents: OCR-extracted data from all documents

        Returns:
            Pre-filled profile with validation results
        """
        # Get field mappings for program
        mappings = IRCC_FIELD_MAPPINGS.get(program_category)
        if not mappings:
            # Fallback to express_entry as default
            mappings = IRCC_FIELD_MAPPINGS["express_entry"]

        # Merge all extracted data into a flat lookup
        data_pool = self._build_data_pool(candidate_data, extracted_documents)

        # Map fields
        sections = {}
        missing_required = []
        validation_errors = []
        filled_count = 0
        total_count = 0

        for section_name, fields in mappings.items():
            section_fields = []
            for field_def in fields:
                total_count += 1
                ircc_field = field_def["ircc_field"]
                source_key = field_def["source"]
                required = field_def["required"]
                label = field_def["label"]
                fmt = field_def.get("format")

                # Look up value
                value = data_pool.get(source_key)

                # Validate format if value exists
                error = None
                if value is not None:
                    filled_count += 1
                    error = self._validate_field(ircc_field, value, fmt)
                    if error:
                        validation_errors.append({
                            "field": ircc_field,
                            "label": label,
                            "value": str(value),
                            "error": error,
                        })
                elif required:
                    missing_required.append({
                        "field": ircc_field,
                        "label": label,
                        "section": section_name,
                    })

                section_fields.append({
                    "ircc_field": ircc_field,
                    "label": label,
                    "value": value,
                    "required": required,
                    "filled": value is not None,
                    "valid": error is None if value else None,
                    "format": fmt,
                })

            sections[section_name] = section_fields

        # Calculate completeness
        completeness = (filled_count / total_count * 100) if total_count > 0 else 0

        return {
            "program_category": program_category,
            "sections": sections,
            "completeness_percent": round(completeness, 1),
            "total_fields": total_count,
            "filled_fields": filled_count,
            "missing_required": missing_required,
            "validation_errors": validation_errors,
            "is_ready": len(missing_required) == 0 and len(validation_errors) == 0,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_submission_guide(self, program_category: str) -> list[dict[str, Any]]:
        """Get step-by-step submission guide for a program."""
        return SUBMISSION_GUIDES.get(program_category, SUBMISSION_GUIDES["express_entry"])

    def export_profile_json(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Export profile as a clean JSON structure for external use."""
        export = {
            "program": profile["program_category"],
            "generated_at": profile["generated_at"],
            "fields": {},
        }

        for section_name, fields in profile["sections"].items():
            export["fields"][section_name] = {}
            for field in fields:
                if field["value"] is not None:
                    export["fields"][section_name][field["ircc_field"]] = field["value"]

        return export

    def _build_data_pool(
        self,
        candidate_data: dict[str, Any],
        extracted_documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build a flat lookup dict from candidate and extracted data."""
        pool: dict[str, Any] = {}

        # Add candidate data
        for key, value in candidate_data.items():
            if value is not None:
                pool[key] = value

        # Add extracted document data (later docs overwrite earlier)
        for doc in extracted_documents:
            fields = doc.get("fields", doc)
            if isinstance(fields, dict):
                for key, val in fields.items():
                    # Handle nested {value, confidence} format
                    if isinstance(val, dict) and "value" in val:
                        extracted_val = val["value"]
                    else:
                        extracted_val = val
                    if extracted_val is not None:
                        pool[key] = extracted_val

        return pool

    def _validate_field(self, field_name: str, value: Any, fmt: str | None) -> str | None:
        """Validate a field value. Returns error message or None."""
        str_val = str(value).strip()

        # Date format validation
        if fmt == "YYYY-MM-DD":
            if not self.DATE_PATTERN.match(str_val):
                return f"Format de date invalide (attendu: AAAA-MM-JJ, recu: {str_val})"
            try:
                parsed = date.fromisoformat(str_val)
                # Check reasonable date range
                if parsed.year < 1900 or parsed.year > 2100:
                    return f"Annee hors plage raisonnable: {parsed.year}"
            except ValueError:
                return f"Date invalide: {str_val}"

        # Email validation
        if "email" in field_name:
            if not self.EMAIL_PATTERN.match(str_val):
                return f"Format de courriel invalide: {str_val}"

        # Phone validation
        if "phone" in field_name:
            if not self.PHONE_PATTERN.match(str_val):
                return f"Format de telephone invalide: {str_val}"

        # Passport number basic check
        if "passport_number" in field_name:
            if len(str_val) < 5 or len(str_val) > 15:
                return f"Longueur de numero de passeport invalide: {len(str_val)} caracteres"

        return None


# Singleton
ircc_profile_service = IRCCProfileService()