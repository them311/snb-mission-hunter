"""
SNB Mission Hunter — RemoteOK scraper.
Source: https://remoteok.com/api (JSON API publique)
Tier 1 — scan toutes les 5 min.
"""

import logging
from typing import List
from datetime import datetime, timezone
import aiohttp

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.remoteok")


class RemoteOKScraper(BaseScraper):
    name = "remoteok"
    tier = 1
    API_URL = "https://remoteok.com/api"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"RemoteOK HTTP {resp.status}")
                data = await resp.json(content_type=None)

        # Le premier élément est un objet "legal" — on le skip
        jobs = data[1:] if isinstance(data, list) and len(data) > 1 else []

        for job in jobs[:50]:  # Limiter pour ne pas surcharger
            try:
                title = job.get("position", "").strip()
                company = job.get("company", "").strip()
                description = job.get("description", "").strip()
                tags = job.get("tags", []) or []

                if not title:
                    continue

                # Parse budget si présent
                salary_min = job.get("salary_min")
                salary_max = job.get("salary_max")
                budget_raw = ""
                budget_min_val = None
                budget_max_val = None

                if salary_min and salary_max:
                    budget_raw = f"${salary_min:,} - ${salary_max:,}/year"
                    # Convertir salaire annuel → TJM approximatif (÷ 220 jours)
                    budget_min_val = round(salary_min / 220, 0)
                    budget_max_val = round(salary_max / 220, 0)
                elif salary_min:
                    budget_raw = f"${salary_min:,}+/year"
                    budget_min_val = round(salary_min / 220, 0)

                # Parse date
                posted_at = None
                epoch = job.get("epoch")
                if epoch:
                    try:
                        posted_at = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
                    except (ValueError, TypeError):
                        pass

                source_url = job.get("url", f"https://remoteok.com/jobs/{job.get('id', '')}")

                missions.append(RawMission(
                    title=title,
                    company=company,
                    description=description[:3000],
                    budget_raw=budget_raw,
                    budget_min=budget_min_val,
                    budget_max=budget_max_val,
                    source="remoteok",
                    source_url=source_url,
                    tags=[t.strip() for t in tags if isinstance(t, str)],
                    remote=True,  # RemoteOK = tout remote par définition
                    posted_at=posted_at,
                ))
            except Exception as e:
                logger.debug(f"Skip job RemoteOK: {e}")
                continue

        return missions
