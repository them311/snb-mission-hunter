"""
SNB Mission Hunter — Génération de propositions via Claude API.
"""

import json
import logging
from typing import Optional
import anthropic
from models import RawMission, Proposal

logger = logging.getLogger("snb.proposer")

TEMPLATES = {
    "web": """Bonjour [Client],

[Résumé besoin 1 phrase] — c'est exactement ce que je fais au quotidien.

J'ai construit l'intégralité du site e-commerce de La Française des Sauces sur Shopify (thème custom Liquid, SEO, tunnel de conversion). Résultat : un site premium fonctionnel de A à Z.

Mon approche :
1. [Cadrage/audit]
2. [Développement]
3. [Tests et livraison]

Ce qui nous différencie : stratégie business + exécution technique. Chaque décision de code sert un objectif business.

Disponible pour un échange de 15 min cette semaine ?

Baptiste Thévenot — S&B Consulting""",

    "ia": """Bonjour [Client],

[Résumé besoin] — sujet que je maîtrise de bout en bout.

J'ai conçu un système multi-agents IA complet (6 agents, Claude API, intégration Shopify MCP) et un configurateur de recettes interactif propulsé par l'IA, en production.

Ce que je propose :
1. [Cadrage technique]
2. [Architecture + développement]
3. [Déploiement + monitoring]

Mon avantage : je travaille quotidiennement avec Claude et GPT en production réelle depuis plus d'un an. Pas de démo, du concret.

On en discute ?

Baptiste Thévenot — S&B Consulting""",

    "consulting": """Bonjour [Client],

[Reformulation besoin] — un enjeu que je comprends pour l'avoir vécu en fondant ma propre marque premium (La Française des Sauces — positionnement, B2B, GMS).

Mon approche :
- Diagnostic sans complaisance
- Recommandations priorisées par impact
- Plan d'action concret avec livrables datés

La différence S&B : Master Stratégie (TBS) + exécution opérationnelle. Pas de slides qui restent au tiroir.

Disponible cette semaine.

Baptiste Thévenot — S&B Consulting, Toulouse""",

    "data": """Bonjour [Client],

[Résumé besoin data]. Expérience concrète : extraction multi-sources, CRM 1300+ contacts structurés, pipelines automatisés sur Railway.

Approche :
1. Analyse sources et contraintes
2. Développement scraper/pipeline Python
3. Structuration, nettoyage, livraison (CSV/JSON/DB/dashboard)

Fiabilité et respect des CGU. Disponible immédiatement.

Baptiste Thévenot — S&B Consulting""",

    "design": """Bonjour [Client],

[Résumé besoin]. J'ai créé de A à Z l'identité de La Française des Sauces — naming, packaging, charte graphique, site web, supports de communication.

Ce que j'apporte :
- Vision cohérente (chaque choix de design sert le positionnement)
- Exécution technique (print-ready, SVG, PDF)
- Regard stratégique (qu'est-ce que votre identité doit communiquer ?)

Prêt à échanger.

Baptiste Thévenot — S&B Consulting""",

    "other": """Bonjour [Client],

[Résumé besoin]. En tant que fondateur de La Française des Sauces et co-fondateur de S&B Consulting, j'interviens sur la stratégie, le web, l'IA et l'automatisation avec un seul objectif : des résultats concrets.

Mon approche :
1. Cadrage du besoin
2. Exécution rapide et itérative
3. Livraison + suivi

Disponible pour un échange cette semaine.

Baptiste Thévenot — S&B Consulting""",
}


class Proposer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        mission: RawMission,
        profile: dict,
        mission_type: str = "other",
    ) -> Optional[Proposal]:
        """Génère une proposition personnalisée pour la mission."""
        template = TEMPLATES.get(mission_type, TEMPLATES["other"])

        # Détecte la langue
        text_sample = f"{mission.title} {mission.description[:200]}"
        lang = self._detect_language(text_sample)

        portfolio_str = "\n".join(f"  - {p}" for p in profile.get("portfolio", []))

        prompt = f"""Tu es le rédacteur de propositions commerciales pour S&B Consulting.

PROFIL DU CONSULTANT :
- Nom : {profile['name']}
- Compétences clés : {', '.join(profile.get('keywords', [])[:20])}
- Formation : {profile.get('formation', '')}
- Portfolio :
{portfolio_str}

MISSION :
- Titre : {mission.title}
- Client : {mission.company}
- Description : {mission.description[:2000]}
- Budget : {mission.budget_raw}
- Plateforme : {mission.source}
- Tags : {', '.join(mission.tags[:10])}

TEMPLATE DE BASE :
{template}

INSTRUCTIONS :
1. Adapte le template à cette mission spécifique
2. Mentionne 1-2 réalisations du portfolio directement pertinentes
3. Propose 3 étapes concrètes pour le projet
4. Adapte le ton à la plateforme ({mission.source})
5. Rédige en {'anglais' if lang == 'en' else 'espagnol' if lang == 'es' else 'français'}
6. Maximum 200 mots
7. Ne jamais mentionner que la proposition est générée par IA
8. Si tu mentionnes LFDS, utilise TOUJOURS "Sauce Beurre & Herbes Fraîches by LFDS"
9. Sois direct et concret, pas de flatterie creuse

Rédige la proposition directement, sans commentaire ni préambule."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            return Proposal(
                mission_id="",  # Sera set après insertion de la mission
                text=text,
                language=lang,
                template_used=mission_type,
                status="ready",
            )
        except Exception as e:
            logger.error(f"Erreur génération proposition: {e}")
            return None

    @staticmethod
    def _detect_language(text: str) -> str:
        text_lower = text.lower()
        fr_markers = ["développeur", "recherche", "projet", "entreprise", "nous", "besoin", "équipe"]
        en_markers = ["developer", "looking", "project", "company", "need", "team", "experience"]
        es_markers = ["desarrollador", "proyecto", "empresa", "necesitamos", "equipo", "experiencia"]

        fr_count = sum(1 for m in fr_markers if m in text_lower)
        en_count = sum(1 for m in en_markers if m in text_lower)
        es_count = sum(1 for m in es_markers if m in text_lower)

        if es_count > fr_count and es_count > en_count:
            return "es"
        if en_count > fr_count:
            return "en"
        return "fr"
