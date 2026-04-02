"""WorkingNomads — Remote jobs JSON API. Tier 1."""
import logging
from typing import List
from datetime import datetime
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.workingnomads")

class WorkingNomadsScraper(BaseScraper):
    name = "workingnomads"
    tier = 1
    API_URL = "https://www.workingnomads.com/api/exposed_jobs/"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept": "application/json",
                   "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"WorkingNomads HTTP {resp.status}")
                data = await resp.json(content_type=None)
        for job in (data if isinstance(data, list) else [])[:40]:
            try:
                title = (job.get("title") or "").strip()
                if not title: continue
                company = (job.get("company_name") or "").strip()
                desc = (job.get("description") or "").strip()
                category = job.get("category_name", "")
                tags_raw = job.get("tags", "")
                tags = [t.strip() for t in str(tags_raw).split(",") if t.strip()] if tags_raw else []
                if category and category not in tags:
                    tags.append(category)
                location = job.get("location", "")
                url = job.get("url", "")
                posted = None
                pub = job.get("pub_date")
                if pub:
                    try:
                        posted = datetime.fromisoformat(pub.replace("Z","+00:00"))
                    except: pass
                missions.append(RawMission(
                    title=title, company=company, description=desc[:3000],
                    budget_raw="", budget_min=None, budget_max=None,
                    source="workingnomads", source_url=url,
                    tags=tags[:10], remote=True, posted_at=posted))
            except Exception as e:
                logger.debug(f"Skip: {e}")
        return missions
