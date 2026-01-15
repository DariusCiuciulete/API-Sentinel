"""
Inventory Router - Manage API endpoints inventory
"""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import csv
import io
import logging
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["inventory"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def inventory_page(request: Request, search: str = None):
    """Inventory management page"""
    endpoints = db.get_all_endpoints()
    
    # Filter by search if provided
    if search:
        search_lower = search.lower()
        endpoints = [e for e in endpoints if 
                    search_lower in e['service_name'].lower() or 
                    search_lower in e['path'].lower() or
                    search_lower in e['method'].lower()]
    
    return templates.TemplateResponse("inventory.html", {
        "request": request,
        "endpoints": endpoints,
        "search": search or ""
    })


@router.post("/add")
async def add_endpoint(
    service_name: str = Form(...),
    base_url: str = Form(...),
    path: str = Form(...),
    method: str = Form(...),
    description: str = Form(None),
    auth_type: str = Form(None),
    is_internal: bool = Form(False)
):
    """Add a new endpoint manually"""
    try:
        endpoint_id = db.add_endpoint(
            service_name=service_name,
            base_url=base_url,
            path=path,
            method=method,
            description=description,
            auth_type=auth_type,
            is_internal=is_internal,
            discovery_source="manual"
        )
        
        logger.info(f"Manually added endpoint: {service_name} - {method} {path}")
        return {"success": True, "endpoint_id": endpoint_id, "message": "Endpoint added successfully"}
    
    except Exception as e:
        logger.error(f"Error adding endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update/{endpoint_id}")
async def update_endpoint(
    endpoint_id: int,
    service_name: str = Form(None),
    base_url: str = Form(None),
    path: str = Form(None),
    method: str = Form(None),
    description: str = Form(None),
    auth_type: str = Form(None),
    is_internal: bool = Form(None),
    is_active: bool = Form(None)
):
    """Update an existing endpoint"""
    try:
        updates = {}
        if service_name: updates['service_name'] = service_name
        if base_url: updates['base_url'] = base_url
        if path: updates['path'] = path
        if method: updates['method'] = method
        if description is not None: updates['description'] = description
        if auth_type: updates['auth_type'] = auth_type
        if is_internal is not None: updates['is_internal'] = is_internal
        if is_active is not None: updates['is_active'] = is_active
        
        success = db.update_endpoint(endpoint_id, **updates)
        
        if success:
            logger.info(f"Updated endpoint ID: {endpoint_id}")
            return {"success": True, "message": "Endpoint updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Endpoint not found")
    
    except Exception as e:
        logger.error(f"Error updating endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete/{endpoint_id}")
async def delete_endpoint(endpoint_id: int):
    """Delete an endpoint"""
    try:
        success = db.delete_endpoint(endpoint_id)
        
        if success:
            logger.info(f"Deleted endpoint ID: {endpoint_id}")
            return {"success": True, "message": "Endpoint deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Endpoint not found")
    
    except Exception as e:
        logger.error(f"Error deleting endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/toggle/{endpoint_id}")
async def toggle_endpoint(endpoint_id: int):
    """Toggle endpoint active status"""
    try:
        endpoint = db.get_endpoint_by_id(endpoint_id)
        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        new_status = not endpoint['is_active']
        success = db.update_endpoint(endpoint_id, is_active=new_status)
        
        if success:
            status_text = "activated" if new_status else "deactivated"
            logger.info(f"Endpoint ID {endpoint_id} {status_text}")
            return {"success": True, "is_active": new_status, "message": f"Endpoint {status_text}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to toggle endpoint")
    
    except Exception as e:
        logger.error(f"Error toggling endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_inventory():
    """Export inventory to CSV"""
    try:
        endpoints = db.get_all_endpoints()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'id', 'service_name', 'base_url', 'path', 'method', 'description',
            'auth_type', 'is_internal', 'is_active', 'discovery_source',
            'created_at', 'updated_at'
        ])
        
        writer.writeheader()
        writer.writerows(endpoints)
        
        # Convert to bytes
        output.seek(0)
        
        logger.info("Inventory exported to CSV")
        db.log_event("EXPORT", None, "Inventory exported to CSV")
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=api_inventory.csv"}
        )
    
    except Exception as e:
        logger.error(f"Error exporting inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{endpoint_id}")
async def get_endpoint_details(request: Request, endpoint_id: int):
    """Get detailed information about a specific endpoint"""
    endpoint = db.get_endpoint_by_id(endpoint_id)
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Get monitoring results for this endpoint
    monitoring_results = db.get_monitoring_results(endpoint_id=endpoint_id, limit=50)
    
    # Get alerts for this endpoint
    alerts = db.get_active_alerts(endpoint_id=endpoint_id)
    
    return templates.TemplateResponse("endpoint_detail.html", {
        "request": request,
        "endpoint": endpoint,
        "monitoring_results": monitoring_results,
        "alerts": alerts
    })
