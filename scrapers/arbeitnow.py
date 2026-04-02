"""Arbeitnow — Remote jobs JSON API. Tier 1. Returns 100+ jobs."""
import logging
from typing import List
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.arbeitnow")

class ArbeitnowScraper(BaseScraper):
    name = "arbeitnow"
    tier = 1
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept": "application/json",
                   "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"Arbeitnow HTTP {resp.status}")
                data = await resp.json(content_type=None)
        for job in (data.get("data") or [])[:60]:
            try:
                title = (job.get("title") or "").strip()
                if not title: continue
                company = (job.get("company_name") or "").strip()
                desc = (job.get("description") or "").strip()
                tags_raw = job.get("tags") or []
                remote = job.get("remote", False)
                url = job.get("url", "")
                location = job.get("location", "")
                tags = tags_raw[:10]
                if location and location not in tags:
                    tags.append(location)
                missions.append(RawMission(
                    title=title, company=company, description=desc[:3000],
                    budget_raw="", budget_min=None, budget_max=None,
                    source="arbeitnow", source_url=url,
                    tags=tags[:10], remote=remote, posted_at=None))
            except Exception as e:
                logger.debug(f"Skip: {e}")
        return missions
