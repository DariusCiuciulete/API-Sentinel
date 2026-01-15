"""
Discovery Router - API discovery from OpenAPI/Swagger specs and documentation
"""
from fastapi import APIRouter, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import yaml
import json
import re
import logging
from bs4 import BeautifulSoup
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def discovery_page(request: Request):
    """API discovery page"""
    return templates.TemplateResponse("discovery.html", {
        "request": request
    })


@router.post("/upload-spec")
async def upload_openapi_spec(
    file: UploadFile = File(...),
    service_name: str = Form(None)
):
    """Parse and import endpoints from OpenAPI/Swagger specification"""
    try:
        content = await file.read()
        
        # Try to parse as YAML first, then JSON
        try:
            if file.filename.endswith('.json'):
                spec = json.loads(content.decode('utf-8'))
            else:
                spec = yaml.safe_load(content.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error parsing spec file: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid OpenAPI/Swagger specification file")
        
        # Extract service name
        if not service_name:
            service_name = spec.get('info', {}).get('title', 'Unknown API')
        
        # Extract base URL
        base_url = ""
        if 'servers' in spec and spec['servers']:
            base_url = spec['servers'][0]['url']
        elif 'host' in spec:  # Swagger 2.0
            scheme = spec.get('schemes', ['https'])[0]
            base_path = spec.get('basePath', '')
            base_url = f"{scheme}://{spec['host']}{base_path}"
        
        # Determine if internal (heuristic based on domain)
        is_internal = any(pattern in base_url.lower() for pattern in 
                         ['localhost', '127.0.0.1', '192.168.', '10.', 'internal', 'local'])
        
        # Extract authentication info
        auth_types = []
        if 'securitySchemes' in spec.get('components', {}):
            auth_types = list(spec['components']['securitySchemes'].keys())
        elif 'securityDefinitions' in spec:  # Swagger 2.0
            auth_types = list(spec['securityDefinitions'].keys())
        
        auth_type = ', '.join(auth_types) if auth_types else None
        
        # Extract endpoints
        paths = spec.get('paths', {})
        endpoints_added = 0
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                    continue
                
                description = details.get('summary') or details.get('description', '')
                
                endpoint_id = db.add_endpoint(
                    service_name=service_name,
                    base_url=base_url,
                    path=path,
                    method=method.upper(),
                    description=description,
                    auth_type=auth_type,
                    is_internal=is_internal,
                    discovery_source=f"openapi:{file.filename}"
                )
                
                endpoints_added += 1
        
        logger.info(f"Discovered {endpoints_added} endpoints from {file.filename}")
        db.log_event("DISCOVERY", None, 
                    f"OpenAPI spec parsed: {service_name}",
                    f"File: {file.filename}, Endpoints: {endpoints_added}")
        
        return {
            "success": True,
            "service_name": service_name,
            "endpoints_added": endpoints_added,
            "message": f"Successfully discovered {endpoints_added} endpoints from {file.filename}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing OpenAPI spec: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing specification: {str(e)}")


@router.post("/upload-docs")
async def upload_documentation(
    file: UploadFile = File(...),
    service_name: str = Form(...),
    base_url: str = Form(...)
):
    """Parse and extract endpoints from API documentation (HTML/text)"""
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
        
        # Determine if internal
        is_internal = any(pattern in base_url.lower() for pattern in 
                         ['localhost', '127.0.0.1', '192.168.', '10.', 'internal', 'local'])
        
        endpoints_added = 0
        
        # Try to parse as HTML first
        if file.filename.endswith('.html') or '<html' in text_content.lower():
            soup = BeautifulSoup(text_content, 'html.parser')
            
            # Extract text from code blocks and pre tags (common in API docs)
            code_blocks = soup.find_all(['code', 'pre', 'div'])
            text_to_search = '\n'.join([block.get_text() for block in code_blocks])
        else:
            text_to_search = text_content
        
        # Regex patterns to match API endpoints
        # Pattern 1: HTTP method followed by path (e.g., "GET /api/users")
        pattern1 = r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(/[\w\-/{}:]*)'
        
        # Pattern 2: Path in URL format (e.g., "https://api.example.com/v1/users")
        pattern2 = r'https?://[^\s]+?((/[\w\-/{}:]+)+)'
        
        # Pattern 3: Markdown-style endpoints (e.g., "`GET /api/users`")
        pattern3 = r'`(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(/[\w\-/{}:]*)`'
        
        found_endpoints = set()
        
        # Find matches for all patterns
        for match in re.finditer(pattern1, text_to_search, re.IGNORECASE):
            method, path = match.groups()
            found_endpoints.add((method.upper(), path))
        
        for match in re.finditer(pattern2, text_to_search):
            path = match.group(1)
            # Try to infer method from context (look for words around the URL)
            context = text_to_search[max(0, match.start()-50):match.end()+50]
            method = 'GET'  # Default
            for m in ['POST', 'PUT', 'DELETE', 'PATCH']:
                if m in context.upper():
                    method = m
                    break
            found_endpoints.add((method, path))
        
        for match in re.finditer(pattern3, text_to_search, re.IGNORECASE):
            method, path = match.groups()
            found_endpoints.add((method.upper(), path))
        
        # Add discovered endpoints to database
        for method, path in found_endpoints:
            # Extract description from surrounding text (simplified)
            description = f"Discovered from {file.filename}"
            
            endpoint_id = db.add_endpoint(
                service_name=service_name,
                base_url=base_url,
                path=path,
                method=method,
                description=description,
                auth_type=None,
                is_internal=is_internal,
                discovery_source=f"docs:{file.filename}"
            )
            
            endpoints_added += 1
        
        logger.info(f"Discovered {endpoints_added} endpoints from documentation: {file.filename}")
        db.log_event("DISCOVERY", None,
                    f"Documentation parsed: {service_name}",
                    f"File: {file.filename}, Endpoints: {endpoints_added}")
        
        return {
            "success": True,
            "service_name": service_name,
            "endpoints_added": endpoints_added,
            "message": f"Successfully discovered {endpoints_added} endpoints from documentation"
        }
    
    except Exception as e:
        logger.error(f"Error processing documentation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing documentation: {str(e)}")


@router.post("/parse-url")
async def parse_url(
    url: str = Form(...),
    service_name: str = Form(None)
):
    """Fetch and parse OpenAPI spec from a URL"""
    try:
        import requests
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Try to parse as JSON or YAML
        try:
            spec = response.json()
        except:
            spec = yaml.safe_load(response.text)
        
        # Extract service name
        if not service_name:
            service_name = spec.get('info', {}).get('title', 'Unknown API')
        
        # Extract base URL
        base_url = ""
        if 'servers' in spec and spec['servers']:
            base_url = spec['servers'][0]['url']
        elif 'host' in spec:
            scheme = spec.get('schemes', ['https'])[0]
            base_path = spec.get('basePath', '')
            base_url = f"{scheme}://{spec['host']}{base_path}"
        
        is_internal = any(pattern in base_url.lower() for pattern in 
                         ['localhost', '127.0.0.1', '192.168.', '10.', 'internal', 'local'])
        
        # Extract authentication info
        auth_types = []
        if 'securitySchemes' in spec.get('components', {}):
            auth_types = list(spec['components']['securitySchemes'].keys())
        elif 'securityDefinitions' in spec:
            auth_types = list(spec['securityDefinitions'].keys())
        
        auth_type = ', '.join(auth_types) if auth_types else None
        
        # Extract endpoints
        paths = spec.get('paths', {})
        endpoints_added = 0
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                    continue
                
                description = details.get('summary') or details.get('description', '')
                
                endpoint_id = db.add_endpoint(
                    service_name=service_name,
                    base_url=base_url,
                    path=path,
                    method=method.upper(),
                    description=description,
                    auth_type=auth_type,
                    is_internal=is_internal,
                    discovery_source=f"url:{url}"
                )
                
                endpoints_added += 1
        
        logger.info(f"Discovered {endpoints_added} endpoints from URL: {url}")
        db.log_event("DISCOVERY", None,
                    f"OpenAPI spec fetched from URL: {service_name}",
                    f"URL: {url}, Endpoints: {endpoints_added}")
        
        return {
            "success": True,
            "service_name": service_name,
            "endpoints_added": endpoints_added,
            "message": f"Successfully discovered {endpoints_added} endpoints from URL"
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error fetching URL: {str(e)}")
    except Exception as e:
        logger.error(f"Error parsing spec from URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error parsing specification: {str(e)}")
