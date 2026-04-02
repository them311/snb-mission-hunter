"""Himalayas.app — Remote jobs JSON API. Tier 1."""
import logging
from typing import List
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.himalayas")

class HimalayasScraper(BaseScraper):
    name = "himalayas"
    tier = 1
    API_URL = "https://himalayas.app/jobs/api?limit=50"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept": "application/json",
                   "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"Himalayas HTTP {resp.status}")
                data = await resp.json(content_type=None)

        for job in (data.get("jobs") or [])[:50]:
            try:
                title = (job.get("title") or "").strip()
                if not title:
                    continue
                company = (job.get("companyName") or "").strip()
                desc = (job.get("excerpt") or "").strip()
                salary_min = job.get("minSalary")
                salary_max = job.get("maxSalary")
                currency = job.get("currency", "USD")
                budget = ""
                bmin = bmax = None
                if salary_min and salary_max:
                    budget = f"{currency} {salary_min:,}-{salary_max:,}/yr"
                    bmin = round(float(salary_min) / 220)
                    bmax = round(float(salary_max) / 220)
                tags = [job.get("seniority","")] if job.get("seniority") else []
                slug = job.get("companySlug","")
                url = f"https://himalayas.app/companies/{slug}/jobs" if slug else ""
                missions.append(RawMission(
                    title=title, company=company, description=desc[:3000],
                    budget_raw=budget, budget_min=bmin, budget_max=bmax,
                    source="himalayas", source_url=url,
                    tags=tags[:10], remote=True, posted_at=None))
            except Exception as e:
                logger.debug(f"Skip: {e}")
        return missions
