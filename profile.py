"""
Profil candidat Baptiste Thevenot — utilisé par le proposer IA.
NE JAMAIS mentionner S&B Consulting dans les propositions.
"""

PROFILE = {
    "name": "Baptiste Thevenot",
    "title": "Consultant Web & IA",
    "tjm": 450,
    "currency": "EUR",
    "location": "Toulouse, France",
    "remote": True,
    "travel_radius_km": 50,
    "languages": ["Français (natif)", "Anglais (courant)", "Espagnol (courant)"],
    "bio_short": (
        "Consultant freelance spécialisé en développement web, "
        "intelligence artificielle et automatisation de processus."
    ),
    "bio_full": (
        "Consultant freelance spécialisé en développement web, intelligence artificielle "
        "et automatisation de processus. Titulaire d'un Master 2 en Stratégie et Conseil "
        "(TBS Toulouse), j'accompagne entreprises et startups dans la création de sites "
        "performants, l'intégration d'outils IA (Claude, OpenAI, n8n) et l'automatisation "
        "de leurs workflows. Expériences internationales et forte culture produit."
    ),
    "skills_primary": [
        "React.js", "Node.js", "Shopify", "Prompt Engineering",
        "Stratégie digitale", "Claude API", "OpenAI",
    ],
    "skills_secondary": [
        "HTML/CSS", "JavaScript", "Python", "Figma", "UI/UX Design",
        "Zapier", "n8n", "Automatisation", "E-commerce",
    ],
    "domains": [
        "E-commerce", "Formation / e-learning", "Secteur public",
        "Entreprises du numérique", "Startups",
    ],
    "experience_years": 5,
    "education": "Master 2 Stratégie et Conseil — TBS Toulouse Business School",
    "experiences": [
        {
            "role": "Consultant Web & IA — Freelance",
            "period": "Janvier 2024 — Aujourd'hui",
            "desc": (
                "Accompagnement d'entreprises et startups : sites performants "
                "(React.js, Node.js, Shopify), intégration IA (Claude API, OpenAI, "
                "Chatbots), automatisation workflows (n8n, Zapier). UI/UX Figma."
            ),
        },
        {
            "role": "Master 2 Stratégie et Conseil — TBS",
            "period": "2021 — 2023",
            "desc": (
                "Stratégie d'entreprise, conseil en transformation digitale, "
                "gestion de projets. Expérience internationale à Barcelone."
            ),
        },
    ],
    "malt_url": "https://www.malt.fr/profile/baptistethevenot1",
    "email": "bp.thevenot@gmail.com",
    "phone": "06 86 50 43 79",
}


def get_proposal_prompt(mission_title, mission_desc, mission_source, language="auto", mission_type="other"):
    """Génère le prompt Claude pour créer une proposition personnalisée."""
    lang = language
    if lang == "auto":
        lang = "fr" if any(w in (mission_desc or "").lower() for w in
            ["bonjour", "nous", "recherchons", "entreprise", "projet", "poste"]) else "en"

    p = PROFILE
    skills = ", ".join(p["skills_primary"][:5])

    # Templates par type de mission
    type_hooks = {
        "ia": "Mon expertise IA : agents autonomes multi-agents en production (Claude API, OpenAI), chatbots, RAG, automatisation intelligente.",
        "web": "Mon expertise web : sites e-commerce Shopify custom, apps React/Next.js, APIs Node.js, responsive design premium.",
        "data": "Mon expertise data : pipelines ETL, scraping intelligent, dashboards analytics, automatisation de reporting.",
        "consulting": "Mon expertise conseil : Master Stratégie & Consulting (TBS), transformation digitale, audit opérationnel, conduite du changement.",
        "design": "Mon expertise design : branding premium, identité visuelle, UX/UI Figma, supports marketing print et digital.",
        "other": "Profil polyvalent : développement web, IA, consulting stratégique, e-commerce.",
    }
    type_hook = type_hooks.get(mission_type, type_hooks["other"])

    if lang == "fr":
        return f"""Tu es {p['name']}, {p['title']} freelance basé à {p['location']}.
{p['bio_full']}
{type_hook}

Compétences clés : {skills}
TJM : {p['tjm']}€/jour | Langues : FR/EN/ES

MISSION :
Titre : {mission_title}
Source : {mission_source}
Description : {mission_desc[:2000]}

Rédige une proposition de candidature professionnelle et personnalisée.
- Accroche qui montre que tu as compris le besoin du client
- 2-3 points montrant comment tes compétences répondent au besoin
- Proposition de valeur concrète (pas de bla-bla)
- Disponibilité et prochaine étape
- Ton professionnel, direct, confiant sans arrogance
- Maximum 200 mots
- NE MENTIONNE JAMAIS "S&B Consulting"
- Signe : Baptiste Thevenot"""
    else:
        return f"""You are {p['name']}, a freelance {p['title']} based in {p['location']}.
{p['bio_full']}

Key skills: {skills}
Day rate: €{p['tjm']}/day | Languages: FR/EN/ES

MISSION:
Title: {mission_title}
Source: {mission_source}
Description: {mission_desc[:2000]}

Write a professional, personalized proposal.
- Hook showing you understand the client's need
- 2-3 points matching your skills to their requirements
- Concrete value proposition (no fluff)
- Availability and next step
- Professional, direct, confident tone
- Maximum 200 words
- NEVER mention "S&B Consulting"
- Sign: Baptiste Thevenot"""
