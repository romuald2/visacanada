"""AI Compliance Verification Agent using Claude API.

Analyzes documents against program requirements to produce a conformity score.
Checks: completeness, validity, cross-reference consistency.
"""

import json
from datetime import date, datetime
from typing import Any

import httpx

from app.core.config import settings


class ComplianceVerificationError(Exception):
    """Custom exception for compliance verification failures."""
    pass


class ComplianceAgent:
    """Claude API-powered compliance verification agent."""

    def __init__(self):
        self._api_key = settings.anthropic_api_key
        self._api_url = "https://api.anthropic.com/v1/messages"
        self._model = "claude-sonnet-4-20250514"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def verify_compliance(
        self,
        program_name: str,
        program_requirements: list[dict],
        submitted_documents: list[dict],
        extracted_data: list[dict],
    ) -> dict[str, Any]:
        """Run full compliance verification.

        Args:
            program_name: Name of the immigration program
            program_requirements: List of required documents with priority
            submitted_documents: List of submitted document metadata
            extracted_data: OCR-extracted data from documents

        Returns:
            Detailed compliance report with scores and recommendations
        """
        if not self.is_configured:
            # Return rule-based analysis when Claude API is not configured
            return self._rule_based_verification(
                program_requirements, submitted_documents, extracted_data
            )

        prompt = self._build_verification_prompt(
            program_name, program_requirements, submitted_documents, extracted_data
        )

        try:
            response = await self._call_claude(prompt)
            return self._parse_compliance_response(response)
        except Exception as e:
            # Fallback to rule-based on API failure
            return self._rule_based_verification(
                program_requirements, submitted_documents, extracted_data
            )

    def _build_verification_prompt(
        self,
        program_name: str,
        requirements: list[dict],
        documents: list[dict],
        extracted_data: list[dict],
    ) -> str:
        """Build the prompt for Claude compliance analysis."""
        req_text = json.dumps(requirements, ensure_ascii=False, indent=2)
        docs_text = json.dumps(documents, ensure_ascii=False, indent=2)
        extracted_text = json.dumps(extracted_data, ensure_ascii=False, indent=2)

        return f"""Tu es un expert en immigration canadienne. Analyse la conformité d'un dossier.

## Programme: {program_name}

## Documents requis par le programme:
{req_text}

## Documents soumis par le candidat:
{docs_text}

## Données extraites des documents (OCR):
{extracted_text}

## Analyse demandée:
1. **Complétude** (40 points): Vérifie que tous les documents obligatoires sont fournis
2. **Validité** (30 points): Vérifie les dates d'expiration, formats acceptés, qualité
3. **Cohérence** (30 points): Cross-référencement des noms, dates, montants entre documents

Réponds UNIQUEMENT avec un JSON valide (pas de texte avant ou après):
{{
    "global_score": <float 0-100>,
    "completeness": {{
        "score": <float 0-100>,
        "weight": 0.4,
        "missing_documents": ["list of missing mandatory documents"],
        "optional_missing": ["list of missing optional documents"]
    }},
    "validity": {{
        "score": <float 0-100>,
        "weight": 0.3,
        "issues": [
            {{"document": "name", "issue": "description", "severity": "high|medium|low"}}
        ]
    }},
    "consistency": {{
        "score": <float 0-100>,
        "weight": 0.3,
        "issues": [
            {{"field": "name", "documents": ["doc1", "doc2"], "issue": "description", "severity": "high|medium|low"}}
        ]
    }},
    "recommendations": [
        {{"priority": "high|medium|low", "action": "description of what to do"}}
    ],
    "summary": "Brief overall assessment in French"
}}"""

    async def _call_claude(self, prompt: str) -> str:
        """Call Claude API and return the response text."""
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self._api_url, headers=headers, json=payload
            )

            if response.status_code != 200:
                raise ComplianceVerificationError(
                    f"Claude API error ({response.status_code}): {response.text[:200]}"
                )

            data = response.json()
            content = data.get("content", [])
            if content:
                return content[0].get("text", "")
            return ""

    def _parse_compliance_response(self, response_text: str) -> dict[str, Any]:
        """Parse Claude's JSON response into structured compliance report."""
        # Try to extract JSON from response
        text = response_text.strip()

        # Handle potential markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            result = json.loads(text)
            # Validate required fields
            if "global_score" not in result:
                result["global_score"] = 0.0
            return result
        except json.JSONDecodeError:
            raise ComplianceVerificationError(
                "Impossible de parser la réponse de l'IA"
            )

    def _rule_based_verification(
        self,
        requirements: list[dict],
        documents: list[dict],
        extracted_data: list[dict],
    ) -> dict[str, Any]:
        """Rule-based compliance verification (fallback when AI unavailable)."""
        # Completeness check
        mandatory_reqs = [r for r in requirements if r.get("priority") == "mandatory"]
        optional_reqs = [r for r in requirements if r.get("priority") != "mandatory"]

        doc_types = {d.get("document_type", "") for d in documents}
        doc_names = {d.get("file_name", "").lower() for d in documents}

        missing_mandatory = []
        for req in mandatory_reqs:
            req_type = req.get("document_type", "")
            req_name = req.get("document_name", "")
            if req_type not in doc_types and not any(
                req_type.lower() in name for name in doc_names
            ):
                missing_mandatory.append(req_name)

        missing_optional = []
        for req in optional_reqs:
            req_type = req.get("document_type", "")
            if req_type not in doc_types:
                missing_optional.append(req.get("document_name", ""))

        # Completeness score
        if mandatory_reqs:
            completeness_score = (
                (len(mandatory_reqs) - len(missing_mandatory)) / len(mandatory_reqs)
            ) * 100
        else:
            completeness_score = 100.0

        # Validity check
        validity_issues = []
        validity_score = 100.0

        for data in extracted_data:
            fields = data.get("fields", {})

            # Check passport expiry
            expiry = fields.get("expiry_date", {}).get("value")
            if expiry:
                try:
                    expiry_date = date.fromisoformat(str(expiry))
                    if expiry_date < date.today():
                        validity_issues.append({
                            "document": "Passeport",
                            "issue": "Document expiré",
                            "severity": "high",
                        })
                        validity_score -= 30
                except (ValueError, TypeError):
                    pass

            # Check low confidence scores
            for field_name, field_data in fields.items():
                confidence = field_data.get("confidence", 1.0)
                if isinstance(confidence, (int, float)) and confidence < 0.7:
                    validity_issues.append({
                        "document": data.get("type", "unknown"),
                        "issue": f"Faible confiance OCR pour {field_name}: {confidence:.0%}",
                        "severity": "medium",
                    })
                    validity_score -= 5

        validity_score = max(0, validity_score)

        # Consistency check (basic name matching)
        consistency_score = 100.0
        consistency_issues = []
        names_found = set()

        for data in extracted_data:
            fields = data.get("fields", {})
            first = fields.get("first_name", {}).get("value", "")
            last = fields.get("last_name", {}).get("value", "")
            if first and last:
                names_found.add(f"{first} {last}".upper())

        if len(names_found) > 1:
            consistency_issues.append({
                "field": "name",
                "documents": list(names_found),
                "issue": "Noms différents trouvés entre les documents",
                "severity": "high",
            })
            consistency_score -= 25

        consistency_score = max(0, consistency_score)

        # Global score (weighted)
        global_score = (
            completeness_score * 0.4
            + validity_score * 0.3
            + consistency_score * 0.3
        )

        # Recommendations
        recommendations = []
        if missing_mandatory:
            for doc in missing_mandatory:
                recommendations.append({
                    "priority": "high",
                    "action": f"Fournir le document manquant: {doc}",
                })

        if validity_issues:
            for issue in validity_issues:
                if issue["severity"] == "high":
                    recommendations.append({
                        "priority": "high",
                        "action": f"{issue['document']}: {issue['issue']}",
                    })

        if consistency_issues:
            recommendations.append({
                "priority": "medium",
                "action": "Vérifier la cohérence des noms entre les documents",
            })

        if missing_optional:
            for doc in missing_optional[:3]:
                recommendations.append({
                    "priority": "low",
                    "action": f"Document recommandé manquant: {doc}",
                })

        return {
            "global_score": round(global_score, 1),
            "completeness": {
                "score": round(completeness_score, 1),
                "weight": 0.4,
                "missing_documents": missing_mandatory,
                "optional_missing": missing_optional,
            },
            "validity": {
                "score": round(validity_score, 1),
                "weight": 0.3,
                "issues": validity_issues,
            },
            "consistency": {
                "score": round(consistency_score, 1),
                "weight": 0.3,
                "issues": consistency_issues,
            },
            "recommendations": recommendations,
            "summary": (
                f"Score global: {global_score:.0f}/100. "
                f"{len(missing_mandatory)} document(s) obligatoire(s) manquant(s). "
                f"{len(validity_issues)} problème(s) de validité. "
                f"{len(consistency_issues)} incohérence(s) détectée(s)."
            ),
            "method": "rule_based",
        }


# Singleton
compliance_agent = ComplianceAgent()
