"""
SNB Mission Hunter — Supabase database layer.
"""

import logging
from typing import Optional, List
from supabase import create_client, Client

logger = logging.getLogger("snb.db")


class Database:
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    # ── Missions ──────────────────────────────────────────────

    def mission_exists(self, dedup_key: str) -> bool:
        result = (
            self.client.table("missions")
            .select("id")
            .eq("dedup_key", dedup_key)
            .execute()
        )
        return len(result.data) > 0

    def insert_mission(self, data: dict) -> Optional[dict]:
        try:
            result = self.client.table("missions").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            if "duplicate key" in str(e).lower() or "23505" in str(e):
                logger.debug(f"Mission déjà existante: {data.get('title', '?')}")
                return None
            logger.error(f"Erreur insertion mission: {e}")
            raise

    def get_recent_missions(self, limit: int = 50) -> List[dict]:
        result = (
            self.client.table("missions")
            .select("*")
            .order("found_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    def update_mission(self, mission_id: str, updates: dict) -> Optional[dict]:
        result = (
            self.client.table("missions")
            .update(updates)
            .eq("id", mission_id)
            .execute()
        )
        return result.data[0] if result.data else None

    # ── Proposals ─────────────────────────────────────────────

    def insert_proposal(self, data: dict) -> Optional[dict]:
        try:
            result = self.client.table("proposals").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Erreur insertion proposal: {e}")
            raise

    # ── Scan Logs ─────────────────────────────────────────────

    def log_scan_start(self, source: str) -> str:
        result = (
            self.client.table("scan_logs")
            .insert({"source": source, "status": "running"})
            .execute()
        )
        return result.data[0]["id"]

    def log_scan_end(
        self,
        log_id: str,
        status: str,
        missions_found: int = 0,
        missions_new: int = 0,
        error_message: str = "",
        duration_ms: int = 0,
    ):
        self.client.table("scan_logs").update(
            {
                "status": status,
                "missions_found": missions_found,
                "missions_new": missions_new,
                "error_message": error_message or None,
                "duration_ms": duration_ms,
                "finished_at": "now()",
            }
        ).eq("id", log_id).execute()

    # ── Stats ─────────────────────────────────────────────────

    def get_today_count(self) -> int:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        result = (
            self.client.table("missions")
            .select("id", count="exact")
            .gte("found_at", f"{today}T00:00:00Z")
            .execute()
        )
        return result.count or 0

    def get_sources_status(self) -> dict:
        """Dernier scan par source."""
        result = (
            self.client.rpc("get_latest_scans", {})
            .execute()
        )
        return result.data if result.data else {}
