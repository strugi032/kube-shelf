import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .inventory import collect_inventory
from .trivy import collect_vulnerabilities
from .registry import get_latest_tag, compare_tags
from .models import Container
from .db import SessionLocal
from .config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def refresh_all():
    logger.info("Starting full refresh...")
    try:
        # 1. Collect K8s inventory
        collect_inventory()
        
        # 2. Collect Vulnerabilities
        collect_vulnerabilities()
        
        # 3. Update Image Freshness
        await update_freshness()
        
        logger.info("Full refresh completed successfully")
    except Exception as e:
        logger.error(f"Error during refresh: {e}")

async def update_freshness():
    db = SessionLocal()
    try:
        containers = db.query(Container).all()
        for c in containers:
            if c.image_tag == "latest" or "@sha256" in c.image_full:
                c.freshness_status = "unknown"
                c.freshness_reason = "latest tag or digest used"
                continue
                
            latest = await get_latest_tag(c.image_repository)
            if latest:
                status = compare_tags(c.image_tag, latest)
                c.latest_tag = latest
                c.freshness_status = status
                c.freshness_reason = f"Latest semver tag found: {latest}"
                c.checked_at = datetime.utcnow()
            else:
                c.freshness_status = "error"
                c.freshness_reason = "Could not fetch tags from registry"
        
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update freshness: {e}")
        db.rollback()
    finally:
        db.close()

def start_background_tasks():
    scheduler.add_job(refresh_all, 'interval', seconds=settings.SCAN_INTERVAL_SECONDS)
    scheduler.start()
    logger.info(f"Background tasks started with interval {settings.SCAN_INTERVAL_SECONDS}s")
