"""
SNB Mission Hunter — Upwork RSS scraper.
Utilise les feeds RSS publics d'Upwork par catégorie.
Tier 1 — scan toutes les 5 min.
"""

import logging
import re
from typing import List
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import aiohttp
import feedparser

from models import RawMission
from scrapers.base import BaseScraper, DEFAULT_HEADERS

logger = logging.getLogger("snb.scrapers.upwork")

# Feeds RSS Upwork — un par domaine de compétence S&B
UPWORK_FEEDS = [
    # Web Dev
    "https://www.upwork.com/ab/feed/jobs/rss?q=react+next.js&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=shopify+developer&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=frontend+developer&sort=recency",
    # IA / Automation
    "https://www.upwork.com/ab/feed/jobs/rss?q=ai+automation+chatbot&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=claude+anthropic+llm&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=python+automation&sort=recency",
    # Consulting / Strategy
    "https://www.upwork.com/ab/feed/jobs/rss?q=digital+strategy+consultant&sort=recency",
    # Scraping / Data
    "https://www.upwork.com/ab/feed/jobs/rss?q=web+scraping+python&sort=recency",
]


def _parse_budget(text: str):
    """Extrait budget min/max du titre ou description Upwork."""
    # Pattern: "$X - $Y"
    match = re.search(r'\$([0-9,]+)\s*-\s*\$([0-9,]+)', text)
    if match:
        lo = float(match.group(1).replace(",", ""))
        hi = float(match.group(2).replace(",", ""))
        return f"${lo:.0f} - ${hi:.0f}", lo, hi

    # Pattern: "Budget: $X"
    match = re.search(r'(?:Budget|budget)[:\s]*\$([0-9,]+)', text)
    if match:
        val = float(match.group(1).replace(",", ""))
        return f"${val:.0f}", val, val

    # Hourly: "$X/hr"
    match = re.search(r'\$([0-9,.]+)\s*/\s*hr', text)
    if match:
        rate = float(match.group(1).replace(",", ""))
        daily = rate * 8
        return f"${rate:.0f}/hr (~${daily:.0f}/day)", daily, daily

    return "", None, None


def _extract_tags_from_html(html_content: str) -> List[str]:
    """Extrait les skills depuis le HTML de la description Upwork."""
    tags = []
    # Upwork met souvent les skills dans des <b> ou en texte
    skill_patterns = re.findall(r'<b>Skills</b>:\s*(.+?)(?:<br|</)', html_content, re.IGNORECASE)
    if skill_patterns:
        raw = re.sub(r'<[^>]+>', '', skill_patterns[0])
        tags = [t.strip() for t in raw.split(",") if t.strip()]
    return tags[:10]


def _clean_html(html: str) -> str:
    """Retire les tags HTML."""
    return re.sub(r'<[^>]+>', ' ', html).strip()


class UpworkRSSScraper(BaseScraper):
    name = "upwork"
    tier = 1

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen_urls = set()

        async with aiohttp.ClientSession() as session:
            for feed_url in UPWORK_FEEDS:
                try:
                    async with session.get(
                        feed_url,
                        headers=DEFAULT_HEADERS,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status != 200:
                            logger.debug(f"Upwork feed {resp.status}: {feed_url[:60]}")
                            continue
                        content = await resp.text()
                except Exception as e:
                    logger.debug(f"Upwork feed error: {e}")
                    continue

                feed = feedparser.parse(content)

                for entry in feed.entries[:15]:  # 15 par feed max
                    try:
                        link = entry.get("link", "")
                        if link in seen_urls:
                            continue
                        seen_urls.add(link)

                        title = entry.get("title", "").strip()
                        if not title:
                            continue

                        summary_html = entry.get("summary", "")
                        description = _clean_html(summary_html)
                        tags = _extract_tags_from_html(summary_html)

                        # Budget
                        full_text = f"{title} {description}"
                        budget_raw, budget_min, budget_max = _parse_budget(full_text)

                        # Date
                        posted_at = None
                        if entry.get("published"):
                            try:
                                posted_at = parsedate_to_datetime(entry.published)
                            except Exception:
                                pass

                        missions.append(RawMission(
                            title=title,
                            company="Upwork Client",
                            description=description[:3000],
                            budget_raw=budget_raw,
                            budget_min=budget_min,
                            budget_max=budget_max,
                            source="upwork",
                            source_url=link,
                            tags=tags,
                            remote=True,
                            posted_at=posted_at,
                        ))
                    except Exception as e:
                        logger.debug(f"Skip Upwork entry: {e}")
                        continue

        return missions
