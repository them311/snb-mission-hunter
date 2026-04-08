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
                        full_text = re.sub(r'<[^>]+>', '', raw).strip()
                        full_text = re.sub(r'\s+', ' ', full_text)
                        if not full_text or len(full_text) < 10 or href in seen: continue
                        seen.add(href)
                        # Extract clean title: first sentence before stats
                        # Pattern: "Title Il y a X jours En cours 500€..."
                        title_match = re.match(r'^(.+?)(?:\s+Il y a|\s+\d+\s+(?:Offre|Vue))', full_text)
                        title = title_match.group(1).strip() if title_match else full_text[:120]
                        # Extract budget
                        budget = ""
                        bm = re.search(r'(\d[\d\s,.]*\s*€(?:\s*à\s*\d[\d\s,.]*\s*€)?)', full_text)
                        if bm: budget = bm.group(1).strip()
                        # Clean description: remove freelancer names at end
                        desc = re.sub(r'(?:\s+[A-Z][a-zà-ü]+\s+[A-Z][a-zà-ü]+){3,}\s*$', '', full_text).strip()
                        missions.append(RawMission(
                            title=title, company="", description=desc[:2000],
                            budget_raw=budget, budget_min=None, budget_max=None,
                            source="codeur", source_url=f"https://www.codeur.com{href}",
                            tags=["freelance","france"], remote=True, posted_at=None))
                except Exception as e:
                    logger.debug(f"Codeur page {page} error: {e}")
        return missions
