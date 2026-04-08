"""
SNB Mission Hunter — Malt.fr scraper (listings publics).

⚠️  RÈGLE ABSOLUE : scraping des annonces publiques UNIQUEMENT.
    Soumission de devis = TOUJOURS manuelle par Baptiste.
    Jamais d'auto-apply sur Malt (CGU + qualité).

Source: https://www.malt.fr/search (HTML public)
Tier 2 — scan toutes les 30 min.
"""

import logging
import re
from typing import List
import aiohttp
from bs4 import BeautifulSoup

from models import RawMission
from scrapers.base import BaseScraper

logger = logging.getLogger("snb.scrapers.malt")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
}

# Requêtes ciblées profil Baptiste
SEARCH_QUERIES = [
    ("consultant-ia", "consultant+IA+intelligence+artificielle"),
    ("agent-ia", "agent+IA+LLM+automatisation"),
    ("shopify-ia", "Shopify+developer+IA"),
    ("react-nextjs", "React+Next.js+freelance"),
    ("consultant-web", "consultant+web+freelance"),
]

BASE_URL = "https://www.malt.fr/search?q={query}&remoteAllowed=true"


def _extract_budget(text: str):
    """Extrait le TJM depuis le texte d'une annonce Malt."""
    # Pattern: "XXX €/jour" ou "XXX-YYY €/j"
    m = re.search(r'(\d[\d\s]*)\s*[€$]\s*/\s*(?:jour|j\b|day)', text, re.IGNORECASE)
    if m:
        val = float(m.group(1).replace(" ", ""))
        return f"{val:.0f}€/jour", val, val

    m = re.search(r'(\d[\d\s]*)\s*-\s*(\d[\d\s]*)\s*[€$]', text, re.IGNORECASE)
    if m:
        lo = float(m.group(1).replace(" ", ""))
        hi = float(m.group(2).replace(" ", ""))
        return f"{lo:.0f}-{hi:.0f}€", lo, hi

    return "", None, None


class MaltScraper(BaseScraper):
    name = "malt"
    tier = 2

    async def fetch(self) -> List[RawMission]:
        missions = []
        seen_titles = set()

        async with aiohttp.ClientSession() as session:
            for query_name, query_str in SEARCH_QUERIES:
                url = BASE_URL.format(query=query_str)
                try:
                    async with session.get(
                        url,
                        headers=HEADERS,
                        timeout=aiohttp.ClientTimeout(total=20),
                        allow_redirects=True,
                    ) as resp:
                        if resp.status != 200:
                            logger.debug(f"Malt [{query_name}] HTTP {resp.status}")
                            continue
                        html = await resp.text(encoding="utf-8", errors="replace")

                except Exception as e:
                    logger.debug(f"Malt [{query_name}] connexion: {e}")
                    continue

                try:
                    soup = BeautifulSoup(html, "html.parser")

                    # Malt liste les projets dans des cards — plusieurs sélecteurs possibles
                    # selon la version du HTML
                    cards = (
                        soup.select("article[data-v-app]")
                        or soup.select(".project-card")
                        or soup.select("[class*='project']")
                        or soup.select("article")
                    )

                    if not cards:
                        # Fallback: extraire les titres <h2> et <h3>
                        titles = soup.find_all(["h2", "h3"], string=True)
                        for h in titles[:15]:
                            t = h.get_text(strip=True)
                            if len(t) < 15 or t in seen_titles:
                                continue
                            seen_titles.add(t)
                            # Chercher le budget dans le parent
                            parent_text = h.parent.get_text(" ", strip=True) if h.parent else ""
                            budget_raw, bmin, bmax = _extract_budget(parent_text)
                            # Lien
                            link_tag = h.find_parent("a") or h.find("a")
                            href = link_tag["href"] if link_tag and link_tag.get("href") else ""
                            if href and not href.startswith("http"):
                                href = "https://www.malt.fr" + href
                            missions.append(RawMission(
                                title=t,
                                company="",
                                description=parent_text[:500],
                                budget_raw=budget_raw,
                                budget_min=bmin,
                                budget_max=bmax,
                                source="malt",
                                source_url=href or url,
                                tags=["freelance", "france", query_name],
                                remote=True,
                                posted_at=None,
                            ))
                        continue

                    for card in cards[:10]:
                        try:
                            text = card.get_text(" ", strip=True)
                            # Titre : premier élément h2/h3 dans la card
                            h_tag = card.find(["h2", "h3", "h4"])
                            title = h_tag.get_text(strip=True) if h_tag else text[:80]

                            if not title or len(title) < 10 or title in seen_titles:
                                continue
                            seen_titles.add(title)

                            budget_raw, bmin, bmax = _extract_budget(text)

                            link_tag = card.find("a", href=True)
                            href = link_tag["href"] if link_tag else ""
                            if href and not href.startswith("http"):
                                href = "https://www.malt.fr" + href

                            missions.append(RawMission(
                                title=title,
                                company="",
                                description=text[:600],
                                budget_raw=budget_raw,
                                budget_min=bmin,
                                budget_max=bmax,
                                source="malt",
                                source_url=href or url,
                                tags=["freelance", "france", query_name],
                                remote=True,
                                posted_at=None,
                            ))
                        except Exception:
                            continue

                except Exception as e:
                    logger.debug(f"Malt [{query_name}] parse: {e}")

        logger.info(f"Malt: {len(missions)} missions extraites (soumission manuelle requise)")
        return missions
