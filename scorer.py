"""
SNB Mission Hunter — Algorithme de scoring 0-100.

Pondération :
- Skill match : 40%
- Budget match : 20%
- Freshness : 20%
- Remote : 10%
- Client quality : 10% (placeholder)
"""

import logging
from datetime import datetime, timezone
from models import RawMission

logger = logging.getLogger("snb.scorer")

# Mots-clés à fort signal (poids x2)
HIGH_VALUE_KEYWORDS = {
    "claude", "anthropic", "shopify", "next.js", "nextjs", "react",
    "ia", "ai", "automatisation", "automation", "agent", "multi-agent",
    "mcp", "chatbot", "scraping", "python",
}


def classify_mission(mission: RawMission) -> str:
    """Classifie le type de mission à partir du titre + description + tags."""
    text = f"{mission.title} {mission.description} {' '.join(mission.tags)}".lower()

    if any(kw in text for kw in ["ia", "ai", "machine learning", "deep learning",
                                   "chatbot", "gpt", "claude", "llm", "nlp",
                                   "automation", "automatisation", "agent"]):
        return "ia"
    if any(kw in text for kw in ["react", "next", "vue", "angular", "frontend",
                                   "backend", "fullstack", "shopify", "wordpress",
                                   "website", "web app", "site web", "landing"]):
        return "web"
    if any(kw in text for kw in ["data", "scraping", "pipeline", "etl", "sql",
                                   "dashboard", "analytics", "bi", "tableau"]):
        return "data"
    if any(kw in text for kw in ["stratégie", "strategy", "consulting", "conseil",
                                   "transformation", "change management", "audit"]):
        return "consulting"
    if any(kw in text for kw in ["design", "branding", "logo", "identité", "ux",
                                   "ui", "figma", "graphique"]):
        return "design"
    return "other"


def score_mission(mission: RawMission, profile: dict) -> int:
    """Score 0-100 une mission par rapport au profil."""
    score = 0
    keywords = profile.get("keywords", [])
    text = f"{mission.title} {mission.description} {' '.join(mission.tags)}".lower()

    # ── Skill match (0-40) ──
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
        # Bonus amplifié pour les mots-clés à haute valeur
        high_bonus = min(15, high_matches * 4)
        skill_score = min(40, int(base_ratio * 60) + high_bonus)
        score += skill_score

    # ── Budget match (0-20) ──
    tjm_min = profile.get("tjm_min", 350)
    if mission.budget_min is not None and mission.budget_max is not None:
        if mission.budget_min >= tjm_min:
            score += 20
        elif mission.budget_max >= tjm_min:
            score += 12
        elif mission.budget_max >= tjm_min * 0.7:
            score += 5
        # En dessous → 0
    elif mission.budget_min is not None:
        score += 15 if mission.budget_min >= tjm_min else 5
    else:
        score += 8  # Budget inconnu — neutre

    # ── Freshness (0-20) ──
    if mission.posted_at:
        now = datetime.now(timezone.utc)
        posted = mission.posted_at if mission.posted_at.tzinfo else mission.posted_at.replace(tzinfo=timezone.utc)
        age_minutes = (now - posted).total_seconds() / 60
        if age_minutes < 15:
            score += 20
        elif age_minutes < 60:
            score += 16
        elif age_minutes < 180:
            score += 12
        elif age_minutes < 720:
            score += 8
        elif age_minutes < 1440:
            score += 4
        # > 24h → 0
    else:
        score += 5  # Pas de date — petit bonus par défaut

    # ── Remote (0-10) ──
    if mission.remote:
        score += 10
    else:
        score += 3  # Pas forcément remote mais pas disqualifiant

    # ── Client quality (0-10) — placeholder ──
    score += 5  # Valeur neutre, enrichir si data client dispo

    return min(100, max(0, score))
