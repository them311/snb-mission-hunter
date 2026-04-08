"""
SNB Mission Hunter â FastAPI endpoints.
Health lit directement depuis Supabase (partagÃ© entre processus).
"""

import time
import logging
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("snb.api")

app = FastAPI(title="SNB Mission Hunter", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_started_at = time.time()
_db = None
_proposer_active = False
_score_threshold = None

def set_proposer_active(active: bool):
    global _proposer_active
    _proposer_active = active

def set_score_threshold(threshold: int):
    global _score_threshold
    _score_threshold = threshold

def set_db(db):
    global _db
    _db = db

@app.on_event("startup")
async def startup():
    """Init DB connection for the uvicorn process."""
    global _db
    if _db is None:
        try:
            from config import Config
            from db import Database
            config = Config.from_env()
            _db = Database(config.supabase_url, config.supabase_service_key)
            logger.info("â API DB initialized")
        except Exception as e:
            logger.warning(f"API DB init failed: {e}")

# Keep these for backward compat with main.py imports
def record_scan(source, count): pass
def record_scan_error(source, error): pass
def increment_missions(): pass
def increment_proposals(): pass


@app.get("/")
async def root():
    return {"service": "SNB Mission Hunter", "status": "running"}

@app.get("/health")
async def health():
    uptime = int(time.time() - _started_at)
    h, r = divmod(uptime, 3600)
    m, s = divmod(r, 60)

    result = {
        "status": "running",
        "uptime": f"{h}h {m}m {s}s",
        "last_scan": None,
        "scans_total": 0,
        "missions_today": 0,
        "proposals_today": 0,
        "proposer_active": _proposer_active,
        "score_threshold": _score_threshold,
        "sources": {},
    }

    if not _db:
        return result

    try:
        # Read real data from Supabase
        today = datetime.now(timezone.utc).date().isoformat()

        # Scan logs from today
        logs = _db.client.table("scan_logs") \
            .select("source,status,started_at,missions_found,missions_new") \
            .gte("started_at", today) \
            .order("started_at", desc=True) \
            .limit(50) \
            .execute()

        scan_data = logs.data or []
        result["scans_total"] = len(scan_data)
        if scan_data:
            result["last_scan"] = scan_data[0].get("started_at")

        # Sources status
        sources = {}
        for s in scan_data:
            src = s.get("source", "?")
            if src not in sources:
                sources[src] = {
                    "last_scan": s.get("started_at"),
                    "status": s.get("status", "ok"),
                    "missions_found": s.get("missions_found", 0),
                }
        result["sources"] = sources

        # Missions today
        missions_today = _db.client.table("missions") \
            .select("id", count="exact") \
            .gte("found_at", today) \
            .execute()
        result["missions_today"] = missions_today.count or 0

        # Proposals today
        proposals_today = _db.client.table("proposals") \
            .select("id", count="exact") \
            .gte("created_at", today) \
            .execute()
        result["proposals_today"] = proposals_today.count or 0

    except Exception as e:
        logger.debug(f"Health DB read error (non-critical): {e}")

    return result


@app.get("/stats")
async def stats():
    return await health()


@app.get("/missions")
async def get_missions(limit: int = 50):
    if not _db:
        return {"error": "DB not init", "missions": []}
    try:
        missions = _db.get_recent_missions(limit=min(limit, 100))
        return {"missions": missions, "count": len(missions)}
    except Exception as e:
        return {"error": str(e), "missions": []}


@app.get("/devis/{mission_id}")
async def generate_devis(mission_id: str):
    """GÃ©nÃ¨re un devis HTML tÃ©lÃ©chargeable pour une mission."""
    if not _db:
        return {"error": "DB not init"}
    try:
        mission = _db.client.table("missions").select("*").eq("id", mission_id).single().execute()
        m = mission.data
        if not m:
            return {"error": "Mission not found"}

        title = m.get("title", "Mission")
        company = m.get("company", "")
        budget = m.get("budget_raw", "")
        today = datetime.now().strftime("%d/%m/%Y")

        from fastapi.responses import HTMLResponse
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Devis {title}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Helvetica,sans-serif;color:#111;padding:40px;max-width:700px;margin:0 auto;font-size:14px;line-height:1.6}}
h1{{font-size:22px;margin-bottom:4px}}h2{{font-size:16px;border-bottom:1px solid #ddd;padding-bottom:4px;margin:20px 0 10px}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}td,th{{padding:8px 10px;border:1px solid #ddd;text-align:left}}th{{background:#f5f5f5}}
.total{{font-size:18px;font-weight:bold;text-align:right;margin:16px 0}}.footer{{margin-top:40px;font-size:11px;color:#888;text-align:center}}
@media print{{body{{padding:20px}}}}</style></head><body>
<div style="display:flex;justify-content:space-between;border-bottom:3px solid #111;padding-bottom:14px;margin-bottom:20px">
<div><h1>Baptiste Thevenot</h1><p style="color:#555;font-size:13px">Consultant Web & IA Â· Freelance</p>
<p style="font-size:12px;color:#888;margin-top:6px">10 chemin de Catala, 31100 Toulouse<br>bp.thevenot@gmail.com Â· 06 86 50 43 79<br>SIRET : 849 022 058</p></div>
<div style="text-align:right"><p style="font-size:18px;font-weight:bold">DEVIS</p><p style="font-size:12px;color:#888">{today}<br>Valable 30 jours</p></div></div>

<div style="background:#f5f7fa;border-radius:8px;padding:14px;margin-bottom:20px">
<p style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;font-weight:bold">Mission Freelance</p>
<p style="font-size:17px;font-weight:bold;margin-top:4px">{title}</p>
<p style="font-size:13px;color:#555">{company} Â· Remote Â· {budget}</p></div>

<h2>Tarification</h2>
<table><tr style="background:#f9f9f9"><td style="font-weight:bold">Taux horaire</td><td style="text-align:center;font-weight:bold;font-size:15px">60 â¬ HT/h</td></tr>
<tr><td style="font-weight:bold">Taux journalier (TJM)</td><td style="text-align:center;font-weight:bold;font-size:15px">450 â¬ HT/jour</td></tr>
<tr style="background:#f0fff4"><td style="font-weight:bold">Forfait mensuel</td><td style="text-align:center;font-weight:bold;font-size:17px">9 000 â¬ HT/mois</td></tr></table>

<h2>Conditions</h2>
<p><strong>DisponibilitÃ© :</strong> ImmÃ©diate<br><strong>Mode :</strong> 100% tÃ©lÃ©travail<br><strong>Paiement :</strong> 30% commande Â· 70% livraison<br>
<strong>CompÃ©tences :</strong> React.js, Node.js, Shopify, Claude API, Python, Figma<br><strong>TVA :</strong> Non applicable â art. 293B du CGI</p>

<div style="margin-top:30px;border-top:1px solid #ddd;padding-top:14px;display:flex;justify-content:space-between">
<div><p style="font-size:12px;color:#888">Bon pour accord</p><div style="margin-top:20px;border-bottom:1px solid #ccc;width:160px"></div></div>
<div style="text-align:right;font-size:12px;color:#888">Baptiste Thevenot<br>Consultant Web & IA</div></div>

<p class="footer">Baptiste Thevenot Â· SIRET 849 022 058 Â· TVA non applicable art. 293B du CGI</p>
<script>window.print&&setTimeout(()=>{{/*window.print()*/}},500)</script>
</body></html>"""
        return HTMLResponse(content=html)
    except Exception as e:
        return {"error": str(e)}
