"""Freelancer.com — RSS feed scraper. Tier 2."""
import logging
from typing import List
from datetime import datetime
import aiohttp
import feedparser
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.freelancercom")

class FreelancerComScraper(BaseScraper):
    name = "freelancercom"
    tier = 2
    RSS_URL = "https://www.freelancer.com/rss.xml"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.RSS_URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"Freelancer HTTP {resp.status}")
                xml = await resp.text()
        feed = feedparser.parse(xml)
        for entry in feed.entries[:40]:
            try:
                title = (entry.get("title") or "").strip()
                if not title: continue
                desc = (entry.get("summary") or "").strip()
                link = entry.get("link", "")
                posted = None
                if entry.get("published_parsed"):
                    posted = datetime(*entry.published_parsed[:6])
                missions.append(RawMission(
                    title=title, company="", description=desc[:3000],
                    budget_raw="", budget_min=None, budget_max=None,
                    source="freelancercom", source_url=link,
                    tags=[], remote=True, posted_at=posted))
            except Exception as e:
                logger.debug(f"Skip: {e}")
        return missions
