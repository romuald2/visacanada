"""AI-powered letter generation service.

Generates personalized immigration letters using Claude API with template fallback.
Supports: motivation letters, explanation letters, financial support letters.
Templates are customized per immigration program.
"""

from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from app.core.config import settings


class LetterType(str, Enum):
    motivation = "motivation"
    explanation = "explanation"
    financial_support = "financial_support"
    cover_letter = "cover_letter"


# =============================================================================
# Letter Templates (French - fallback when AI not available)
# =============================================================================

LETTER_TEMPLATES = {
    LetterType.motivation: {
        "title": "Lettre de motivation",
        "template": (
            "{city}, le {date}\n\n"
            "Objet: Lettre de motivation - {program_name}\n\n"
            "Madame, Monsieur,\n\n"
            "Je soussigne(e) {full_name}, de nationalite {nationality}, "
            "souhaite par la presente exprimer ma motivation pour le programme "
            "{program_name}.\n\n"
            "Parcours professionnel:\n"
            "{professional_background}\n\n"
            "Motivations pour le Canada:\n"
            "{motivations}\n\n"
            "Objectifs au Canada:\n"
            "{objectives}\n\n"
            "Je suis convaincu(e) que mon profil correspond aux criteres du programme "
            "et que je pourrai contribuer positivement a la societe canadienne.\n\n"
            "Je vous prie d'agreer, Madame, Monsieur, l'expression de mes "
            "salutations distinguees.\n\n"
            "{full_name}\n"
            "{email}\n"
            "{phone}"
        ),
    },
# PLACEHOLDER_MORE_TEMPLATES
    LetterType.explanation: {
        "title": "Lettre d'explication",
        "template": (
            "{city}, le {date}\n\n"
            "Objet: Lettre d'explication - {subject}\n\n"
            "Madame, Monsieur,\n\n"
            "Je soussigne(e) {full_name}, numero de dossier {reference_number}, "
            "souhaite apporter des explications concernant {subject}.\n\n"
            "Contexte:\n"
            "{context}\n\n"
            "Explication:\n"
            "{explanation}\n\n"
            "Mesures prises:\n"
            "{measures_taken}\n\n"
            "Je reste a votre disposition pour tout renseignement complementaire "
            "et vous prie d'agreer, Madame, Monsieur, mes salutations distinguees.\n\n"
            "{full_name}\n"
            "{email}"
        ),
    },
    LetterType.financial_support: {
        "title": "Lettre de soutien financier",
        "template": (
            "{city}, le {date}\n\n"
            "Objet: Attestation de soutien financier\n\n"
            "Madame, Monsieur,\n\n"
            "Je soussigne(e) {sponsor_name}, residant au {sponsor_address}, "
            "atteste par la presente m'engager a soutenir financierement "
            "{full_name} pendant son sejour au Canada.\n\n"
            "Relation avec le candidat: {relationship}\n\n"
            "Informations financieres:\n"
            "- Revenu annuel: {annual_income}\n"
            "- Epargne disponible: {savings}\n"
            "- Emploi: {sponsor_employment}\n\n"
            "Je m'engage a couvrir les frais suivants:\n"
            "{covered_expenses}\n\n"
            "Duree de l'engagement: {duration}\n\n"
            "Je joins a cette lettre les documents justificatifs de ma "
            "situation financiere.\n\n"
            "Fait a {city}, le {date}\n\n"
            "{sponsor_name}\n"
            "Signature: _______________"
        ),
    },
    LetterType.cover_letter: {
        "title": "Lettre d'accompagnement",
        "template": (
            "{city}, le {date}\n\n"
            "Objet: Demande de {program_name} - {full_name}\n\n"
            "Madame, Monsieur,\n\n"
            "Veuillez trouver ci-joint ma demande complete pour le programme "
            "{program_name}.\n\n"
            "Documents inclus:\n"
            "{documents_list}\n\n"
            "Informations du demandeur:\n"
            "- Nom complet: {full_name}\n"
            "- Date de naissance: {date_of_birth}\n"
            "- Nationalite: {nationality}\n"
            "- Passeport: {passport_number}\n\n"
            "Je certifie que toutes les informations fournies sont exactes "
            "et completes.\n\n"
            "Cordialement,\n\n"
            "{full_name}\n"
            "{email}\n"
            "{phone}"
        ),
    },
}

# Program-specific guidance for AI generation
PROGRAM_CONTEXT = {
    "express_entry": (
        "Programme d'immigration economique du Canada. "
        "Mettre en avant: competences professionnelles, "
        "adaptabilite, contribution economique, maitrise des langues officielles."
    ),
    "study_permit": (
        "Permis d'etudes au Canada. "
        "Mettre en avant: plan d'etudes, pertinence du programme choisi, "
        "objectifs de carriere, liens avec le pays d'origine, capacite financiere."
    ),
    "work_permit": (
        "Permis de travail au Canada. "
        "Mettre en avant: experience professionnelle pertinente, "
        "offre d'emploi, competences recherchees, intention temporaire."
    ),
    "family_sponsorship": (
        "Parrainage familial. "
        "Mettre en avant: lien familial genuein, capacite financiere du parrain, "
        "intention d'etablissement, integration."
    ),
    "visitor_visa": (
        "Visa de visiteur. "
        "Mettre en avant: but de la visite, liens avec le pays d'origine, "
        "capacite financiere, intention de retour."
    ),
}
# PLACEHOLDER_SERVICE_CLASS


