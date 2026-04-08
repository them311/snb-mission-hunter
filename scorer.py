"""
SNB Mission Hunter — Scorer v2
Calibré pour : Baptiste Thévenot, Consultant Web & IA, TJM 450€/j, Toulouse/Remote
Seuil proposal : 55 (abaissé depuis 70 — scorer v1 sous-estimait les missions FR)

Score max théorique : 100
Composantes :
  - Stack match        : 0-35 pts  (pondération principale)
  - Budget/TJM         : 0-25 pts
  - Type de mission    : 0-20 pts  (consulting > dev pur)
  - Remote & localité  : 0-10 pts
  - Urgence/fraîcheur  : 0-10 pts
"""

import re
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional


@dataclass
class Mission:
    title: str
    description: str
    source: str
    url: str
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    is_remote: bool = True
    location: Optional[str] = None
    posted_at: Optional[datetime] = None
    tags: list = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


# ─────────────────────────────────────────────────────────────────────────────
# PROFIL BAPTISTE — à ajuster ici uniquement
# ─────────────────────────────────────────────────────────────────────────────

# Stack technique — pondérée par maîtrise + valeur marché
STACK_WEIGHTS = {
    # IA / Agents (cœur de valeur, très demandé)
    "intelligence artificielle": 10, "ia ": 10, " ia": 10, "agent ia": 10,
    "agent ai": 10, "llm": 9, "claude": 9, "openai": 9, "gpt": 8,
    "chatgpt": 8, "langchain": 8, "langgraph": 8, "rag": 8,
    "automatisation ia": 9, "automation ai": 9, "ai automation": 9,
    "machine learning": 7, "deep learning": 7, "nlp": 7,
    "computer vision": 6, "generative ai": 9, "gen ai": 9,
    "prompt engineering": 8, "fine-tuning": 7, "embedding": 7,

    # Web full-stack
    "react": 8, "next.js": 8, "nextjs": 8, "vue": 7, "nuxt": 7,
    "typescript": 7, "javascript": 6, "node.js": 7, "nodejs": 7,
    "python": 8, "fastapi": 8, "django": 7, "flask": 7,
    "api rest": 7, "rest api": 7, "graphql": 7, "websocket": 6,

    # E-commerce / Shopify (expertise LFDS)
    "shopify": 9, "e-commerce": 7, "ecommerce": 7, "prestashop": 6,
    "woocommerce": 6, "liquid": 7, "shopify plus": 9,

    # DevOps / Cloud (compétences secondaires)
    "supabase": 8, "postgresql": 7, "sql": 6, "nosql": 5,
    "docker": 6, "railway": 6, "netlify": 6, "vercel": 6,
    "aws": 5, "gcp": 5, "azure": 5, "kubernetes": 4,

    # No-code / Automatisation
    "n8n": 8, "make": 7, "zapier": 6, "airtable": 6,
    "notion api": 7, "bubble": 5, "webflow": 7,

    # Consulting / Stratégie (bonus fort)
    "consultant": 5, "consulting": 5, "conseil": 5,
    "stratégie digitale": 6, "transformation digitale": 6,
    "audit": 5, "accompagnement": 4,
    "product manager": 4, "product owner": 4, "chef de projet": 4,

    # Design / UX (compétences légères)
    "figma": 4, "ui/ux": 4, "ux design": 4, "design system": 5,
}

# Mots-clés mission idéale (type de mission)
MISSION_TYPE_KEYWORDS = {
    "consultant ia": 20, "consultant web": 18, "consultant freelance": 15,
    "expert ia": 20, "expert agent": 20, "expert llm": 18,
    "développeur ia": 15, "développeur ai": 15, "ai developer": 15,
    "full stack": 12, "fullstack": 12, "full-stack": 12,
    "développeur web": 10, "web developer": 10,
    "freelance": 8, "indépendant": 8,
    "mission courte": 12,  # missions courtes = bon TJM
    "poc": 10, "prototype": 10, "mvp": 10,
    "audit technique": 12, "audit ia": 15,
    "formation": 8, "coaching": 8,
}

