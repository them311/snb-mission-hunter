"""
SNB Mission Hunter — Data models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import hashlib
import json


@dataclass
class RawMission:
    """Mission brute extraite par un scraper."""
    title: str
    company: str
    description: str
    budget_raw: str
    source: str
    source_url: str
    tags: List[str] = field(default_factory=list)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    remote: bool = True
    posted_at: Optional[datetime] = None

    @property
    def dedup_key(self) -> str:
        raw = f"{self.source}:{self.title}:{self.company}".lower().strip()
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def to_db_dict(self, score: int = 0, mission_type: str = "other") -> dict:
        return {
            "dedup_key": self.dedup_key,
            "title": self.title,
            "company": self.company,
            "description": self.description[:5000] if self.description else "",
            "budget_raw": self.budget_raw,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "type": mission_type,
            "source": self.source,
            "source_url": self.source_url,
            "tags": self.tags,
            "remote": self.remote,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "score": score,
            "status": "new",
        }


@dataclass
class Proposal:
    """Proposition générée."""
    mission_id: str
    text: str
    language: str = "fr"
    template_used: str = ""
    status: str = "draft"

    def to_db_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "text": self.text,
            "language": self.language,
            "template_used": self.template_used,
            "status": self.status,
        }
