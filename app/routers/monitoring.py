"""
Monitoring Router - API health monitoring and metrics
"""
from fastapi import APIRouter, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import asyncio
import time
import logging
import requests
from typing import List, Dict
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))

# Track if monitoring is currently running
monitoring_active = False


@router.get("/", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Monitoring dashboard page"""
    endpoints = db.get_all_endpoints(active_only=True)
    monitoring_stats = db.get_monitoring_stats()
    
    # Get latest monitoring result for each endpoint
    for endpoint in endpoints:
        results = db.get_monitoring_results(endpoint_id=endpoint['id'], limit=1)
        endpoint['last_result'] = results[0] if results else None
        
        # Get monitoring config
        config = db.get_monitoring_config(endpoint['id'])
        endpoint['config'] = config
    
    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "endpoints": endpoints,
        "monitoring_stats": monitoring_stats,
        "monitoring_active": monitoring_active
    })


def check_endpoint(endpoint: Dict) -> Dict:
    """Check a single endpoint and return result"""
    endpoint_id = endpoint['id']
    full_url = endpoint['base_url'].rstrip('/') + endpoint['path']
    
    try:
        # Get monitoring config or use defaults
        config = db.get_monitoring_config(endpoint_id)
        timeout = config['timeout_seconds'] if config else 30
        
        start_time = time.time()
        
        # Send request based on method
        method = endpoint['method'].lower()
        response = requests.request(
            method=method,
            url=full_url,
            timeout=timeout,
            allow_redirects=True,
            verify=False  # For testing; in production, handle SSL properly
        )
        
        response_time_ms = (time.time() - start_time) * 1000
        
        # Check if response is successful
        success = 200 <= response.status_code < 400
        
        # Store monitoring result
        db.add_monitoring_result(
            endpoint_id=endpoint_id,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            success=success,
            error_message=None
        )
        
        # Check thresholds and create alerts if needed
        check_thresholds(endpoint_id, response_time_ms, success, config)
        
        logger.info(f"Monitored {method.upper()} {endpoint['path']}: {response.status_code} ({response_time_ms:.2f}ms)")
        
        return {
            "endpoint_id": endpoint_id,
            "success": success,
            "status_code": response.status_code,
            "response_time_ms": response_time_ms
        }
    
    except requests.exceptions.Timeout:
        error_msg = "Request timeout"
        db.add_monitoring_result(
            endpoint_id=endpoint_id,
            status_code=None,
            response_time_ms=None,
            success=False,
            error_message=error_msg
        )
        
        logger.warning(f"Timeout monitoring {endpoint['path']}")
        
        # Create alert for timeout
        db.create_alert(
            endpoint_id=endpoint_id,
            alert_type="TIMEOUT",
            severity="warning",
            message=f"Endpoint timeout: {endpoint['service_name']} - {endpoint['path']}"
        )
        
        return {
            "endpoint_id": endpoint_id,
            "success": False,
            "error": error_msg
        }
    
    except Exception as e:
        error_msg = str(e)
        db.add_monitoring_result(
            endpoint_id=endpoint_id,
            status_code=None,
            response_time_ms=None,
            success=False,
            error_message=error_msg
        )
        
        logger.error(f"Error monitoring {endpoint['path']}: {error_msg}")
        
        # Create alert for failure
        db.create_alert(
            endpoint_id=endpoint_id,
            alert_type="FAILURE",
            severity="danger",
            message=f"Endpoint check failed: {endpoint['service_name']} - {endpoint['path']}",
            actual_value=0
        )
        
        return {
            "endpoint_id": endpoint_id,
            "success": False,
            "error": error_msg
        }


def check_thresholds(endpoint_id: int, response_time_ms: float, success: bool, config: Dict = None):
    """Check if monitoring results exceed thresholds and create alerts"""
    if not config:
        config = db.get_monitoring_config(endpoint_id)
    
    if not config:
        return
    
    endpoint = db.get_endpoint_by_id(endpoint_id)
    
    # Check latency threshold
    latency_threshold = config.get('latency_threshold_ms', 1000)
    if response_time_ms > latency_threshold:
        db.create_alert(
            endpoint_id=endpoint_id,
            alert_type="HIGH_LATENCY",
            severity="warning",
            message=f"High latency detected: {endpoint['service_name']} - {endpoint['path']}",
            threshold_value=latency_threshold,
            actual_value=response_time_ms
        )
    
    # Check availability (if failed)
    if not success:
        db.create_alert(
            endpoint_id=endpoint_id,
            alert_type="UNAVAILABLE",
            severity="danger",
            message=f"Endpoint unavailable: {endpoint['service_name']} - {endpoint['path']}"
        )
    
    # Check error rate (last 10 checks)
    recent_results = db.get_monitoring_results(endpoint_id=endpoint_id, limit=10)
    if len(recent_results) >= 5:  # Only check if we have enough data
        failed_count = sum(1 for r in recent_results if not r['success'])
        error_rate = failed_count / len(recent_results)
        
        error_threshold = config.get('error_rate_threshold', 0.1)
        if error_rate > error_threshold:
            db.create_alert(
                endpoint_id=endpoint_id,
                alert_type="HIGH_ERROR_RATE",
                severity="danger",
                message=f"High error rate: {endpoint['service_name']} - {endpoint['path']} ({error_rate*100:.1f}%)",
                threshold_value=error_threshold,
                actual_value=error_rate
            )


@router.post("/run")
async def run_monitoring(background_tasks: BackgroundTasks):
    """Manually trigger monitoring for all active endpoints"""
    global monitoring_active
    
    if monitoring_active:
        return {"success": False, "message": "Monitoring is already running"}
    
    try:
        monitoring_active = True
        
        # Get all active endpoints
        endpoints = db.get_all_endpoints(active_only=True)
        
        if not endpoints:
            monitoring_active = False
            return {"success": False, "message": "No active endpoints to monitor"}
        
        db.log_event("MONITORING", None, f"Manual monitoring started for {len(endpoints)} endpoints")
        
        # Check all endpoints
        results = []
        for endpoint in endpoints:
            result = check_endpoint(endpoint)
            results.append(result)
        
        monitoring_active = False
        
        # Count successes and failures
        successes = sum(1 for r in results if r.get('success'))
        failures = len(results) - successes
        
        db.log_event("MONITORING", None, 
                    f"Monitoring completed: {successes} successful, {failures} failed")
        
        logger.info(f"Monitoring run completed: {successes}/{len(results)} successful")
        
        return {
            "success": True,
            "total": len(results),
            "successful": successes,
            "failed": failures,
            "message": f"Monitoring completed: {successes} successful, {failures} failed"
        }
    
    except Exception as e:
        monitoring_active = False
        logger.error(f"Error during monitoring: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/{endpoint_id}")
async def test_endpoint(endpoint_id: int):
    """Test a specific endpoint immediately"""
    endpoint = db.get_endpoint_by_id(endpoint_id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    result = check_endpoint(endpoint)
    
    return result


@router.post("/configure/{endpoint_id}")
async def configure_monitoring(
    endpoint_id: int,
    check_interval_seconds: int = Form(300),
    timeout_seconds: int = Form(30),
    latency_threshold_ms: float = Form(1000),
    error_rate_threshold: float = Form(0.1),
    enabled: bool = Form(True)
):
    """Configure monitoring settings for an endpoint"""
    try:
        endpoint = db.get_endpoint_by_id(endpoint_id)
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        config_id = db.set_monitoring_config(
            endpoint_id=endpoint_id,
            check_interval_seconds=check_interval_seconds,
            timeout_seconds=timeout_seconds,
            latency_threshold_ms=latency_threshold_ms,
            error_rate_threshold=error_rate_threshold
        )
        
        db.log_event("MONITORING", endpoint_id, 
                    "Monitoring configuration updated",
                    f"Interval: {check_interval_seconds}s, Timeout: {timeout_seconds}s")
        
        logger.info(f"Monitoring configured for endpoint {endpoint_id}")
        
        return {
            "success": True,
            "config_id": config_id,
            "message": "Monitoring configuration updated"
        }
    
    except Exception as e:
        logger.error(f"Error configuring monitoring: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{endpoint_id}")
async def get_monitoring_results(endpoint_id: int, limit: int = 50):
    """Get monitoring results for a specific endpoint"""
    endpoint = db.get_endpoint_by_id(endpoint_id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    results = db.get_monitoring_results(endpoint_id=endpoint_id, limit=limit)
    
    return {
        "endpoint": endpoint,
        "results": results
    }


@router.get("/stats")
async def get_monitoring_statistics():
    """Get overall monitoring statistics"""
    stats = db.get_monitoring_stats()
    
    return stats


# Background task for periodic monitoring (to be called by scheduler)
async def periodic_monitoring_task():
    """Run periodic monitoring for all enabled endpoints"""
    global monitoring_active
    
    if monitoring_active:
        logger.info("Monitoring already running, skipping this cycle")
        return
    
    try:
        monitoring_active = True
        
        endpoints = db.get_all_endpoints(active_only=True)
        
        for endpoint in endpoints:
            config = db.get_monitoring_config(endpoint['id'])
            
            # Check if this endpoint should be monitored now
            if config and config.get('enabled'):
                check_endpoint(endpoint)
        
        monitoring_active = False
        
    except Exception as e:
        monitoring_active = False
        logger.error(f"Error in periodic monitoring: {str(e)}")