# Mots-clés négatifs (pénalité)
NEGATIVE_KEYWORDS = {
    # Hors compétences
    "java": -8, "spring": -8, "kotlin": -8, "swift": -8,
    "ios developer": -10, "android developer": -10, "mobile native": -8,
    "unity": -10, "unreal": -10, "game": -5,
    "c++": -8, "c#": -6, "rust": -5, "golang": -5, "go developer": -5,
    "sap": -10, "salesforce": -5, "oracle": -8,
    "devops only": -5, "sre": -5, "infrastructure only": -5,
    "data scientist only": -3,
    # Emploi CDI (pas freelance)
    "cdi": -15, "cdd": -10, "temps plein": -10, "full time employee": -10,
    "poste de": -8, "nous recrutons": -8, "rejoignez notre équipe": -5,
    # Budget trop bas
    "stage": -20, "stagiaire": -20, "alternance": -20, "alternant": -20,
    "bénévole": -20,
}

PROPOSAL_SCORE_THRESHOLD = 55  # Abaissé depuis 70


def _text(mission: Mission) -> str:
    """Texte consolidé pour matching (lowercase)."""
    parts = [
        mission.title or "",
        mission.description or "",
        " ".join(mission.tags or []),
        mission.location or "",
    ]
    return " ".join(parts).lower()


def _score_stack(text: str) -> tuple[int, list]:
    """Stack match — max 35 pts."""
    total = 0
    matched = []
    for kw, pts in STACK_WEIGHTS.items():
        if kw in text:
            total += pts
            matched.append((kw, pts))
    # Cap à 35
    total = min(total, 35)
    return total, matched


def _score_mission_type(text: str) -> tuple[int, list]:
    """Type de mission — max 20 pts."""
    total = 0
    matched = []
    for kw, pts in MISSION_TYPE_KEYWORDS.items():
        if kw in text:
            total += pts
            matched.append((kw, pts))
    return min(total, 20), matched


def _score_budget(mission: Mission) -> tuple[int, str]:
    """Budget vs TJM 450€/j — max 25 pts.
    
    Logique :
    - Si budget journalier ≥ 450€ → 25 pts
    - Si budget total ≥ 5 000€ → 20 pts (mission ≥ ~11j)
    - Si budget 1 000-5 000€ → 12 pts
    - Si budget < 500€ → 3 pts
    - Si budget inconnu → 10 pts (neutre, pas pénalisé)
    """
    bmin = mission.budget_min
    bmax = mission.budget_max
    budget = bmax or bmin

    if budget is None:
        # Budget non renseigné → neutre
        return 10, "inconnu (neutre)"

    if budget >= 10000:
        return 25, f"{budget:.0f}€ (excellent)"
    if budget >= 5000:
        return 20, f"{budget:.0f}€ (bon)"
    if budget >= 1000:
        return 12, f"{budget:.0f}€ (acceptable)"
    if budget >= 500:
        return 6, f"{budget:.0f}€ (faible)"
    return 2, f"{budget:.0f}€ (trop bas)"


def _score_remote(mission: Mission) -> tuple[int, str]:
    """Remote / localité — max 10 pts."""
    text = _text(mission)

    # Remote explicite
    if mission.is_remote or "remote" in text or "télétravail" in text or "à distance" in text:
        return 10, "remote confirmé"

    # Toulouse ou Occitanie
    if "toulouse" in text or "occitanie" in text or "31" in (mission.location or ""):
        return 8, "Toulouse/local"

    # Autre ville France
    if any(v in text for v in ["paris", "lyon", "bordeaux", "nantes", "marseille", "france"]):
        return 4, "France (déplacement possible)"

    # International en présentiel
    return 2, "présentiel étranger (pénalité)"


def _score_freshness(mission: Mission) -> tuple[int, str]:
    """Fraîcheur — max 10 pts."""
    if not mission.posted_at:
        return 5, "date inconnue (neutre)"

    now = datetime.now(timezone.utc)
    if mission.posted_at.tzinfo is None:
        mission.posted_at = mission.posted_at.replace(tzinfo=timezone.utc)

    age_hours = (now - mission.posted_at).total_seconds() / 3600

    if age_hours <= 24:
        return 10, "< 24h (très fraîche)"
    if age_hours <= 72:
        return 8, "< 3j"
    if age_hours <= 168:
        return 5, "< 7j"
    if age_hours <= 336:
        return 2, "< 14j"
    return 0, "> 14j (ancienne)"


def _score_negatives(text: str) -> tuple[int, list]:
    """Pénalités — pas de cap (peut devenir très négatif)."""
    total = 0
    matched = []
    for kw, pts in NEGATIVE_KEYWORDS.items():
        if kw in text:
            total += pts
            matched.append((kw, pts))
    return total, matched


