"""
SNB Mission Hunter — We Work Remotely RSS scraper.
Tier 1 — scan toutes les 10 min.
"""

import logging
import re
from typing import List
from datetime import datetime
from email.utils import parsedate_to_datetime
import aiohttp
import feedparser

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.wwr")

WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]


class WeWorkRemotelyScraper(BaseScraper):
    name = "weworkremotely"
    tier = 1

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen = set()

        async with aiohttp.ClientSession() as session:
            for feed_url in WWR_FEEDS:
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
                    logger.debug(f"WWR feed error: {e}")
                    continue

                feed = feedparser.parse(content)

                for entry in feed.entries[:20]:
                    try:
                        link = entry.get("link", "")
                        if link in seen:
                            continue
                        seen.add(link)

                        title = entry.get("title", "").strip()
                        if not title:
                            continue

                        # Séparer company du titre si format "Company: Title"
                        company = "Unknown"
                        if ":" in title:
                            parts = title.split(":", 1)
                            company = parts[0].strip()
                            title = parts[1].strip()

                        description = re.sub(r'<[^>]+>', ' ', entry.get("summary", "")).strip()

                        posted_at = None
                        if entry.get("published"):
                            try:
                                posted_at = parsedate_to_datetime(entry.published)
                            except Exception:
                                pass

                        # Extraire tags depuis le titre/description
                        tags = []
                        tech_keywords = [
                            "python", "react", "node", "typescript", "javascript",
                            "aws", "docker", "kubernetes", "go", "rust", "ruby",
                            "rails", "django", "flask", "vue", "angular", "shopify",
                        ]
                        text_lower = f"{title} {description}".lower()
                        tags = [kw for kw in tech_keywords if kw in text_lower]

                        missions.append(RawMission(
                            title=title,
                            company=company,
                            description=description[:3000],
                            budget_raw="",
                            source="weworkremotely",
                            source_url=link,
                            tags=tags,
                            remote=True,
                            posted_at=posted_at,
                        ))
                    except Exception as e:
                        logger.debug(f"Skip WWR entry: {e}")
                        continue

        return missions
