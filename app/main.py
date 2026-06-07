from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from .config import settings
from .db import init_db, get_db
from .models import Workload, WorkloadImage
from .background import start_background_tasks, refresh_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kubernetes Image Inventory")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def startup_event():
    init_db()
    start_background_tasks()
    await refresh_all()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    workloads = db.query(Workload).all()
    
    total_images = db.query(WorkloadImage).count()
    outdated_images = db.query(WorkloadImage).filter(WorkloadImage.freshness_status == "outdated").count()
    unknown_freshness = db.query(WorkloadImage).filter(WorkloadImage.freshness_status == "unknown").count()
    
    cve_stats = db.query(
        func.sum(WorkloadImage.critical_cve),
        func.sum(WorkloadImage.high_cve)
    ).first()
    
    critical_cves = cve_stats[0] or 0
    high_cves = cve_stats[1] or 0
    
    last_scan = db.query(Workload).order_by(Workload.last_observed.desc()).first()
    last_scan_time = last_scan.last_observed if last_scan else None

    return templates.TemplateResponse("index.html", {
        "request": request,
        "workloads": workloads,
        "summary": {
            "total_workloads": len(workloads),
            "total_images": total_images,
            "outdated_images": outdated_images,
            "unknown_freshness": unknown_freshness,
            "critical_cves": critical_cves,
            "high_cves": high_cves,
            "last_scan_time": last_scan_time
        }
    })

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready(db: Session = Depends(get_db)):
    try:
        # Check DB connection
        db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Not ready")

@app.get("/refresh")
async def manual_refresh(request: Request):
    await refresh_all()
    return RedirectResponse(url="/")
