"""
SNB Mission Hunter — Indeed France RSS scraper.
Missions freelance et consulting en France.
Tier 1 — scan toutes les 5 min.
"""

import logging
import re
from typing import List
from email.utils import parsedate_to_datetime
import aiohttp
import feedparser

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.indeed_fr")

INDEED_FR_FEEDS = [
    # Freelance React/Next.js France
    "https://fr.indeed.com/rss?q=freelance+react&l=France&sort=date",
    "https://fr.indeed.com/rss?q=freelance+next.js&l=France&sort=date",
    # Freelance Shopify France
    "https://fr.indeed.com/rss?q=freelance+shopify&l=France&sort=date",
    # Freelance IA / Automatisation France
    "https://fr.indeed.com/rss?q=freelance+intelligence+artificielle&l=France&sort=date",
    "https://fr.indeed.com/rss?q=freelance+automatisation+python&l=France&sort=date",
    # Freelance consultant digital France
    "https://fr.indeed.com/rss?q=consultant+digital+freelance&l=France&sort=date",
    # Freelance développeur web France
    "https://fr.indeed.com/rss?q=freelance+d%C3%A9veloppeur+web&l=France&sort=date",
    # Missions consulting stratégie
    "https://fr.indeed.com/rss?q=consultant+strat%C3%A9gie+digitale&l=France&sort=date",
    # Toulouse spécifique
    "https://fr.indeed.com/rss?q=freelance+d%C3%A9veloppeur&l=Toulouse&sort=date",
    "https://fr.indeed.com/rss?q=freelance+consultant&l=Toulouse&sort=date",
]


class IndeedFRScraper(BaseScraper):
    name = "indeed_fr"
    tier = 1

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen_urls = set()

        async with aiohttp.ClientSession() as session:
            for feed_url in INDEED_FR_FEEDS:
                try:
                    async with session.get(
                        feed_url,
                        headers=DEFAULT_HEADERS,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status != 200:
                            continue
                        content = await resp.text()
                except Exception as e:
                    logger.debug(f"Indeed FR feed error: {e}")
                    continue

                feed = feedparser.parse(content)

                for entry in feed.entries[:15]:
                    try:
                        link = entry.get("link", "")
                        if link in seen_urls:
                            continue
                        seen_urls.add(link)

                        title = entry.get("title", "").strip()
                        if not title:
                            continue

                        description = re.sub(r'<[^>]+>', ' ', entry.get("summary", "")).strip()

                        # Extraire company
                        company = "Indeed Client"
                        company_match = re.search(r'(?:chez|at|par)\s+([^-–]+)', title)
                        if company_match:
                            company = company_match.group(1).strip()

                        # Budget extraction
                        budget_raw = ""
                        budget_min = None
                        budget_max = None
                        tjm = re.search(r'(\d{3,4})\s*€?\s*/?\s*(?:jour|j\b|day)', f"{title} {description}", re.I)
                        if tjm:
                            budget_min = float(tjm.group(1))
                            budget_max = budget_min
                            budget_raw = f"{budget_min:.0f}€/j"
                        salary = re.search(r'(\d[\d\s]*)\s*€\s*/\s*(?:an|mois|month|year)', f"{title} {description}", re.I)
                        if salary and not budget_raw:
                            val = float(salary.group(1).replace(" ", ""))
                            budget_raw = f"{val:.0f}€"

                        # Date
                        posted_at = None
                        if entry.get("published"):
                            try:
                                posted_at = parsedate_to_datetime(entry.published)
                            except Exception:
                                pass

                        # Tags
                        text_lower = f"{title} {description}".lower()
                        tech_kw = ["react", "python", "shopify", "next.js", "node", "typescript",
                                   "docker", "aws", "ia", "ai", "devops", "angular", "vue",
                                   "wordpress", "php", "java", "consulting", "stratégie"]
                        tags = [kw for kw in tech_kw if kw in text_lower]

                        # Remote
                        remote = any(kw in text_lower for kw in ["remote", "télétravail", "home office", "à distance"])

                        missions.append(RawMission(
                            title=title,
                            company=company,
                            description=description[:3000],
                            budget_raw=budget_raw,
                            budget_min=budget_min,
                            budget_max=budget_max,
                            source="indeed_fr",
                            source_url=link,
                            tags=tags,
                            remote=remote,
                            posted_at=posted_at,
                        ))
                    except Exception as e:
                        logger.debug(f"Skip Indeed FR entry: {e}")
                        continue

        return missions
