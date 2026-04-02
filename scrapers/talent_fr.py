"""
SNB Mission Hunter — Talent.com France scraper.
Agrégateur d'offres d'emploi et missions en France.
Tier 2 — scan toutes les 30 min.
"""

import logging
import re
from typing import List
import aiohttp
from bs4 import BeautifulSoup

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.talent_fr")

TALENT_URLS = [
    "https://fr.talent.com/jobs?k=freelance+react&l=France",
    "https://fr.talent.com/jobs?k=freelance+python+ia&l=France",
    "https://fr.talent.com/jobs?k=freelance+shopify&l=France",
    "https://fr.talent.com/jobs?k=freelance+consultant+digital&l=France",
    "https://fr.talent.com/jobs?k=freelance+developpeur+web&l=Toulouse",
    "https://fr.talent.com/jobs?k=freelance+automatisation&l=France",
    "https://fr.talent.com/jobs?k=freelance+next.js&l=France",
    "https://fr.talent.com/jobs?k=mission+consultant+strategie&l=France",
]


class TalentFRScraper(BaseScraper):
    name = "talent_fr"
    tier = 2

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen = set()

        async with aiohttp.ClientSession() as session:
            for url in TALENT_URLS:
                try:
                    async with session.get(
                        url,
                        headers=DEFAULT_HEADERS,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp:
                        if resp.status != 200:
                            continue
                        html = await resp.text()
                except Exception as e:
                    logger.debug(f"Talent.com error: {e}")
                    continue

                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select("a[href*='/job/'], a[href*='/view/']")

                for card in cards[:15]:
                    try:
                        link = card.get("href", "")
                        if not link or link in seen:
                            continue
                        if not link.startswith("http"):
                            link = f"https://fr.talent.com{link}"
                        seen.add(link)

                        title = card.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                        parent = card.find_parent("div") or card.find_parent("li")
                        parent_text = parent.get_text(" ", strip=True) if parent else title

                        company = "Talent.com Client"
                        budget_raw = ""
                        budget_min = None
                        tjm = re.search(r'(\d{3,4})\s*€?\s*/?\s*(?:jour|j\b)', parent_text, re.I)
                        if tjm:
                            budget_min = float(tjm.group(1))
                            budget_raw = f"{budget_min:.0f}€/j"

                        text_lower = parent_text.lower()
                        tech_kw = ["react", "python", "shopify", "next.js", "node", "typescript",
                                   "docker", "aws", "ia", "ai", "devops", "consulting"]
                        tags = [kw for kw in tech_kw if kw in text_lower]
                        remote = "remote" in text_lower or "télétravail" in text_lower

                        missions.append(RawMission(
                            title=title[:200],
                            company=company,
                            description=parent_text[:2000],
                            budget_raw=budget_raw,
                            budget_min=budget_min,
                            budget_max=budget_min,
                            source="talent_fr",
                            source_url=link,
                            tags=tags,
                            remote=remote,
                            posted_at=None,
                        ))
                    except Exception as e:
                        logger.debug(f"Skip Talent card: {e}")
                        continue

        return missions
