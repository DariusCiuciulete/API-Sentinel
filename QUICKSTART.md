# Quick Start Guide - API Sentinel

## 1. First-Time Setup

### Install Dependencies

Open PowerShell in the project directory and run:

```powershell
# Activate virtual environment
.venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Start the Application

```powershell
# Method 1: Direct Python
python -m app.main

# Method 2: Using uvicorn (recommended for development)
uvicorn app.main:app --reload --port 8000
```

The server will start at: **http://localhost:8000**

## 3. Quick Test Workflow

### A. Start Mock API (Optional - for monitoring testing)

Open a **new** PowerShell window:

```powershell
cd examples
python mock_api.py
```

This starts a test API server at http://127.0.0.1:8001

### B. Discover APIs

1. Go to **Discovery** page
2. Upload `examples/petstore_openapi.yaml` or `examples/mock_api_spec.yaml`
3. Click "Parse Specification"
4. View discovered endpoints in **Inventory**

### C. Monitor APIs

1. Go to **Monitoring** page
2. Configure thresholds for endpoints
3. Click "Run Monitoring Now"
4. View results and any alerts

### D. View Logs & Reports

1. Go to **Logs** page
2. View system events
3. Export logs or monitoring reports

## 4. Example Test Scenarios

### Scenario 1: Discovery from OpenAPI Spec

1. Go to Discovery page
2. Upload `examples/petstore_openapi.yaml`
3. Verify 9 endpoints were discovered
4. Check Inventory page - should show all endpoints

### Scenario 2: Discovery from Documentation

1. Go to Discovery page
2. Upload `examples/sample_api_docs.html`
3. Set:
   - Service Name: "Sample API"
   - Base URL: "https://api.example.com/v1"
4. Verify endpoints were extracted from HTML

### Scenario 3: Monitoring Live API

1. Start mock API: `python examples/mock_api.py`
2. Upload `examples/mock_api_spec.yaml` via Discovery
3. Go to Monitoring page
4. Configure endpoint (optional):
   - Check interval: 60 seconds
   - Timeout: 30 seconds
   - Latency threshold: 1000ms
   - Error rate threshold: 10%
5. Click "Run Monitoring Now"
6. Test individual endpoints:
   - `/api/slow` - Should trigger latency alert (2s response)
   - `/api/random-fail` - May trigger error rate alert after multiple checks
   - `/api/users` - Should always succeed

### Scenario 4: Alert Management

1. After monitoring creates alerts (from slow or failing endpoints)
2. Go to Alerts page
3. View alert details (type, severity, threshold vs actual)
4. Resolve individual alerts or "Resolve All"

### Scenario 5: Export Data

**Export Inventory:**
- Inventory page → "Export CSV" button
- Downloads `api_inventory.csv`

**Export Logs:**
- Logs page → "Export CSV" or "Export JSON"
- Downloads complete event log

**Export Monitoring Report:**
- Logs page → "Monitoring Report" button
- Downloads comprehensive monitoring statistics

## 5. Typical First-Time Usage (15-Minute Target)

**Minute 0-2:** Start application and open dashboard

**Minute 2-5:** Upload OpenAPI spec, verify discovery

**Minute 5-8:** Review inventory, configure monitoring for 2-3 endpoints

**Minute 8-12:** Run monitoring, observe results

**Minute 12-15:** Check alerts, export inventory, review logs

## 6. Common Issues & Solutions

**Issue:** "Module not found" error
- **Solution:** Ensure virtual environment is activated and dependencies installed

**Issue:** Database not created
- **Solution:** Database auto-creates on first run. Check for `api_sentinel.db` file.

**Issue:** Mock API won't start
- **Solution:** Port 8001 may be in use. Edit `mock_api.py` to use different port.

**Issue:** Monitoring shows all endpoints as failed
- **Solution:** Ensure mock API is running if testing with mock endpoints, or endpoints are accessible.

## 7. Stopping the Application

Press `Ctrl+C` in the terminal running the server

## 8. Project Structure Reference

```
API-Sentinel/
├── app/
│   ├── main.py              # Start server from here
│   ├── database.py          # Database operations
│   └── routers/             # Feature modules
├── templates/               # Web UI pages
├── static/                  # CSS styling
├── examples/                # Test files
├── api_sentinel.db          # Database (auto-created)
└── api_sentinel.log         # Application logs
```

## 9. Next Steps

1. Explore all dashboard pages
2. Try discovery with your own OpenAPI specs
3. Set up monitoring for real APIs
4. Configure custom alert thresholds
5. Export and review reports

## 10. Development Mode

For development with auto-reload:

```powershell
uvicorn app.main:app --reload --port 8000
```

Any code changes will automatically restart the server.
