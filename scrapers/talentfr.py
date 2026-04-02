"""Talent.com FR — Missions freelance françaises. Tier 1."""
import logging, re
from typing import List
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.talentfr")

QUERIES = [
    "développeur+web+freelance",
    "consultant+IA+freelance",
    "développeur+react+freelance",
    "chef+de+projet+digital+CDD",
    "consultant+shopify+freelance",
]

class TalentFRScraper(BaseScraper):
    name = "talentfr"
    tier = 1
    BASE = "https://fr.talent.com/jobs"

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen = set()
        headers = {**DEFAULT_HEADERS, "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            for q in QUERIES[:3]:
                try:
                    url = f"{self.BASE}?q={q}&l=France"
                    async with session.get(url, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status != 200: continue
                        html = await resp.text()
                    # Parse job titles and links
                    titles = re.findall(r'class="[^"]*card__job-title[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', html)
                    if not titles:
                        titles = [(m.group(1), m.group(2)) for m in re.finditer(r'<a[^>]*href="(/job/[^"]*)"[^>]*>\s*([^<]{10,80})', html)]
                    companies = re.findall(r'class="[^"]*card__job-empname[^"]*"[^>]*>([^<]+)<', html)
                    for i, (href, title) in enumerate(titles[:15]):
                        t = title.strip()
                        if not t or t in seen: continue
                        seen.add(t)
                        company = companies[i].strip() if i < len(companies) else ""
                        link = f"https://fr.talent.com{href}" if href.startswith("/") else href
                        missions.append(RawMission(
                            title=t, company=company, description=t,
                            budget_raw="", budget_min=None, budget_max=None,
                            source="talentfr", source_url=link,
                            tags=["france","freelance"], remote="télétravail" in t.lower() or "remote" in t.lower(),
                            posted_at=None))
                except Exception as e:
                    logger.debug(f"TalentFR query error: {e}")
        return missions
