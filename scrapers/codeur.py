"""Codeur.com — Missions freelance FR. Scraping HTML. Tier 1."""
import logging, re
from typing import List
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.codeur")

class CodeurScraper(BaseScraper):
    name = "codeur"
    tier = 1
    URL = "https://www.codeur.com/projects?page=1"

    async def fetch(self) -> List[RawMission]:
        missions = []
        headers = {**DEFAULT_HEADERS, "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            async with session.get(self.URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    raise Exception(f"Codeur HTTP {resp.status}")
                html = await resp.text()
        # Parse projects from HTML
        links = re.findall(r'href="(/projects/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        seen = set()
        for href, raw_title in links:
            title = re.sub(r'<[^>]+>', '', raw_title).strip()
            title = re.sub(r'\s+', ' ', title)
            if not title or len(title) < 10 or href in seen:
                continue
            seen.add(href)
            # Extract budget if present near the link
            budget = ""
            budget_match = re.search(re.escape(href) + r'.*?(\d[\d\s]*€)', html[:html.find(href)+2000] if href in html else '', re.DOTALL)
            if budget_match:
                budget = budget_match.group(1).strip()
            missions.append(RawMission(
                title=title, company="", description=title,
                budget_raw=budget, budget_min=None, budget_max=None,
                source="codeur", source_url=f"https://www.codeur.com{href}",
                tags=["freelance", "france"], remote=True, posted_at=None))
        return missions
