"""
SNB Mission Hunter — Base scraper interface.

Tous les scrapers héritent de cette classe.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List
from models import RawMission

logger = logging.getLogger("snb.scrapers")

# Headers réalistes pour éviter les bans
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}


class BaseScraper(ABC):
    name: str = "base"
    tier: int = 1  # 1 = fast, 2 = slow

    @abstractmethod
    async def fetch(self) -> List[RawMission]:
        """Retourne les missions brutes. Implémenté par chaque scraper."""
        raise NotImplementedError

    async def safe_fetch(self) -> List[RawMission]:
        """Fetch avec retry + error handling. Ne crashe jamais l'agent."""
        retries = 3
        backoff = [5, 15, 30]

        for attempt in range(retries):
            try:
                missions = await self.fetch()
                logger.info(f"[{self.name}] {len(missions)} missions trouvées")
                return missions
            except Exception as e:
                wait = backoff[min(attempt, len(backoff) - 1)]
                logger.warning(
                    f"[{self.name}] Tentative {attempt + 1}/{retries} échouée: {e} — retry dans {wait}s"
                )
                if attempt < retries - 1:
                    await asyncio.sleep(wait)

        logger.error(f"[{self.name}] Échec après {retries} tentatives")
        return []
