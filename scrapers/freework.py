"""Free-Work.com — Missions freelance tech FR. Tier 1."""
import logging, re, json
from typing import List
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.freework")

class FreeWorkScraper(BaseScraper):
    name = "freework"
    tier = 1
    URL = "https://www.free-work.com/fr/tech-it/jobs?contracts=freelance&page={page}"

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen = set()
        headers = {**DEFAULT_HEADERS}
        async with aiohttp.ClientSession() as session:
            for page in range(1, 3):
                try:
                    url = self.URL.format(page=page)
                    async with session.get(url, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        if resp.status != 200: continue
                        html = await resp.text()
                    # Try Next.js __NEXT_DATA__
                    match = re.search(r'__NEXT_DATA__.*?>(.*?)</script>', html, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            jobs = data.get("props",{}).get("pageProps",{}).get("jobs",{}).get("data",[])
                            for j in jobs:
                                t = j.get("title","").strip()
                                if not t or t in seen: continue
                                seen.add(t)
                                company = j.get("company",{}).get("name","") if isinstance(j.get("company"),dict) else ""
                                slug = j.get("slug","")
                                link = f"https://www.free-work.com/fr/tech-it/jobs/{slug}" if slug else ""
                                tjm = j.get("dailyRate","")
                                loc = j.get("location",{}).get("city","") if isinstance(j.get("location"),dict) else ""
                                missions.append(RawMission(
                                    title=t, company=company, description=j.get("description",t)[:500],
                                    budget_raw=f"{tjm}€/jour" if tjm else "",
                                    budget_min=None, budget_max=None,
                                    source="freework", source_url=link,
                                    tags=["freelance","france"], remote="remote" in t.lower() or "télétravail" in (loc or "").lower(),
                                    posted_at=None))
                        except json.JSONDecodeError:
                            pass
                    # Fallback: parse HTML titles
                    if not missions:
                        titles = re.findall(r'<h2[^>]*>([^<]{10,80})</h2>', html)
                        for t in titles[:20]:
                            t = t.strip()
                            if t in seen: continue
                            seen.add(t)
                            missions.append(RawMission(
                                title=t, company="", description=t,
                                budget_raw="", budget_min=None, budget_max=None,
                                source="freework", source_url="https://www.free-work.com/fr/tech-it/jobs",
                                tags=["freelance","france"], remote=True, posted_at=None))
                except Exception as e:
                    logger.debug(f"FreeWork page {page} error: {e}")
        return missions
