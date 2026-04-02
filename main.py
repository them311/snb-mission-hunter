"""
SNB Mission Hunter — Point d'entrée principal.

Orchestre les scrapers via APScheduler, score les missions,
génère des propositions pour les missions à fort score,
et notifie en temps réel via Telegram.
"""

import asyncio
import logging
import sys
import time
import signal
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import Config, PROFILES
from db import Database
from scorer import score_mission, classify_mission
from proposer import Proposer
from notifier import notify_telegram, send_email_digest
from api import app, set_db, record_scan, record_scan_error, increment_missions, increment_proposals

# Scrapers
from scrapers.remoteok import RemoteOKScraper
from scrapers.remotive import RemotiveScraper
from scrapers.jobicy import JobicyScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.guru import GuruScraper

# ── Logging ──────────────────────────────────────────────────

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger("snb.main")

# ── Scrapers registry ────────────────────────────────────────

SCRAPERS_TIER1 = [
    RemoteOKScraper(),
    RemotiveScraper(),
    JobicyScraper(),
    WeWorkRemotelyScraper(),
]

SCRAPERS_TIER2 = [
    GuruScraper(),
]

ALL_SCRAPERS = SCRAPERS_TIER1 + SCRAPERS_TIER2

# ── Globals ──────────────────────────────────────────────────

config: Config = None
db: Database = None
proposer: Proposer = None
scheduler: AsyncIOScheduler = None

# Digest buffer — missions à fort score depuis le dernier email
_digest_buffer = []


# ── Core pipeline ────────────────────────────────────────────

async def run_scraper(scraper):
    """Pipeline complet : scrape → dedupe → score → insert → propose → notify."""
    global _digest_buffer

    source_name = scraper.name
    start_time = time.time()
    log_id = None

    try:
        # Log scan start
        try:
            log_id = db.log_scan_start(source_name)
        except Exception as e:
            logger.debug(f"Scan log start failed (non-critical): {e}")

        # 1. Scrape
        raw_missions = await scraper.safe_fetch()
        missions_found = len(raw_missions)

        if not raw_missions:
            record_scan(source_name, 0)
            if log_id:
                duration_ms = int((time.time() - start_time) * 1000)
                db.log_scan_end(log_id, "success", 0, 0, duration_ms=duration_ms)
            return

        profile = PROFILES.get(config.active_profile, PROFILES["baptiste"])
        missions_new = 0

        for raw in raw_missions:
            # 2. Dedupe
            if db.mission_exists(raw.dedup_key):
                continue

            # 3. Score
            mission_score = score_mission(raw, profile)
            mission_type = classify_mission(raw)

            # 4. Insert en base
            db_data = raw.to_db_dict(score=mission_score, mission_type=mission_type)
            inserted = db.insert_mission(db_data)

            if not inserted:
                continue

            missions_new += 1
            increment_missions()
            mission_id = inserted["id"]

            logger.info(
                f"[{source_name}] ✅ Nouvelle mission (score {mission_score}): {raw.title[:60]}"
            )

            # 5. Si score >= seuil → générer proposition + notifier
            if mission_score >= config.score_threshold and proposer:
                try:
                    proposal = proposer.generate(raw)
                    if proposal:
                        proposal.mission_id = mission_id
                        proposal_data = proposal.to_db_dict()
                        proposal_inserted = db.insert_proposal(proposal_data)

                        if proposal_inserted:
                            # Mettre à jour la mission avec l'ID de la proposition
                            db.update_mission(mission_id, {
                                "status": "proposal_ready",
                                "proposal_id": proposal_inserted["id"],
                            })
                            increment_proposals()

                            # Notifier Telegram
                            await notify_telegram(inserted, proposal.text, config)

                            # Ajouter au buffer digest
                            _digest_buffer.append(inserted)

                            logger.info(
                                f"[{source_name}] 📝 Proposition générée + notifiée: {raw.title[:50]}"
                            )
                except Exception as e:
                    logger.error(f"Proposal/notify error for {raw.title[:40]}: {e}")

        # Log scan end
        record_scan(source_name, missions_found)
        if log_id:
            duration_ms = int((time.time() - start_time) * 1000)
            db.log_scan_end(
                log_id, "success",
                missions_found=missions_found,
                missions_new=missions_new,
                duration_ms=duration_ms,
            )

        if missions_new > 0:
            logger.info(f"[{source_name}] Scan terminé: {missions_new} nouvelles / {missions_found} trouvées")

    except Exception as e:
        logger.error(f"[{source_name}] ERREUR SCRAPER: {e}", exc_info=True)
        record_scan_error(source_name, str(e))
        if log_id:
            duration_ms = int((time.time() - start_time) * 1000)
            db.log_scan_end(log_id, "error", error_message=str(e), duration_ms=duration_ms)


async def run_email_digest():
    """Envoie le digest email avec les missions bufferisées."""
    global _digest_buffer
    if _digest_buffer:
        try:
            send_email_digest(_digest_buffer, config)
            _digest_buffer = []
        except Exception as e:
            logger.error(f"Email digest error: {e}")


