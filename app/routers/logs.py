"""
Logs Router - View and export system logs and reports
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import csv
import json
import io
import logging
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def logs_page(request: Request, event_type: str = None, limit: int = 100):
    """Logs and reports page"""
    logs = db.get_logs(event_type=event_type, limit=limit)
    
    # Get event type counts
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT event_type, COUNT(*) as count
        FROM event_logs
        GROUP BY event_type
        ORDER BY count DESC
    ''')
    
    event_type_counts = dict(cursor.fetchall())
    
    # Get severity counts
    cursor.execute('''
        SELECT severity, COUNT(*) as count
        FROM event_logs
        GROUP BY severity
    ''')
    
    severity_counts = dict(cursor.fetchall())
    
    conn.close()
    
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "logs": logs,
        "event_type_counts": event_type_counts,
        "severity_counts": severity_counts,
        "event_type_filter": event_type,
        "limit": limit
    })


@router.get("/export/csv")
async def export_logs_csv(event_type: str = None, limit: int = 1000):
    """Export logs to CSV"""
    try:
        logs = db.get_logs(event_type=event_type, limit=limit)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'id', 'event_type', 'endpoint_id', 'service_name', 'path',
            'message', 'details', 'severity', 'created_at'
        ])
        
        writer.writeheader()
        writer.writerows(logs)
        
        output.seek(0)
        
        logger.info(f"Logs exported to CSV (count: {len(logs)})")
        db.log_event("EXPORT", None, f"Logs exported to CSV ({len(logs)} records)")
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=api_sentinel_logs.csv"}
        )
    
    except Exception as e:
        logger.error(f"Error exporting logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/json")
async def export_logs_json(event_type: str = None, limit: int = 1000):
    """Export logs to JSON"""
    try:
        logs = db.get_logs(event_type=event_type, limit=limit)
        
        # Convert to JSON
        logs_json = json.dumps(logs, indent=2, default=str)
        
        logger.info(f"Logs exported to JSON (count: {len(logs)})")
        db.log_event("EXPORT", None, f"Logs exported to JSON ({len(logs)} records)")
        
        return StreamingResponse(
            iter([logs_json]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=api_sentinel_logs.json"}
        )
    
    except Exception as e:
        logger.error(f"Error exporting logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring-report")
async def monitoring_report():
    """Generate a monitoring report"""
    try:
        # Get overall monitoring stats
        stats = db.get_monitoring_stats()
        
        # Get per-endpoint statistics
        endpoints = db.get_all_endpoints(active_only=False)
        
        endpoint_stats = []
        for endpoint in endpoints:
            results = db.get_monitoring_results(endpoint_id=endpoint['id'], limit=100)
            
            if results:
                successful = sum(1 for r in results if r['success'])
                failed = len(results) - successful
                avg_response = sum(r['response_time_ms'] or 0 for r in results) / len(results)
                
                endpoint_stats.append({
                    'endpoint_id': endpoint['id'],
                    'service_name': endpoint['service_name'],
                    'path': endpoint['path'],
                    'method': endpoint['method'],
                    'total_checks': len(results),
                    'successful': successful,
                    'failed': failed,
                    'availability': round((successful / len(results)) * 100, 2),
                    'avg_response_time': round(avg_response, 2)
                })
        
        return {
            "overall_stats": stats,
            "endpoint_stats": endpoint_stats,
            "report_generated_at": db.get_connection().execute("SELECT datetime('now')").fetchone()[0]
        }
    
    except Exception as e:
        logger.error(f"Error generating monitoring report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/monitoring-report")
async def export_monitoring_report(format: str = "json"):
    """Export monitoring report in CSV or JSON format"""
    try:
        report = await monitoring_report()
        
        if format == "csv":
            output = io.StringIO()
            
            # Write overall stats
            output.write("Overall Monitoring Statistics\n")
            output.write(f"Total Checks,{report['overall_stats']['total_checks']}\n")
            output.write(f"Successful Checks,{report['overall_stats']['successful_checks']}\n")
            output.write(f"Failed Checks,{report['overall_stats']['failed_checks']}\n")
            output.write(f"Availability,{report['overall_stats']['availability']}%\n")
            output.write(f"Average Response Time,{report['overall_stats']['avg_response_time']}ms\n")
            output.write("\n")
            
            # Write per-endpoint stats
            output.write("Per-Endpoint Statistics\n")
            writer = csv.DictWriter(output, fieldnames=[
                'service_name', 'method', 'path', 'total_checks', 'successful',
                'failed', 'availability', 'avg_response_time'
            ])
            writer.writeheader()
            writer.writerows(report['endpoint_stats'])
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=monitoring_report.csv"}
            )
        
        else:  # JSON
            report_json = json.dumps(report, indent=2, default=str)
            
            return StreamingResponse(
                iter([report_json]),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=monitoring_report.json"}
            )
    
    except Exception as e:
        logger.error(f"Error exporting monitoring report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
