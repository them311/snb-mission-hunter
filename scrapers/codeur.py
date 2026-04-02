"""
SNB Mission Hunter — Codeur.com scraper.
Plateforme française majeure pour freelances.
Tier 2 — scan toutes les 30 min.
"""

import logging
import re
from typing import List
from datetime import datetime, timezone
import aiohttp
from bs4 import BeautifulSoup

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.codeur")

CODEUR_URLS = [
    "https://www.codeur.com/projects?categories=site-internet-e-commerce&sort=created_at",
    "https://www.codeur.com/projects?categories=application-web&sort=created_at",
    "https://www.codeur.com/projects?categories=marketing-seo-sem&sort=created_at",
    "https://www.codeur.com/projects?categories=graphisme-design&sort=created_at",
    "https://www.codeur.com/projects?categories=developpement-informatique&sort=created_at",
    "https://www.codeur.com/projects?categories=redaction-traduction&sort=created_at",
]


class CodeurScraper(BaseScraper):
    name = "codeur"
    tier = 2

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen = set()

        async with aiohttp.ClientSession() as session:
            for url in CODEUR_URLS:
                try:
                    async with session.get(
                        url,
                        headers=DEFAULT_HEADERS,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as resp:
                        if resp.status != 200:
                            logger.debug(f"Codeur.com {resp.status}: {url[:60]}")
                            continue
                        html = await resp.text()
                except Exception as e:
                    logger.debug(f"Codeur.com error: {e}")
                    continue

                soup = BeautifulSoup(html, "html.parser")
                # Codeur.com utilise des cards de projet
                cards = soup.select("a[href*='/projects/']")

                for card in cards[:15]:
                    try:
                        link = card.get("href", "")
                        if not link or link in seen or "/projects?" in link:
                            continue
                        if not link.startswith("http"):
                            link = f"https://www.codeur.com{link}"
                        seen.add(link)

                        title = card.get_text(strip=True)
                        if not title or len(title) < 10:
                            continue

                        parent = card.find_parent("div") or card.find_parent("article")
                        parent_text = parent.get_text(" ", strip=True) if parent else title

                        # Budget
                        budget_raw = ""
                        budget_min = None
                        budget_max = None
                        budget_match = re.search(r'(\d[\d\s]*)\s*€', parent_text)
                        if budget_match:
                            val = float(budget_match.group(1).replace(" ", ""))
                            budget_raw = f"{val:.0f}€"
                            budget_min = val
                            budget_max = val

                        # Tags
                        text_lower = parent_text.lower()
                        tech_kw = ["react", "python", "shopify", "wordpress", "php", "javascript",
                                   "node", "seo", "design", "logo", "e-commerce", "prestashop",
                                   "woocommerce", "figma", "ia", "automatisation", "next.js"]
                        tags = [kw for kw in tech_kw if kw in text_lower]

                        missions.append(RawMission(
                            title=title[:200],
                            company="Codeur Client",
                            description=parent_text[:2000],
                            budget_raw=budget_raw,
                            budget_min=budget_min,
                            budget_max=budget_max,
                            source="codeur",
                            source_url=link,
                            tags=tags,
                            remote=True,  # Codeur.com = tout remote
                            posted_at=None,
                        ))
                    except Exception as e:
                        logger.debug(f"Skip Codeur card: {e}")
                        continue

        return missions