def score_mission(mission: Mission) -> dict:
    """
    Calcule le score d'une mission.
    
    Returns:
        dict avec 'score' (0-100), 'breakdown' (détail), 'generate_proposal' (bool)
    """
    text = _text(mission)

    stack_pts, stack_matches = _score_stack(text)
    type_pts, type_matches = _score_mission_type(text)
    budget_pts, budget_detail = _score_budget(mission)
    remote_pts, remote_detail = _score_remote(mission)
    fresh_pts, fresh_detail = _score_freshness(mission)
    neg_pts, neg_matches = _score_negatives(text)

    raw = stack_pts + type_pts + budget_pts + remote_pts + fresh_pts + neg_pts
    final = max(0, min(100, raw))

    breakdown = {
        "stack": {"pts": stack_pts, "max": 35, "matches": stack_matches[:5]},
        "type": {"pts": type_pts, "max": 20, "matches": type_matches[:3]},
        "budget": {"pts": budget_pts, "max": 25, "detail": budget_detail},
        "remote": {"pts": remote_pts, "max": 10, "detail": remote_detail},
        "freshness": {"pts": fresh_pts, "max": 10, "detail": fresh_detail},
        "negatives": {"pts": neg_pts, "matches": neg_matches},
    }

    return {
        "score": final,
        "breakdown": breakdown,
        "generate_proposal": final >= PROPOSAL_SCORE_THRESHOLD,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TEST RAPIDE
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from datetime import timedelta

    missions_test = [
        Mission(
            title="Recherche consultant IA - expert agent",
            description="Mission de conseil en intelligence artificielle pour déployer des agents LLM. Budget 3000-8000€. Télétravail possible.",
            source="codeur",
            url="https://codeur.com/test1",
            budget_min=3000,
            budget_max=8000,
            is_remote=True,
            posted_at=datetime.now(timezone.utc) - timedelta(hours=12),
        ),
        Mission(
            title="Développeur React / Next.js - Startup IA",
            description="Rejoignez notre équipe full-time pour développer une plateforme React + FastAPI + LLM. CDI Paris.",
            source="linkedin",
            url="https://linkedin.com/test2",
            budget_min=None,
            budget_max=None,
            is_remote=False,
            location="Paris",
        ),
        Mission(
            title="Audit et déploiement agent IA pour PME",
            description="Consultant freelance pour audit IA, prototype n8n + Claude API. Mission courte 5-10 jours. Remote. Budget 5000€.",
            source="codeur",
            url="https://codeur.com/test3",
            budget_min=5000,
            budget_max=5000,
            is_remote=True,
            posted_at=datetime.now(timezone.utc) - timedelta(hours=2),
        ),
        Mission(
            title="Java Spring Boot Developer",
            description="Développeur Java senior pour migration microservices. CDI. SAP expérience souhaitée.",
            source="weworkremotely",
            url="https://weworkremotely.com/test4",
        ),
        Mission(
            title="Développement Shopify store + IA personnalisation",
            description="Mission e-commerce Shopify avec personnalisation produit par IA. Toulouse ou remote. Budget 2000-4000€.",
            source="codeur",
            url="https://codeur.com/test5",
            budget_min=2000,
            budget_max=4000,
            is_remote=True,
            location="Toulouse",
        ),
    ]

    print("=" * 60)
    print("SNB SCORER v2 — TEST DE CALIBRATION")
    print(f"Seuil génération proposition : {PROPOSAL_SCORE_THRESHOLD}")
    print("=" * 60)

    for m in missions_test:
        result = score_mission(m)
        s = result["score"]
        gen = "✅ PROPOSAL" if result["generate_proposal"] else "❌ skip"
        b = result["breakdown"]
        print(f"\n[{s:3d}/100] {gen}")
        print(f"  📋 {m.title[:60]}")
        print(f"  Stack: {b['stack']['pts']}/35 | Type: {b['type']['pts']}/20 | Budget: {b['budget']['pts']}/25 | Remote: {b['remote']['pts']}/10 | Fresh: {b['freshness']['pts']}/10 | Neg: {b['negatives']['pts']}")
        if b["negatives"]["matches"]:
            print(f"  ⚠️  Pénalités: {[m[0] for m in b['negatives']['matches']]}")
