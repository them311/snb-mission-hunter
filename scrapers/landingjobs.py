"""Landing.jobs — EU tech jobs JSON API. Tier 2."""
import logging
from typing import List
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.landingjobs")

class LandingJobsScraper(BaseScraper):
    name = "landingjobs"
    tier = 2
    API_URL = "https://landing.jobs/api/v1/offers?limit=30"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept": "application/json",
                   "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"Landing.jobs HTTP {resp.status}")
                data = await resp.json(content_type=None)
        for job in (data if isinstance(data, list) else [])[:30]:
            try:
                title = (job.get("title") or "").strip()
                if not title: continue
                desc = (job.get("main_requirements") or "").strip()
                currency = job.get("currency_code", "EUR")
                salary_from = job.get("salary_from")
                salary_to = job.get("salary_to")
                budget = ""
                if salary_from and salary_to:
                    budget = f"{currency} {salary_from}-{salary_to}/yr"
                url = f"https://landing.jobs/offer/{job.get('id','')}"
                missions.append(RawMission(
                    title=title, company="", description=desc[:3000],
                    budget_raw=budget, budget_min=None, budget_max=None,
                    source="landingjobs", source_url=url,
                    tags=[], remote=True, posted_at=None))
            except Exception as e:
                logger.debug(f"Skip: {e}")
        return missions
