"""
SNB Mission Hunter — Remotive.com API scraper.
Source: https://remotive.com/api/remote-jobs (JSON API publique)
Tier 1 — scan toutes les 5 min.
"""

import logging
from typing import List
from datetime import datetime, timezone
import aiohttp

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.remotive")


class RemotiveScraper(BaseScraper):
    name = "remotive"
    tier = 1
    API_URL = "https://remotive.com/api/remote-jobs?limit=50"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept": "application/json", "Accept-Encoding": "gzip, deflate"}

        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"Remotive HTTP {resp.status}")
                data = await resp.json(content_type=None)

        jobs = data.get("jobs", [])

        for job in jobs[:50]:
            try:
                title = job.get("title", "").strip()
                company = job.get("company_name", "").strip()
                description = job.get("description", "").strip()
                tags = job.get("tags", []) or []
                category = job.get("category", "")

                if not title:
                    continue

                # Parse salary
                salary = job.get("salary", "")
                budget_raw = salary if salary else ""
                budget_min = None
                budget_max = None

                # Parse date
                posted_at = None
                pub_date = job.get("publication_date")
                if pub_date:
                    try:
                        posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                source_url = job.get("url", "")

                all_tags = [t.strip() for t in tags if isinstance(t, str)]
                if category and category not in all_tags:
                    all_tags.append(category)

                missions.append(RawMission(
                    title=title,
                    company=company,
                    description=description[:3000],
                    budget_raw=budget_raw,
                    budget_min=budget_min,
                    budget_max=budget_max,
                    source="remotive",
                    source_url=source_url,
                    tags=all_tags[:10],
                    remote=True,
                    posted_at=posted_at,
                ))
            except Exception as e:
                logger.debug(f"Skip Remotive job: {e}")
                continue

        return missions
