"""Codeur.com — Missions freelance FR. Scraping HTML. Tier 1. Pages 1-3."""
import logging, re
from typing import List
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.codeur")

class CodeurScraper(BaseScraper):
    name = "codeur"
    tier = 1

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen = set()
        headers = {**DEFAULT_HEADERS, "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            for page in range(1, 4):
                try:
                    url = f"https://www.codeur.com/projects?page={page}"
                    async with session.get(url, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        if resp.status != 200: continue
                        html = await resp.text()
                    links = re.findall(r'href="(/projects/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
                    for href, raw in links:
                        title = re.sub(r'<[^>]+>', '', raw).strip()
                        title = re.sub(r'\s+', ' ', title)
                        if not title or len(title) < 10 or href in seen: continue
                        seen.add(href)
                        budget = ""
                        bm = re.search(r'(\d[\d\s,.]*\s*€)', html[max(0,html.find(href)-200):html.find(href)+500])
                        if bm: budget = bm.group(1).strip()
                        missions.append(RawMission(
                            title=title, company="", description=title,
                            budget_raw=budget, budget_min=None, budget_max=None,
                            source="codeur", source_url=f"https://www.codeur.com{href}",
                            tags=["freelance","france"], remote=True, posted_at=None))
                except Exception as e:
                    logger.debug(f"Codeur page {page} error: {e}")
        return missions
