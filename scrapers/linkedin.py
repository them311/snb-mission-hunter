"""LinkedIn Jobs — Public scrape (no auth). Tier 1.
Searches for freelance/CDD/consultant missions in France."""
import logging
from typing import List
from html.parser import HTMLParser
import aiohttp
from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.linkedin")

QUERIES = [
    "consultant+web+IA+freelance",
    "développeur+react+freelance",
    "consultant+digital+CDD",
    "chef+de+projet+web+freelance",
    "shopify+developer+remote",
    "automatisation+IA+consultant",
]

class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.jobs = []
        self._current = {}
        self._in_title = False
        self._in_company = False
        self._in_location = False
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'div' and 'base-search-card__info' in d.get('class',''):
            self._current = {}
        if tag == 'h3': self._in_title = True
        if tag == 'h4': self._in_company = True
        if tag == 'span' and 'job-search-card__location' in d.get('class',''):
            self._in_location = True
        if tag == 'a' and 'base-card__full-link' in d.get('class',''):
            self._current['url'] = d.get('href','')
    def handle_endtag(self, tag):
        if tag == 'h3': self._in_title = False
        if tag == 'h4': self._in_company = False
        if tag == 'span': self._in_location = False
    def handle_data(self, data):
        t = data.strip()
        if not t: return
        if self._in_title:
            self._current['title'] = t
        elif self._in_company:
            self._current['company'] = t
        elif self._in_location:
            self._current['location'] = t
            if self._current.get('title'):
                self.jobs.append(dict(self._current))

class LinkedInScraper(BaseScraper):
    name = "linkedin"
    tier = 1
    BASE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen_titles = set()
        headers = {**DEFAULT_HEADERS, "Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession() as session:
            for query in QUERIES[:4]:
                try:
                    url = f"{self.BASE}?keywords={query}&location=France&f_TPR=r604800&start=0"
                    async with session.get(url, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status != 200:
                            continue
                        html = await resp.text()
                    parser = TitleParser()
                    parser.feed(html)
                    for job in parser.jobs:
                        title = job.get('title','').strip()
                        if not title or title in seen_titles:
                            continue
                        seen_titles.add(title)
                        company = job.get('company','').strip()
                        location = job.get('location','').strip()
                        tags = [location] if location else []
                        missions.append(RawMission(
                            title=title, company=company,
                            description=f"{title} chez {company}. {location}.",
                            budget_raw="", budget_min=None, budget_max=None,
                            source="linkedin", source_url=job.get('url',''),
                            tags=tags[:10], remote='remote' in title.lower() or 'remote' in location.lower(),
                            posted_at=None))
                except Exception as e:
                    logger.debug(f"LinkedIn query error: {e}")
        return missions
