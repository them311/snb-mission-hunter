"""
SNB Mission Hunter — Scorer v2.
Basé sur v1, mêmes signatures, meilleure calibration profil Baptiste.

score_mission(mission: RawMission, profile: dict) -> int   [0-100]
classify_mission(mission: RawMission) -> str
"""

import logging
from datetime import datetime, timezone
from models import RawMission

logger = logging.getLogger("snb.scorer")

# ── Mots-clés à fort signal ─────────────────────────────────
HIGH_VALUE_KEYWORDS = {
    "claude", "anthropic", "shopify", "next.js", "nextjs", "react",
    "ia", "ai", "automatisation", "automation", "agent", "multi-agent",
    "mcp", "chatbot", "scraping", "python", "llm", "openai", "gpt",
    "langchain", "n8n", "fastapi", "supabase", "rag",
}

# Pénalité CDI / hors-profil
CDI_KEYWORDS = [
    "permanent", "cdi", "indefinite", "unbefristet",
    "full-time employee", "contrat indéterminée",
    "rejoignez notre équipe", "nous recrutons", "temps plein",
]

# Bonus mission freelance / courte durée
FREELANCE_KEYWORDS = [
    "freelance", "mission", "contract", "short-term",
    "part-time", "courte durée", "poc", "prototype", "mvp",
]

# Mots-clés consultant IA — bonus supplémentaire pour le cœur de valeur Baptiste
IA_CONSULTING_KEYWORDS = [
    "consultant ia", "expert ia", "expert agent", "agent ia", "expert llm",
    "consultant intelligence artificielle", "audit ia",
    "automatisation ia", "formation ia", "coaching ia",
]

# Sources FR — bonus contextuel
FR_SOURCES = {"talentfr", "codeur", "freework", "malt"}


def _text(mission):
    """Texte consolidé lowercase (robuste aux tags non-string)."""
    tags_str = " ".join(str(t) for t in (mission.tags or []) if t)
    return f"{mission.title or ''} {mission.description or ''} {tags_str}".lower()


def classify_mission(mission):
    """Classifie une RawMission dans une catégorie métier."""
    text = _text(mission)

    if any(kw in text for kw in ["ia", "ai", "machine learning", "deep learning",
                                  "chatbot", "gpt", "claude", "llm", "nlp",
                                  "automation", "automatisation", "agent",
                                  "intelligence artificielle"]):
        return "ia_consulting"
    if any(kw in text for kw in ["react", "next", "vue", "angular", "frontend",
                                  "backend", "fullstack", "shopify", "wordpress",
                                  "website", "web app", "site web", "landing"]):
        return "web_dev"
    if any(kw in text for kw in ["shopify", "e-commerce", "ecommerce", "liquid",
                                  "prestashop", "woocommerce"]):
        return "shopify"
    if any(kw in text for kw in ["n8n", "make", "zapier", "airtable",
                                  "automatisation", "workflow", "no-code"]):
        return "automation"
    if any(kw in text for kw in ["data", "scraping", "pipeline", "etl", "sql",
                                  "dashboard", "analytics", "bi", "tableau"]):
        return "data"
    if any(kw in text for kw in ["stratégie", "strategy", "consulting", "conseil",
                                  "transformation", "audit"]):
        return "consulting"
    return "other"


def score_mission(mission, profile):
    """Score 0-100 une RawMission par rapport au profil Baptiste."""
    score = 0
    keywords = profile.get("keywords", [])
    text = _text(mission)

    # ── Skill match (0-40) ──────────────────────────────────
    if keywords:
        matches = 0
        high_matches = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text:
                matches += 1
                if kw_lower in HIGH_VALUE_KEYWORDS:
                    high_matches += 1

        base_ratio = matches / len(keywords)
        high_bonus = min(20, high_matches * 5)  # v2: bonus x2 vs v1
        skill_score = min(40, int(base_ratio * 70) + high_bonus)  # v2: ratio amplifié
        score += skill_score

    # ── Bonus consultant IA (cœur de valeur Baptiste) ───────
    # Récompense explicitement les missions IA consulting, souvent mal scorées
    if any(kw in text for kw in IA_CONSULTING_KEYWORDS):
        score += 20

    # ── Budget match (0-20) ─────────────────────────────────
    tjm_min = profile.get("tjm_min", 400)
    if mission.budget_min is not None and mission.budget_max is not None:
        if mission.budget_min >= tjm_min:
            score += 20
        elif mission.budget_max >= tjm_min:
            score += 12
        elif mission.budget_max >= tjm_min * 0.7:
            score += 5
    elif mission.budget_min is not None:
        score += 15 if mission.budget_min >= tjm_min else 5
    else:
        score += 8  # Budget inconnu — neutre

    # ── Freshness (0-20) ────────────────────────────────────
    if mission.posted_at:
        now = datetime.now(timezone.utc)
        posted = mission.posted_at
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        age_min = (now - posted).total_seconds() / 60
        if age_min < 15:
            score += 20
        elif age_min < 60:
            score += 16
        elif age_min < 180:
            score += 12
        elif age_min < 720:
            score += 8
        elif age_min < 1440:
            score += 4
    else:
        score += 5

    # ── Remote (0-10) ───────────────────────────────────────
    score += 10 if mission.remote else 3

    # ── Client quality placeholder (0-10) ───────────────────
    score += 5

    # ── CDI penalty (-25) ────────────────────────────────────
    if any(kw in text for kw in CDI_KEYWORDS):
        score -= 25  # v2: pénalité plus forte que v1 (-20)

    # ── Freelance bonus (+10) ───────────────────────────────
    if any(kw in text for kw in FREELANCE_KEYWORDS):
        score += 10

    # ── France bonus (+5) ───────────────────────────────────
    if mission.source in FR_SOURCES:
        score += 5

    # ── Hors-profil penalties ───────────────────────────────
    off_profile = ["java ", " java", "spring boot", "kotlin", " swift ",
                   "unity", "sap ", "stage ", "stagiaire", "alternance"]
    if any(kw in text for kw in off_profile):
        score -= 15

    return min(100, max(0, score))