class LetterGenerator:
    """Generate personalized immigration letters."""

    def __init__(self):
        self._api_key = settings.anthropic_api_key
        self._model = "claude-sonnet-4-20250514"

    @property
    def ai_available(self) -> bool:
        return bool(self._api_key)

    async def generate(
        self,
        letter_type: str,
        candidate_data: dict[str, Any],
        program: str | None = None,
        custom_instructions: str | None = None,
    ) -> dict[str, Any]:
        """Generate a letter using AI or template fallback.

        Args:
            letter_type: Type of letter (motivation, explanation, etc.)
            candidate_data: Candidate info for personalization
            program: Immigration program for context
            custom_instructions: Additional instructions for AI

        Returns:
            Dict with generated content, method used, and metadata
        """
        if self.ai_available:
            try:
                content = await self._generate_with_ai(
                    letter_type, candidate_data, program, custom_instructions
                )
                return {
                    "content": content,
                    "method": "ai",
                    "letter_type": letter_type,
                    "generated_at": datetime.utcnow().isoformat(),
                    "program": program,
                }
            except Exception:
                pass  # Fall through to template

        # Template fallback
        content = self._generate_from_template(letter_type, candidate_data)
        return {
            "content": content,
            "method": "template",
            "letter_type": letter_type,
            "generated_at": datetime.utcnow().isoformat(),
            "program": program,
        }

    async def _generate_with_ai(
        self,
        letter_type: str,
        candidate_data: dict[str, Any],
        program: str | None,
        custom_instructions: str | None,
    ) -> str:
        """Generate letter content using Claude API."""
        prompt = self._build_prompt(letter_type, candidate_data, program, custom_instructions)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    def _build_prompt(
        self,
        letter_type: str,
        candidate_data: dict[str, Any],
        program: str | None,
        custom_instructions: str | None,
    ) -> str:
        """Build the AI prompt for letter generation."""
        template_info = LETTER_TEMPLATES.get(letter_type, {})
        title = template_info.get("title", "Lettre")

        program_context = ""
        if program:
            program_context = PROGRAM_CONTEXT.get(program, "")

        prompt = (
            f"Redige une {title} professionnelle pour une demande d'immigration au Canada.\n\n"
            f"Type de lettre: {title}\n"
            f"Programme: {program or 'Non specifie'}\n"
        )

        if program_context:
            prompt += f"Contexte du programme: {program_context}\n"

        prompt += f"\nInformations du candidat:\n"
        for key, value in candidate_data.items():
            if value:
                prompt += f"- {key}: {value}\n"

        if custom_instructions:
            prompt += f"\nInstructions supplementaires: {custom_instructions}\n"

        prompt += (
            "\nConsignes:\n"
            "- Rediger en francais formel\n"
            "- Ton professionnel et convaincant\n"
            "- Structure claire avec paragraphes\n"
            "- Adapter au programme d'immigration specifique\n"
            "- Inclure les informations du candidat naturellement\n"
            "- Ne pas inventer d'informations non fournies\n"
            "- Format pret a l'emploi (avec date, objet, formules de politesse)\n"
        )

        return prompt

    def _generate_from_template(
        self,
        letter_type: str,
        candidate_data: dict[str, Any],
    ) -> str:
        """Generate letter from template with data substitution."""
        template_info = LETTER_TEMPLATES.get(letter_type)
        if not template_info:
            return f"[Type de lettre non supporte: {letter_type}]"

        template = template_info["template"]

        # Add defaults
        defaults = {
            "date": datetime.utcnow().strftime("%d/%m/%Y"),
            "city": "Montreal",
            "full_name": "[Nom complet]",
            "email": "[Email]",
            "phone": "[Telephone]",
            "nationality": "[Nationalite]",
            "program_name": "[Programme]",
            "reference_number": "[Numero de dossier]",
            "professional_background": "[Parcours professionnel]",
            "motivations": "[Motivations]",
            "objectives": "[Objectifs]",
            "subject": "[Sujet]",
            "context": "[Contexte]",
            "explanation": "[Explication]",
            "measures_taken": "[Mesures prises]",
            "sponsor_name": "[Nom du garant]",
            "sponsor_address": "[Adresse du garant]",
            "relationship": "[Relation]",
            "annual_income": "[Revenu annuel]",
            "savings": "[Epargne]",
            "sponsor_employment": "[Emploi du garant]",
            "covered_expenses": "[Frais couverts]",
            "duration": "[Duree]",
            "documents_list": "[Liste des documents]",
            "date_of_birth": "[Date de naissance]",
            "passport_number": "[Numero de passeport]",
        }

        # Merge candidate data over defaults
        data = {**defaults, **candidate_data}

        try:
            return template.format_map(_SafeDict(data))
        except Exception:
            return template.format_map(_SafeDict(defaults))

    def get_available_templates(self) -> list[dict[str, str]]:
        """List available letter templates."""
        return [
            {"type": lt.value, "title": info["title"]}
            for lt, info in LETTER_TEMPLATES.items()
        ]


class _SafeDict(dict):
    """Dict that returns placeholder for missing keys."""

    def __missing__(self, key: str) -> str:
        return f"[{key}]"


# Singleton
letter_generator = LetterGenerator()