async def run_health_log():
    """Log périodique de l'état de l'agent."""
    now = datetime.now(timezone.utc).strftime("%H:%M")
    sources_ok = sum(
        1 for s in ALL_SCRAPERS
        if s.name in [sc.name for sc in ALL_SCRAPERS]
    )
    logger.info(
        f"💓 Health [{now}] — Sources: {sources_ok}/{len(ALL_SCRAPERS)} — "
        f"Scans total: {scheduler.get_jobs().__len__() if scheduler else 0} jobs actifs"
    )


# ── Scheduler setup ─────────────────────────────────────────

def setup_scheduler():
    global scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Tier 1 — toutes les 5 minutes (décalés pour éviter les pics)
    for i, scraper in enumerate(SCRAPERS_TIER1):
        # Décalage de 30s entre chaque scraper
        delay_seconds = i * 30
        scheduler.add_job(
            run_scraper,
            IntervalTrigger(seconds=config.scan_interval_fast),
            args=[scraper],
            id=f"scraper_{scraper.name}",
            name=f"Scrape {scraper.name}",
            next_run_time=datetime.now(timezone.utc),  # Lancer immédiatement
            misfire_grace_time=60,
            max_instances=1,
        )

    # Tier 2 — toutes les 30 minutes
    for scraper in SCRAPERS_TIER2:
        scheduler.add_job(
            run_scraper,
            IntervalTrigger(seconds=config.scan_interval_slow),
            args=[scraper],
            id=f"scraper_{scraper.name}",
            name=f"Scrape {scraper.name}",
            next_run_time=datetime.now(timezone.utc),
            misfire_grace_time=120,
            max_instances=1,
        )

    # Email digest — toutes les 2 heures
    scheduler.add_job(
        run_email_digest,
        IntervalTrigger(hours=2),
        id="email_digest",
        name="Email Digest",
        misfire_grace_time=300,
    )

    # Health log — toutes les heures
    scheduler.add_job(
        run_health_log,
        IntervalTrigger(hours=1),
        id="health_log",
        name="Health Log",
    )

    return scheduler


# ── Main ─────────────────────────────────────────────────────

async def main():
    global config, db, proposer

    setup_logging()
    logger.info("=" * 60)
    logger.info("🚀 SNB Mission Hunter — Démarrage")
    logger.info("=" * 60)

    # 1. Charger config
    config = Config.from_env()
    errors = config.validate()
    if errors:
        logger.error(f"❌ Variables d'environnement manquantes: {', '.join(errors)}")
        logger.error("Configurez les variables dans Railway ou .env")
        sys.exit(1)

    logger.info(f"✅ Config chargée — Profil actif: {config.active_profile}")
    logger.info(f"   Score threshold: {config.score_threshold}")
    logger.info(f"   Tier 1 interval: {config.scan_interval_fast}s")
    logger.info(f"   Tier 2 interval: {config.scan_interval_slow}s")

    # 2. Init Supabase
    db = Database(config.supabase_url, config.supabase_service_key)
    set_db(db)
    logger.info("✅ Supabase connecté")

    # 3. Init Proposer
    if config.anthropic_api_key:
        proposer = Proposer(config.anthropic_api_key)
        logger.info("✅ Proposer Claude API initialisé")
    else:
        proposer = None
        logger.warning("⚠️ Proposer désactivé — ANTHROPIC_API_KEY manquante")

    # 4. Scheduler
    sched = setup_scheduler()
    sched.start()
    logger.info(f"✅ Scheduler démarré — {len(sched.get_jobs())} jobs programmés:")
    for job in sched.get_jobs():
        logger.info(f"   📋 {job.name} (next: {job.next_run_time})")

    # 5. Telegram startup message
    try:
        import aiohttp
        if config.telegram_bot_token and config.telegram_chat_id:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": config.telegram_chat_id,
                        "text": (
                            "🟢 *SNB Mission Hunter démarré*\n\n"
                            f"Sources: {len(ALL_SCRAPERS)}\n"
                            f"Score min: {config.score_threshold}\n"
                            f"Profil: {config.active_profile}\n\n"
                            "📊 [Dashboard](https://snb-consulting-platform.netlify.app)"
                        ),
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                )
            logger.info("✅ Message Telegram envoyé")
    except Exception as e:
        logger.warning(f"Telegram startup message failed: {e}")

    logger.info("=" * 60)
    logger.info("🏃 Agent en cours d'exécution... (Ctrl+C pour arrêter)")
    logger.info("=" * 60)

    # Garder le process vivant
    stop_event = asyncio.Event()

    def handle_signal(*_):
        logger.info("🛑 Signal d'arrêt reçu — shutdown...")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_event_loop().add_signal_handler(sig, handle_signal)

    await stop_event.wait()

    # Cleanup
    sched.shutdown(wait=False)
    logger.info("🛑 SNB Mission Hunter arrêté proprement.")


if __name__ == "__main__":
    asyncio.run(main())
