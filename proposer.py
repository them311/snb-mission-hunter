"""
SNB Mission Hunter — Génération de propositions via Claude API.
Utilise le profil Baptiste Thevenot (profile.py).
NE JAMAIS mentionner S&B Consulting dans les propositions.
"""

import logging
from typing import Optional
import anthropic
from models import RawMission, Proposal
from profile import PROFILE, get_proposal_prompt

logger = logging.getLogger("snb.proposer")


class Proposer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, mission: RawMission, **kwargs) -> Optional[Proposal]:
        """Génère une proposition personnalisée pour la mission."""
        prompt = get_proposal_prompt(
            mission_title=mission.title,
            mission_desc=mission.description or "",
            mission_source=mission.source,
        )
        # Detect language
        text_sample = f"{mission.title} {(mission.description or '')[:200]}"
        lang = self._detect_language(text_sample)

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()

            # Safety: remove any S&B mention that might slip through
            text = text.replace("S&B Consulting", "").replace("S&B", "")

            return Proposal(
                mission_id="",
                text=text,
                language=lang,
                template_used="profile_v1",
                status="ready",
            )
        except Exception as e:
            logger.error(f"Erreur génération proposition: {e}")
            return None

    @staticmethod
    def _detect_language(text: str) -> str:
        text_lower = text.lower()
        fr = ["développeur", "recherche", "projet", "entreprise", "nous", "besoin"]
        en = ["developer", "looking", "project", "company", "need", "team"]
        fc = sum(1 for m in fr if m in text_lower)
        ec = sum(1 for m in en if m in text_lower)
        return "en" if ec > fc else "fr"
