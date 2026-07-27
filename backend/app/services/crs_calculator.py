"""CRS (Comprehensive Ranking System) Calculator.

Implements the official IRCC scoring grid for Express Entry:
- Core/Human capital factors (age, education, language, Canadian experience)
- Spouse/common-law partner factors
- Skill transferability factors
- Additional points (PNP, job offer, Canadian education, French language)

Reference: https://www.canada.ca/en/immigration-refugees-citizenship/services/
           immigrate-canada/express-entry/eligibility/criteria-comprehensive-ranking-system.html
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MaritalStatus(str, Enum):
    single = "single"
    married = "married"


class EducationLevel(str, Enum):
    none = "none"
    secondary = "secondary"
    one_year_post_secondary = "one_year_post_secondary"
    two_year_post_secondary = "two_year_post_secondary"
    three_year_post_secondary = "three_year_post_secondary"
    bachelors = "bachelors"
    two_or_more_post_secondary = "two_or_more_post_secondary"
    masters = "masters"
    doctoral = "doctoral"


class LanguageTestType(str, Enum):
    ielts = "ielts"
    celpip = "celpip"
    tef = "tef"
    tcf = "tcf"


@dataclass
class LanguageScore:
    """Language test scores (reading, writing, listening, speaking)."""
    reading: float = 0
    writing: float = 0
    listening: float = 0
    speaking: float = 0
    test_type: str = "ielts"
# PLACEHOLDER_CRS_CLASSES


@dataclass
class CRSInput:
    """All inputs needed for CRS calculation."""
    # Personal
    age: int = 30
    marital_status: str = "single"

    # Education
    education_level: str = "bachelors"
    canadian_education: str = "none"  # none, one_year, two_year, three_plus

    # Language - First official language
    first_language: LanguageScore = field(default_factory=LanguageScore)
    # Language - Second official language (optional)
    second_language: LanguageScore | None = None

    # Work experience
    canadian_experience_years: int = 0
    foreign_experience_years: int = 0

    # Spouse factors (if married)
    spouse_education: str = "none"
    spouse_language: LanguageScore | None = None
    spouse_canadian_experience_years: int = 0

    # Additional
    has_provincial_nomination: bool = False
    has_arranged_employment: bool = False  # LMIA job offer
    arranged_employment_noc: str = "other"  # 00, 0ab, other
    has_canadian_sibling: bool = False
    french_language_proficiency: str = "none"  # none, clb7, clb7_plus


# =============================================================================
# CLB Conversion Tables
# =============================================================================

# IELTS to CLB mapping
IELTS_TO_CLB = {
    "reading": [
        (8.0, 10), (7.0, 9), (6.5, 8), (6.0, 7),
        (5.0, 6), (4.0, 5), (3.5, 4),
    ],
    "writing": [
        (7.5, 10), (7.0, 9), (6.5, 8), (6.0, 7),
        (5.5, 6), (5.0, 5), (4.0, 4),
    ],
    "listening": [
        (8.5, 10), (8.0, 9), (7.5, 8), (6.0, 7),
        (5.5, 6), (5.0, 5), (4.5, 4),
    ],
    "speaking": [
        (7.5, 10), (7.0, 9), (6.5, 8), (6.0, 7),
        (5.5, 6), (5.0, 5), (4.0, 4),
    ],
}


def ielts_to_clb(score: float, skill: str) -> int:
    """Convert IELTS score to CLB level."""
    for threshold, clb in IELTS_TO_CLB.get(skill, []):
        if score >= threshold:
            return clb
    return 3


def language_to_clb(lang: LanguageScore) -> dict[str, int]:
    """Convert language scores to CLB levels."""
    if lang.test_type in ("ielts", "celpip"):
        return {
            "reading": ielts_to_clb(lang.reading, "reading"),
            "writing": ielts_to_clb(lang.writing, "writing"),
            "listening": ielts_to_clb(lang.listening, "listening"),
            "speaking": ielts_to_clb(lang.speaking, "speaking"),
        }
    # TEF/TCF - simplified: assume scores are already CLB equivalent
    return {
        "reading": int(lang.reading),
        "writing": int(lang.writing),
        "listening": int(lang.listening),
        "speaking": int(lang.speaking),
    }
# PLACEHOLDER_SCORING_TABLES


# =============================================================================
# CRS Point Tables (Single applicant / With spouse)
# =============================================================================

# Age points: (age, single_points, married_points)
AGE_POINTS = {
    17: (0, 0), 18: (99, 90), 19: (105, 95), 20: (110, 100),
    21: (110, 100), 22: (110, 100), 23: (110, 100), 24: (110, 100),
    25: (110, 100), 26: (110, 100), 27: (110, 100), 28: (110, 100),
    29: (110, 100), 30: (105, 95), 31: (99, 90), 32: (94, 85),
    33: (88, 80), 34: (83, 75), 35: (77, 70), 36: (72, 65),
    37: (66, 60), 38: (61, 55), 39: (55, 50), 40: (50, 45),
    41: (39, 35), 42: (28, 25), 43: (17, 15), 44: (6, 5),
    45: (0, 0),
}

# Education points: (level, single_points, married_points)
EDUCATION_POINTS = {
    "none": (0, 0),
    "secondary": (30, 28),
    "one_year_post_secondary": (90, 84),
    "two_year_post_secondary": (98, 91),
    "three_year_post_secondary": (120, 112),
    "bachelors": (120, 112),
    "two_or_more_post_secondary": (128, 119),
    "masters": (135, 126),
    "doctoral": (150, 140),
}

# First official language points per CLB level (per ability)
# (clb_level, single_points, married_points)
FIRST_LANG_POINTS = {
    3: (0, 0), 4: (6, 6), 5: (6, 6), 6: (9, 8),
    7: (17, 16), 8: (23, 22), 9: (31, 29), 10: (34, 32),
}

# Second official language points per CLB level (per ability)
SECOND_LANG_POINTS = {
    0: (0, 0), 1: (0, 0), 2: (0, 0), 3: (0, 0), 4: (0, 0),
    5: (1, 1), 6: (1, 1), 7: (3, 3), 8: (3, 3), 9: (6, 6), 10: (6, 6),
}

# Canadian work experience points
CANADIAN_EXP_POINTS = {
    0: (0, 0), 1: (40, 35), 2: (53, 46), 3: (64, 56),
    4: (72, 63), 5: (80, 70),
}

# Spouse education points
SPOUSE_EDUCATION_POINTS = {
    "none": 0, "secondary": 2, "one_year_post_secondary": 6,
    "two_year_post_secondary": 7, "three_year_post_secondary": 8,
    "bachelors": 8, "two_or_more_post_secondary": 9,
    "masters": 10, "doctoral": 10,
}

# Spouse language points per CLB (per ability)
SPOUSE_LANG_POINTS = {
    0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 1,
    7: 3, 8: 3, 9: 5, 10: 5,
}

# Spouse Canadian experience
SPOUSE_EXP_POINTS = {0: 0, 1: 5, 2: 7, 3: 8, 4: 9, 5: 10}
# PLACEHOLDER_CALCULATOR


# =============================================================================
# Skill Transferability Points
# =============================================================================

def _calc_skill_transferability(
    education: str,
    clb_levels: dict[str, int],
    canadian_exp: int,
    foreign_exp: int,
) -> dict[str, int]:
    """Calculate skill transferability (max 100 points total).

    Combines: education + language, education + experience,
    foreign experience + language, foreign experience + canadian experience.
    Certificate of qualification not implemented (trade-specific).
    """
    details = {}
    min_clb = min(clb_levels.values())
    edu_level = _education_rank(education)

    # Education + Language (max 50)
    edu_lang = 0
    if edu_level >= 3 and min_clb >= 7:  # post-secondary + CLB7+
        if min_clb >= 9 and edu_level >= 5:
            edu_lang = 50
        elif min_clb >= 9 or edu_level >= 5:
            edu_lang = 25
        else:
            edu_lang = 13
    details["education_language"] = edu_lang

    # Education + Canadian experience (max 50)
    edu_exp = 0
    if edu_level >= 3 and canadian_exp >= 1:
        if edu_level >= 5 and canadian_exp >= 2:
            edu_exp = 50
        elif edu_level >= 5 or canadian_exp >= 2:
            edu_exp = 25
        else:
            edu_exp = 13
    details["education_canadian_exp"] = edu_exp

    # Foreign experience + Language (max 50)
    foreign_lang = 0
    if foreign_exp >= 1 and min_clb >= 7:
        if foreign_exp >= 3 and min_clb >= 9:
            foreign_lang = 50
        elif foreign_exp >= 3 or min_clb >= 9:
            foreign_lang = 25
        else:
            foreign_lang = 13
    details["foreign_exp_language"] = foreign_lang

    # Foreign experience + Canadian experience (max 50)
    foreign_canadian = 0
    if foreign_exp >= 1 and canadian_exp >= 1:
        if foreign_exp >= 3 and canadian_exp >= 2:
            foreign_canadian = 50
        elif foreign_exp >= 3 or canadian_exp >= 2:
            foreign_canadian = 25
        else:
            foreign_canadian = 13
    details["foreign_exp_canadian_exp"] = foreign_canadian

    # Total capped at 100
    total = edu_lang + edu_exp + foreign_lang + foreign_canadian
    details["total"] = min(total, 100)
    return details


def _education_rank(level: str) -> int:
    """Rank education level for transferability scoring."""
    ranks = {
        "none": 0, "secondary": 1, "one_year_post_secondary": 2,
        "two_year_post_secondary": 3, "three_year_post_secondary": 4,
        "bachelors": 4, "two_or_more_post_secondary": 5,
        "masters": 5, "doctoral": 6,
    }
    return ranks.get(level, 0)


# =============================================================================
# Main Calculator
# =============================================================================

class CRSCalculator:
    """Calculate CRS score from input data."""

    # Recent rounds for comparison (updated periodically)
    RECENT_ROUNDS = [
        {"date": "2025-12-17", "program": "No program specified", "score": 524, "invitations": 5500},
        {"date": "2025-12-03", "program": "No program specified", "score": 522, "invitations": 5750},
        {"date": "2025-11-19", "program": "No program specified", "score": 529, "invitations": 4000},
        {"date": "2025-11-05", "program": "STEM", "score": 502, "invitations": 2500},
        {"date": "2025-10-22", "program": "No program specified", "score": 531, "invitations": 4000},
        {"date": "2025-10-09", "program": "French language", "score": 410, "invitations": 3200},
    ]

    def calculate(self, input_data: CRSInput) -> dict[str, Any]:
        """Calculate full CRS score with breakdown."""
        is_single = input_data.marital_status == "single"
        idx = 0 if is_single else 1

        # Convert languages to CLB
        first_clb = language_to_clb(input_data.first_language)
        second_clb = (
            language_to_clb(input_data.second_language)
            if input_data.second_language
            else {"reading": 0, "writing": 0, "listening": 0, "speaking": 0}
        )

        # --- Section A: Core/Human Capital ---
        age_pts = self._get_age_points(input_data.age, idx)
        edu_pts = self._get_education_points(input_data.education_level, idx)
        lang1_pts = self._get_first_language_points(first_clb, idx)
        lang2_pts = self._get_second_language_points(second_clb, idx)
        can_exp_pts = self._get_canadian_exp_points(input_data.canadian_experience_years, idx)

        core_total = age_pts + edu_pts + lang1_pts + lang2_pts + can_exp_pts

        # --- Section B: Spouse factors (if married) ---
        spouse_pts = 0
        spouse_edu_pts = 0
        spouse_lang_pts = 0
        spouse_exp_pts = 0
        if not is_single:
            spouse_edu_pts = SPOUSE_EDUCATION_POINTS.get(input_data.spouse_education, 0)
            if input_data.spouse_language:
                spouse_clb = language_to_clb(input_data.spouse_language)
                spouse_lang_pts = sum(
                    SPOUSE_LANG_POINTS.get(min(v, 10), 0)
                    for v in spouse_clb.values()
                )
            spouse_exp_pts = SPOUSE_EXP_POINTS.get(
                min(input_data.spouse_canadian_experience_years, 5), 0
            )
            spouse_pts = spouse_edu_pts + spouse_lang_pts + spouse_exp_pts

        # --- Section C: Skill Transferability (max 100) ---
        transferability = _calc_skill_transferability(
            input_data.education_level,
            first_clb,
            input_data.canadian_experience_years,
            input_data.foreign_experience_years,
        )
        transferability_pts = transferability["total"]

        # --- Section D: Additional Points (max 600) ---
        additional_pts = 0
        additional_details = {}

        if input_data.has_provincial_nomination:
            additional_pts += 600
            additional_details["provincial_nomination"] = 600

        if input_data.has_arranged_employment:
            if input_data.arranged_employment_noc == "00":
                additional_pts += 200
                additional_details["arranged_employment"] = 200
            else:
                additional_pts += 50
                additional_details["arranged_employment"] = 50

        # Canadian education bonus
        can_edu_pts = 0
        if input_data.canadian_education == "one_year":
            can_edu_pts = 15
        elif input_data.canadian_education == "two_year":
            can_edu_pts = 15
        elif input_data.canadian_education == "three_plus":
            can_edu_pts = 30
        if can_edu_pts:
            additional_pts += can_edu_pts
            additional_details["canadian_education"] = can_edu_pts

        # French language
        if input_data.french_language_proficiency == "clb7":
            additional_pts += 25
            additional_details["french_proficiency"] = 25
        elif input_data.french_language_proficiency == "clb7_plus":
            additional_pts += 50
            additional_details["french_proficiency"] = 50

        # Sibling in Canada
        if input_data.has_canadian_sibling:
            additional_pts += 15
            additional_details["canadian_sibling"] = 15

        # --- Total ---
        total = core_total + spouse_pts + transferability_pts + additional_pts

        breakdown = {
            "core_human_capital": {
                "age": age_pts,
                "education": edu_pts,
                "first_language": lang1_pts,
                "second_language": lang2_pts,
                "canadian_experience": can_exp_pts,
                "subtotal": core_total,
            },
            "spouse_factors": {
                "education": spouse_edu_pts,
                "language": spouse_lang_pts,
                "canadian_experience": spouse_exp_pts,
                "subtotal": spouse_pts,
            },
            "skill_transferability": transferability,
            "additional_points": {
                **additional_details,
                "subtotal": additional_pts,
            },
            "total": total,
        }

        # Recommendations
        recommendations = self._generate_recommendations(
            input_data, first_clb, total, breakdown
        )

        return {
            "total_score": total,
            "breakdown": breakdown,
            "clb_levels": {"first": first_clb, "second": second_clb},
            "recommendations": recommendations,
            "recent_rounds": self.RECENT_ROUNDS[:5],
            "eligible_for_ita": total >= self.RECENT_ROUNDS[0]["score"],
        }

    # --- Point lookup helpers ---

    def _get_age_points(self, age: int, idx: int) -> int:
        if age < 18 or age > 44:
            return 0
        return AGE_POINTS.get(age, (0, 0))[idx]

    def _get_education_points(self, level: str, idx: int) -> int:
        return EDUCATION_POINTS.get(level, (0, 0))[idx]

    def _get_first_language_points(self, clb: dict[str, int], idx: int) -> int:
        total = 0
        for skill in ("reading", "writing", "listening", "speaking"):
            level = min(clb.get(skill, 0), 10)
            total += FIRST_LANG_POINTS.get(level, (0, 0))[idx]
        return total

    def _get_second_language_points(self, clb: dict[str, int], idx: int) -> int:
        total = 0
        for skill in ("reading", "writing", "listening", "speaking"):
            level = min(clb.get(skill, 0), 10)
            total += SECOND_LANG_POINTS.get(level, (0, 0))[idx]
        return total

    def _get_canadian_exp_points(self, years: int, idx: int) -> int:
        capped = min(years, 5)
        return CANADIAN_EXP_POINTS.get(capped, (0, 0))[idx]

    # --- Recommendations ---

    def _generate_recommendations(
        self,
        input_data: CRSInput,
        first_clb: dict[str, int],
        total: int,
        breakdown: dict,
    ) -> list[dict[str, Any]]:
        """Generate personalized recommendations to improve CRS score."""
        recs = []
        min_clb = min(first_clb.values())
        latest_cutoff = self.RECENT_ROUNDS[0]["score"]
        gap = latest_cutoff - total

        if gap > 0:
            recs.append({
                "category": "general",
                "message": f"Vous avez besoin de {gap} points supplementaires pour atteindre le dernier seuil ({latest_cutoff}).",
                "priority": "high",
            })

        # Language improvement
        if min_clb < 9:
            potential = sum(
                FIRST_LANG_POINTS.get(9, (0, 0))[0] - FIRST_LANG_POINTS.get(min(v, 10), (0, 0))[0]
                for v in first_clb.values()
            )
            if potential > 0:
                recs.append({
                    "category": "language",
                    "message": f"Ameliorer votre score linguistique a CLB 9+ pourrait ajouter jusqu'a {potential} points.",
                    "priority": "high" if potential >= 20 else "medium",
                })

        # Canadian experience
        if input_data.canadian_experience_years < 3:
            recs.append({
                "category": "experience",
                "message": "Obtenir plus d'experience canadienne augmentera significativement votre score.",
                "priority": "medium",
            })

        # Education upgrade
        if input_data.education_level in ("secondary", "one_year_post_secondary", "two_year_post_secondary"):
            recs.append({
                "category": "education",
                "message": "Un diplome de niveau superieur (maitrise, doctorat) peut ajouter 30-50 points.",
                "priority": "medium",
            })

        # PNP
        if not input_data.has_provincial_nomination:
            recs.append({
                "category": "pnp",
                "message": "Une nomination provinciale (PNP) ajoute 600 points et garantit une invitation.",
                "priority": "high" if gap > 50 else "low",
            })

        # French
        if input_data.french_language_proficiency == "none":
            recs.append({
                "category": "french",
                "message": "Un score TEF/TCF CLB 7+ en francais ajoute 25-50 points bonus.",
                "priority": "medium",
            })

        # Second language
        if not input_data.second_language:
            recs.append({
                "category": "second_language",
                "message": "Passer un test dans la seconde langue officielle peut ajouter jusqu'a 24 points.",
                "priority": "low",
            })

        return recs


# Singleton
crs_calculator = CRSCalculator()

