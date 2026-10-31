import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal
from app.services.billing_service import process_due_subscriptions

logger = logging.getLogger(__name__)


def scheduled_billing_run() -> None:
    db = SessionLocal()
    try:
        process_due_subscriptions(db, date.today())
    except Exception:
        db.rollback()
        logger.exception("Scheduled billing run failed")
    finally:
        db.close()


def start_scheduler(interval_hours: int = 1) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        scheduled_billing_run,
        trigger="interval",
        hours=interval_hours,
        id="brightloop-recurring-billing",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("Scheduled recurring billing every %s hour(s)", interval_hours)
    return scheduler
