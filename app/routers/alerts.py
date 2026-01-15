"""
Alerts Router - Manage and view alerts
"""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def alerts_page(request: Request, status: str = "active"):
    """Alerts management page"""
    if status == "active":
        alerts = db.get_active_alerts()
    else:
        # Get all alerts (would need a new db method for this)
        alerts = db.get_active_alerts()  # Simplified for now
    
    # Get alert statistics
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            alert_type,
            COUNT(*) as count
        FROM alerts
        WHERE is_resolved = 0
        GROUP BY alert_type
    ''')
    
    alert_type_counts = dict(cursor.fetchall())
    
    cursor.execute('''
        SELECT 
            severity,
            COUNT(*) as count
        FROM alerts
        WHERE is_resolved = 0
        GROUP BY severity
    ''')
    
    severity_counts = dict(cursor.fetchall())
    
    conn.close()
    
    return templates.TemplateResponse("alerts.html", {
        "request": request,
        "alerts": alerts,
        "alert_type_counts": alert_type_counts,
        "severity_counts": severity_counts,
        "status_filter": status
    })


@router.post("/resolve/{alert_id}")
async def resolve_alert(alert_id: int):
    """Mark an alert as resolved"""
    try:
        success = db.resolve_alert(alert_id)
        
        if success:
            db.log_event("ALERT", None, f"Alert resolved (ID: {alert_id})")
            logger.info(f"Alert {alert_id} resolved")
            return {"success": True, "message": "Alert resolved successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve-all")
async def resolve_all_alerts():
    """Resolve all active alerts"""
    try:
        alerts = db.get_active_alerts()
        count = 0
        
        for alert in alerts:
            if db.resolve_alert(alert['id']):
                count += 1
        
        db.log_event("ALERT", None, f"Bulk resolve: {count} alerts resolved")
        logger.info(f"Resolved {count} alerts")
        
        return {"success": True, "resolved_count": count, "message": f"Resolved {count} alerts"}
    
    except Exception as e:
        logger.error(f"Error resolving alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/endpoint/{endpoint_id}")
async def get_endpoint_alerts(endpoint_id: int):
    """Get all alerts for a specific endpoint"""
    endpoint = db.get_endpoint_by_id(endpoint_id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    alerts = db.get_active_alerts(endpoint_id=endpoint_id)
    
    return {
        "endpoint": endpoint,
        "alerts": alerts,
        "alert_count": len(alerts)
    }
