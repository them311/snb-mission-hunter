"""
SNB Mission Hunter — Jobicy.com API scraper.
Source: https://jobicy.com/api/v2/remote-jobs (JSON API publique)
Tier 1 — scan toutes les 5 min.
"""

import logging
from typing import List
from datetime import datetime, timezone
import aiohttp

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.jobicy")


class JobicyScraper(BaseScraper):
    name = "jobicy"
    tier = 1
    API_URL = "https://jobicy.com/api/v2/remote-jobs?count=50"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept": "application/json", "Accept-Encoding": "gzip, deflate"}

        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"Jobicy HTTP {resp.status}")
                data = await resp.json(content_type=None)

        jobs = data.get("jobs", [])

        for job in jobs[:50]:
            try:
                title = job.get("jobTitle", "").strip()
                company = job.get("companyName", "").strip()
                description = job.get("jobDescription", "").strip()

                if not title:
                    continue

                # Parse salary
                salary_min = job.get("annualSalaryMin")
                salary_max = job.get("annualSalaryMax")
                budget_raw = ""
                budget_min_val = None
                budget_max_val = None

                if salary_min and salary_max:
                    budget_raw = f"${salary_min:,} - ${salary_max:,}/year"
                    budget_min_val = round(float(salary_min) / 220, 0)
                    budget_max_val = round(float(salary_max) / 220, 0)

                # Parse date
                posted_at = None
                pub_date = job.get("pubDate")
                if pub_date:
                    try:
                        posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                source_url = job.get("jobLink", job.get("url", ""))
                job_type = job.get("jobType", "")
                geo = job.get("jobGeo", "")
                tags = []
                if job_type:
                    tags.append(job_type)
                if geo:
                    tags.append(geo)

                missions.append(RawMission(
                    title=title,
                    company=company,
                    description=description[:3000],
                    budget_raw=budget_raw,
                    budget_min=budget_min_val,
                    budget_max=budget_max_val,
                    source="jobicy",
                    source_url=source_url,
                    tags=tags[:10],
                    remote=True,
                    posted_at=posted_at,
                ))
            except Exception as e:
                logger.debug(f"Skip Jobicy job: {e}")
                continue

        return missions
