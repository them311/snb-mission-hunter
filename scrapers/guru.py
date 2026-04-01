"""
SNB Mission Hunter — Guru.com RSS scraper.
Tier 2 — scan toutes les 30 min.
"""

import logging
import re
from typing import List
from email.utils import parsedate_to_datetime
import aiohttp
import feedparser

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.guru")

GURU_FEEDS = [
    "https://www.guru.com/rss/jobs/",
]


class GuruScraper(BaseScraper):
    name = "guru"
    tier = 2

    async def fetch(self) -> List[RawMission]:
        missions = []

        async with aiohttp.ClientSession() as session:
            for feed_url in GURU_FEEDS:
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
                    logger.debug(f"Guru feed error: {e}")
                    continue

                feed = feedparser.parse(content)

                for entry in feed.entries[:25]:
                    try:
                        title = entry.get("title", "").strip()
                        link = entry.get("link", "")
                        if not title:
                            continue

                        description = re.sub(r'<[^>]+>', ' ', entry.get("summary", "")).strip()

                        # Budget extraction
                        budget_raw = ""
                        budget_min = None
                        budget_max = None
                        budget_match = re.search(r'\$([0-9,]+)\s*-\s*\$([0-9,]+)', f"{title} {description}")
                        if budget_match:
                            budget_min = float(budget_match.group(1).replace(",", ""))
                            budget_max = float(budget_match.group(2).replace(",", ""))
                            budget_raw = f"${budget_min:.0f} - ${budget_max:.0f}"

                        posted_at = None
                        if entry.get("published"):
                            try:
                                posted_at = parsedate_to_datetime(entry.published)
                            except Exception:
                                pass

                        missions.append(RawMission(
                            title=title,
                            company="Guru Client",
                            description=description[:3000],
                            budget_raw=budget_raw,
                            budget_min=budget_min,
                            budget_max=budget_max,
                            source="guru",
                            source_url=link,
                            tags=[],
                            remote=True,
                            posted_at=posted_at,
                        ))
                    except Exception as e:
                        logger.debug(f"Skip Guru entry: {e}")
                        continue

        return missions
