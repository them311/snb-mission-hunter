"""
SNB Mission Hunter — Jobicy.com API scraper (v2 — fix encodage brotli).
Source: https://jobicy.com/api/v2/remote-jobs (JSON API publique)
Tier 1 — scan toutes les 5 min.
"""

import logging
from typing import List
from datetime import datetime, timezone
import aiohttp

from models import RawMission
from scrapers.base import BaseScraper

logger = logging.getLogger("snb.scrapers.jobicy")

# Headers sans brotli (cause du crash v1)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SNBBot/1.0; +https://snb-consulting.fr)",
    "Accept": "application/json",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    # PAS de Accept-Encoding brotli — Railway n'a pas brotlicffi
}

API_URL = "https://jobicy.com/api/v2/remote-jobs?count=50&tag=developer&tag=design&tag=marketing"


class JobicyScraper(BaseScraper):
    name = "jobicy"
    tier = 1

    async def fetch(self) -> List[RawMission]:
        missions = []

        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    API_URL,
                    headers=HEADERS,
                    timeout=aiohttp.ClientTimeout(total=25),
                    allow_redirects=True,
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Jobicy HTTP {resp.status} — skip")
                        return []

                    # Lire en bytes puis décoder manuellement (évite le décodage auto brotli)
                    raw = await resp.read()
                    text = raw.decode("utf-8", errors="replace")
                    import json
                    data = json.loads(text)

            jobs = data.get("jobs", [])
            logger.info(f"Jobicy: {len(jobs)} jobs récupérés")

            for job in jobs:
                try:
                    title = (job.get("jobTitle") or "").strip()
                    if not title:
                        continue

                    company = (job.get("companyName") or "").strip()
                    description = (job.get("jobDescription") or "").strip()
                    url = (job.get("url") or f"https://jobicy.com/jobs/{job.get('id', '')}").strip()
                    tags = job.get("jobIndustry", []) or []
                    if isinstance(tags, str):
                        tags = [tags]

                    # Budget depuis salaire annuel
                    salary_min = job.get("annualSalaryMin")
                    salary_max = job.get("annualSalaryMax")
                    budget_raw = ""
                    budget_min_val = None
                    budget_max_val = None
                    if salary_min and salary_max:
                        budget_raw = f"${salary_min:,} - ${salary_max:,}/year"
                        # Salaire annuel → TJM approximatif (÷ 220 jours ouvrés)
                        budget_min_val = round(float(salary_min) / 220, 0)
                        budget_max_val = round(float(salary_max) / 220, 0)

                    # Date de publication
                    posted_at = None
                    pub_date = job.get("pubDate")
                    if pub_date:
                        try:
                            from email.utils import parsedate_to_datetime
                            posted_at = parsedate_to_datetime(pub_date).replace(tzinfo=timezone.utc)
                        except Exception:
                            pass

                    missions.append(RawMission(
                        title=title,
                        company=company,
                        description=description[:800],
                        budget_raw=budget_raw,
                        budget_min=budget_min_val,
                        budget_max=budget_max_val,
                        source="jobicy",
                        source_url=url,
                        tags=tags,
                        remote=True,  # Jobicy = 100% remote
                        posted_at=posted_at,
                    ))

                except Exception as e:
                    logger.debug(f"Jobicy job parse error: {e}")
                    continue

        except Exception as e:
            logger.error(f"Jobicy fetch error: {e}")
            return []

        logger.info(f"Jobicy: {len(missions)} missions extraites")
        return missions
