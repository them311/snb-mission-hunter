"""
SNB Mission Hunter — FastAPI endpoints.
/health : état de l'agent
/stats  : statistiques
/missions : dernières missions (pour le dashboard)
"""

import time
import logging
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("snb.api")

app = FastAPI(title="SNB Mission Hunter", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://snb-consulting-platform.netlify.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Stockage léger en mémoire — enrichi par main.py au runtime
_state = {
    "started_at": time.time(),
    "last_scan": None,
    "scans_total": 0,
    "missions_today": 0,
    "proposals_today": 0,
    "sources_status": {},
    "db": None,
}


def set_db(db):
    _state["db"] = db


def record_scan(source: str, count: int):
    _state["last_scan"] = datetime.now(timezone.utc).isoformat()
    _state["scans_total"] += 1
    _state["sources_status"][source] = {
        "last_scan": _state["last_scan"],
        "missions_found": count,
        "status": "ok",
    }


def record_scan_error(source: str, error: str):
    _state["sources_status"][source] = {
        "last_scan": datetime.now(timezone.utc).isoformat(),
        "status": "error",
        "error": error,
    }


def increment_missions():
    _state["missions_today"] += 1


def increment_proposals():
    _state["proposals_today"] += 1


@app.get("/health")
async def health():
    uptime = int(time.time() - _state["started_at"])
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        "status": "running",
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "last_scan": _state["last_scan"],
        "scans_total": _state["scans_total"],
        "missions_today": _state["missions_today"],
        "proposals_today": _state["proposals_today"],
        "sources": _state["sources_status"],
    }


@app.get("/stats")
async def stats():
    db = _state.get("db")
    if not db:
        return {"error": "Database not initialized"}

    try:
        today_count = db.get_today_count()
    except Exception:
        today_count = _state["missions_today"]

    return {
        "missions_today": today_count,
        "proposals_today": _state["proposals_today"],
        "scans_total": _state["scans_total"],
        "sources_active": len(_state["sources_status"]),
    }


@app.get("/missions")
async def get_missions(limit: int = 50):
    db = _state.get("db")
    if not db:
        return {"error": "Database not initialized"}

    try:
        missions = db.get_recent_missions(limit=min(limit, 100))
        return {"missions": missions, "count": len(missions)}
    except Exception as e:
        logger.error(f"API /missions error: {e}")
        return {"error": str(e), "missions": []}
