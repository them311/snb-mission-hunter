"""
SNB Mission Hunter — Scorer v2 (compatible main.py)
Calibré pour : Baptiste Thévenot, Consultant Web & IA, TJM 450€/j, Toulouse/Remote

Signatures conservées :
  score_mission(raw: RawMission, profile: dict) -> int
  classify_mission(raw: RawMission) -> str

Score max : 100
Composantes :
  Stack match     0-35 pts  (pondération principale)
  Budget/TJM      0-25 pts
  Type mission    0-20 pts  (consulting > dev pur)
  Remote          0-10 pts
  Fraîcheur       0-10 pts
  Pénalités       illimitées (CDI, Java, stage…)

Seuil génération proposition : 55 (config.py SCORE_THRESHOLD)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import RawMission

logger = logging.getLogger("snb.scorer")

# ─────────────────────────────────────────────────────────────
# DICTIONNAIRES DE SCORING — modifier ici pour recalibrer
# ─────────────────────────────────────────────────────────────

# Mots-clés stack technique (contribution : 0–35 pts, cappés)
STACK_WEIGHTS: dict[str, int] = {
    # IA / Agents — cœur de valeur Baptiste
    "intelligence artificielle": 10, "agent ia": 10, "agent ai": 10,
    "llm": 9, "claude": 9, "openai": 9, "gpt": 8, "chatgpt": 8,
    "langchain": 8, "langgraph": 8, "rag": 8,
    "automatisation ia": 9, "automation ai": 9, "ai automation": 9,
    "generative ai": 9, "gen ai": 9, "prompt engineering": 8,
    "machine learning": 7, "deep learning": 7, "nlp": 7,
    "fine-tuning": 7, "embedding": 7, "computer vision": 6,
    # Web full-stack
    "react": 8, "next.js": 8, "nextjs": 8, "vue": 7, "nuxt": 7,
    "typescript": 7, "javascript": 6, "node.js": 7, "nodejs": 7,
    "python": 8, "fastapi": 8, "django": 7, "flask": 7,
    "api rest": 7, "rest api": 7, "graphql": 7,
    # Shopify / e-commerce
    "shopify": 9, "shopify plus": 9, "e-commerce": 7, "ecommerce": 7,
    "liquid": 7, "prestashop": 6, "woocommerce": 6,
    # Data / BDD
    "supabase": 8, "postgresql": 7, "sql": 6,
    # DevOps / Cloud (secondaire)
    "docker": 6, "railway": 6, "netlify": 6, "vercel": 6,
    "aws": 5, "gcp": 5, "azure": 5,
    # No-code / Automatisation
    "n8n": 8, "make": 7, "zapier": 6, "airtable": 6,
    "notion api": 7, "webflow": 7,
    # Consulting
    "consultant": 5, "consulting": 5, "conseil": 5,
    "stratégie digitale": 6, "transformation digitale": 6,
    "audit": 5, "accompagnement": 4,
}

# Mots-clés type de mission (contribution : 0–20 pts, cappés)
MISSION_TYPE_WEIGHTS: dict[str, int] = {
    "consultant ia": 20, "consultant web": 18, "expert ia": 20,
    "expert agent": 20, "expert llm": 18, "consultant freelance": 15,
    "développeur ia": 15, "développeur ai": 15, "ai developer": 15,
    "full stack": 12, "fullstack": 12, "full-stack": 12,
    "développeur web": 10, "web developer": 10,
    "poc": 10, "prototype": 10, "mvp": 10,
    "mission courte": 12, "audit technique": 12, "audit ia": 15,
    "freelance": 8, "indépendant": 8,
    "formation": 8, "coaching": 8,
}

# Pénalités (pas de cap — peut être très négatif)
NEGATIVE_WEIGHTS: dict[str, int] = {
    # Hors compétences
    "java": -8, "spring boot": -8, "kotlin": -8, "swift": -8,
    "unity": -10, "unreal": -10, "c++": -8, "c#": -6,
    "sap": -10, "oracle": -8, "golang": -5,
    "ios developer": -10, "android developer": -10,
    # CDI / emploi salarié
    "cdi": -15, "cdd": -10, "temps plein": -10, "full time employee": -10,
    "poste de": -8, "nous recrutons": -8, "rejoignez notre équipe": -5,
    # Sans budget
    "stage": -20, "stagiaire": -20, "alternance": -20, "bénévole": -20,
}

# Types de mission pour classify_mission()
MISSION_TYPES = {
    "ia_consulting": ["consultant ia", "expert ia", "agent ia", "expert agent", "expert llm",
                      "intelligence artificielle", "llm", "rag", "langchain", "automatisation ia"],
    "web_dev": ["react", "next.js", "nextjs", "vue", "nuxt", "typescript", "javascript",
                "développeur web", "web developer", "full stack", "fullstack"],
    "shopify": ["shopify", "shopify plus", "liquid", "e-commerce", "ecommerce"],
    "automation": ["n8n", "make", "zapier", "automatisation", "automation", "workflow", "airtable"],
    "consulting": ["consultant", "consulting", "conseil", "stratégie", "audit", "accompagnement"],
    "data": ["machine learning", "deep learning", "nlp", "sql", "postgresql", "supabase", "data"],
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _lower_text(raw) -> str:
    """Texte consolidé lowercase pour matching."""
    parts = [
        raw.title or "",
        raw.description or "",
        " ".join(raw.tags or []),
    ]
    return " ".join(parts).lower()


def _score_stack(text: str) -> int:
    total = sum(pts for kw, pts in STACK_WEIGHTS.items() if kw in text)
    return min(total, 35)


def _score_mission_type(text: str) -> int:
    total = sum(pts for kw, pts in MISSION_TYPE_WEIGHTS.items() if kw in text)
    return min(total, 20)


def _score_budget(raw) -> int:
    """Budget vs TJM 450€/j — max 25 pts."""
    budget = raw.budget_max or raw.budget_min
    if budget is None:
        return 10  # neutre si inconnu
    if budget >= 10000:
        return 25
    if budget >= 5000:
        return 20
    if budget >= 1000:
        return 12
    if budget >= 500:
        return 6
    return 2


def _score_remote(raw) -> int:
    """Remote / localité — max 10 pts."""
    if getattr(raw, "remote", True):
        return 10
    text = _lower_text(raw)
    if "remote" in text or "télétravail" in text or "à distance" in text:
        return 10
    if "toulouse" in text or "occitanie" in text:
        return 8
    if any(v in text for v in ["paris", "lyon", "bordeaux", "france"]):
        return 4
    return 2


def _score_freshness(raw) -> int:
    """Fraîcheur — max 10 pts."""
    posted_at = getattr(raw, "posted_at", None)
    if not posted_at:
        return 5  # neutre
    now = datetime.now(timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    age_hours = (now - posted_at).total_seconds() / 3600
    if age_hours <= 24:
        return 10
    if age_hours <= 72:
        return 8
    if age_hours <= 168:
        return 5
    if age_hours <= 336:
        return 2
    return 0


def _score_negatives(text: str) -> int:
    return sum(pts for kw, pts in NEGATIVE_WEIGHTS.items() if kw in text)


# ─────────────────────────────────────────────────────────────
# API PUBLIQUE — signatures compatibles avec main.py
# ─────────────────────────────────────────────────────────────

def score_mission(raw, profile: dict | None = None) -> int:
    """
    Calcule le score d'une RawMission (0–100).

    Args:
        raw     : RawMission instance
        profile : dict profil S&B (optionnel — réservé usage futur)

    Returns:
        int score entre 0 et 100
    """
    text = _lower_text(raw)

    pts = (
        _score_stack(text)
        + _score_mission_type(text)
        + _score_budget(raw)
        + _score_remote(raw)
        + _score_freshness(raw)
        + _score_negatives(text)
    )

    score = max(0, min(100, pts))
    logger.debug(f"score_mission [{raw.source}] '{raw.title[:50]}' → {score}")
    return score


def classify_mission(raw) -> str:
    """
    Classifie une RawMission dans une catégorie métier.

    Returns:
        str parmi : 'ia_consulting', 'web_dev', 'shopify', 'automation',
                    'consulting', 'data', 'other'
    """
    text = _lower_text(raw)

    # Ordre de priorité : catégories les plus spécifiques en premier
    for mission_type, keywords in MISSION_TYPES.items():
        if any(kw in text for kw in keywords):
            return mission_type

    return "other"
