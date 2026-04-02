"""
SNB Mission Hunter — Free-Work.com scraper (ex Freelance-info).
Le plus gros agrégateur de missions freelance IT en France.
Tier 1 — scan toutes les 5 min.
"""

import logging
import re
from typing import List
from datetime import datetime, timezone
import aiohttp
from bs4 import BeautifulSoup

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.freework")

FREEWORK_URLS = [
    "https://www.free-work.com/fr/tech-it/jobs?query=react&contracts=freelance",
    "https://www.free-work.com/fr/tech-it/jobs?query=shopify&contracts=freelance",
    "https://www.free-work.com/fr/tech-it/jobs?query=python+automatisation&contracts=freelance",
    "https://www.free-work.com/fr/tech-it/jobs?query=intelligence+artificielle&contracts=freelance",
    "https://www.free-work.com/fr/tech-it/jobs?query=next.js&contracts=freelance",
    "https://www.free-work.com/fr/tech-it/jobs?query=consultant+digital&contracts=freelance",
    "https://www.free-work.com/fr/tech-it/jobs?query=devops&contracts=freelance",
    "https://www.free-work.com/fr/tech-it/jobs?query=data+engineer&contracts=freelance",
]


class FreeWorkScraper(BaseScraper):
    name = "freework"
    tier = 1

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen = set()

        async with aiohttp.ClientSession() as session:
            for url in FREEWORK_URLS:
                try:
                    async with session.get(
                        url,
                        headers=DEFAULT_HEADERS,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp:
                        if resp.status != 200:
                            logger.debug(f"Free-Work {resp.status}: {url[:60]}")
                            continue
                        html = await resp.text()
                except Exception as e:
                    logger.debug(f"Free-Work error: {e}")
                    continue

                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select("a[href*='/fr/tech-it/jobs/']")

                for card in cards[:20]:
                    try:
                        link = card.get("href", "")
                        if not link or link in seen:
                            continue
                        if not link.startswith("http"):
                            link = f"https://www.free-work.com{link}"
                        seen.add(link)

                        title = card.get_text(strip=True)
                        if not title or len(title) < 5:
                            continue

                        # Extraire company et TJM du texte parent
                        parent = card.find_parent("div") or card.find_parent("li")
                        parent_text = parent.get_text(" ", strip=True) if parent else ""

                        company = "Free-Work Client"
                        tjm_match = re.search(r'(\d{3,4})\s*€?\s*/?\s*j', parent_text)
                        budget_raw = ""
                        budget_min = None
                        if tjm_match:
                            tjm = float(tjm_match.group(1))
                            budget_raw = f"{tjm:.0f}€/j"
                            budget_min = tjm

                        # Tags depuis le texte
                        tags = []
                        tech_kw = ["react", "python", "shopify", "next.js", "node", "typescript",
                                   "docker", "aws", "ia", "ai", "devops", "angular", "vue"]
                        text_lower = parent_text.lower()
                        tags = [kw for kw in tech_kw if kw in text_lower]

                        missions.append(RawMission(
                            title=title[:200],
                            company=company,
                            description=parent_text[:2000],
                            budget_raw=budget_raw,
                            budget_min=budget_min,
                            budget_max=budget_min,
                            source="freework",
                            source_url=link,
                            tags=tags,
                            remote="remote" in text_lower or "télétravail" in text_lower,
                            posted_at=None,
                        ))
                    except Exception as e:
                        logger.debug(f"Skip Free-Work card: {e}")
                        continue

        return missions
