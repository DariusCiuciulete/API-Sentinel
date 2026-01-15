# API Sentinel

**A System for API Discovery, Inventory and Monitoring in Small and Medium Enterprises**

## Overview

API Sentinel is a lightweight, automated, self-contained system that helps SMEs discover, inventory, and monitor REST APIs by analyzing existing documentation and specification files (OpenAPI/Swagger) and presenting results in a single dashboard with alerts.

## Features

### ✅ Implemented

- **API Discovery**
  - OpenAPI/Swagger 2.0 & 3.0 specification parsing (YAML/JSON)
  - Structured documentation parsing (HTML/text with regex)
  - URL-based specification fetching
  - Manual endpoint entry

- **Unified API Inventory**
  - Centralized endpoint storage with metadata
  - Internal/external classification
  - Authentication mechanism tracking
  - Search and filter capabilities
  - CSV export functionality

- **API Monitoring**
  - Periodic health checks
  - Availability tracking
  - Response time measurement
  - Error rate calculation
  - Configurable check intervals and thresholds
  - Manual and automated monitoring runs

- **Alerting System**
  - Threshold-based alerts (latency, error rate, availability)
  - Severity levels (info, warning, danger)
  - Alert resolution and management
  - Dashboard alert display

- **Single-Pane Dashboard**
  - Real-time statistics
  - Active alerts display
  - Endpoint inventory overview
  - Monitoring status
  - Recent activity log

- **Logging & Reports**
  - Comprehensive event logging
  - Discovery, monitoring, and alert event tracking
  - CSV and JSON export
  - Monitoring reports with per-endpoint statistics
  - Filtering by event type and severity

## Technology Stack

- **Backend**: Python 3, FastAPI
- **Database**: SQLite
- **Frontend**: HTML/CSS, Jinja2 templates
- **Libraries**: 
  - PyYAML (OpenAPI parsing)
  - BeautifulSoup4 (documentation parsing)
  - Requests (HTTP monitoring)
  - python-multipart (file uploads)

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/API-Sentinel.git
   cd API-Sentinel
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   The database will be automatically created on first run.

5. **Run the application**
   ```bash
   python -m app.main
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. **Access the dashboard**
   Open your browser and navigate to: `http://localhost:8000`

## Usage Guide

### 1. Discover APIs

**From OpenAPI/Swagger Specification:**
1. Go to Discovery page
2. Upload a YAML or JSON OpenAPI/Swagger file
3. Endpoints are automatically extracted and added to inventory

**From Documentation:**
1. Go to Discovery page
2. Upload HTML or text documentation
3. Specify service name and base URL
4. System extracts endpoint patterns using regex

**From URL:**
1. Go to Discovery page
2. Enter URL to OpenAPI specification
3. System fetches and parses automatically

**Manual Entry:**
1. Go to Inventory page
2. Click "Add Endpoint"
3. Fill in endpoint details

### 2. Manage Inventory

- View all discovered endpoints
- Search and filter by service, path, or method
- Toggle endpoints active/inactive
- Edit endpoint details
- Export inventory to CSV

### 3. Monitor APIs

- Configure monitoring intervals and thresholds per endpoint
- Run monitoring manually or wait for periodic checks
- View real-time health status
- Test individual endpoints on-demand
- Review historical monitoring data

### 4. Handle Alerts

- View active alerts on dashboard and alerts page
- Filter by severity or alert type
- Resolve individual or all alerts
- Configure thresholds to control alert triggers

### 5. Review Logs & Reports

- View system event logs
- Filter by event type and severity
- Export logs to CSV or JSON
- Generate monitoring reports
- Track discovery, monitoring, and alert activities

## Project Structure

```
API-Sentinel/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Database operations and schema
│   └── routers/
│       ├── __init__.py
│       ├── discovery.py     # API discovery endpoints
│       ├── inventory.py     # Inventory management
│       ├── monitoring.py    # Monitoring operations
│       ├── alerts.py        # Alert management
│       └── logs.py          # Logging and reports
├── templates/               # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── inventory.html
│   ├── discovery.html
│   ├── monitoring.html
│   ├── alerts.html
│   └── logs.html
├── static/
│   └── style.css           # Application styling
├── requirements.txt         # Python dependencies
├── .gitignore
└── README.md

Generated files:
├── api_sentinel.db         # SQLite database
└── api_sentinel.log        # Application logs
```

## Database Schema

- **api_endpoints**: Stores discovered API endpoints
- **monitoring_results**: Historical monitoring check results
- **alerts**: Alert records with threshold information
- **event_logs**: System event logging
- **monitoring_config**: Per-endpoint monitoring configuration
- **alert_thresholds**: Custom alert threshold definitions

## Configuration

### Monitoring Configuration (Per Endpoint)
- **Check Interval**: How often to check endpoint (default: 300s)
- **Timeout**: Maximum wait time for response (default: 30s)
- **Latency Threshold**: Alert if response time exceeds (default: 1000ms)
- **Error Rate Threshold**: Alert if error rate exceeds (default: 10%)

## Testing

### Mock APIs for Testing

Create local mock API servers for testing. See `examples/` directory.

### Sample Files

Check the `examples/` directory for:
- Sample OpenAPI specifications
- Mock API server scripts
- Sample documentation files

## Performance Targets

- **Deployment**: Single mid-range workstation
- **Monitoring Capacity**: Up to 10 APIs efficiently
- **Resource Usage**: 
  - App footprint: < 200MB
  - RAM usage: < 500MB
- **Usability**: First-time users can perform discovery + monitoring within 15 minutes

## Constraints & Limitations

- REST APIs only (no GraphQL, gRPC, or SOAP)
- No vulnerability testing or penetration testing
- No machine learning anomaly detection (rule-based alerts only)
- Local deployment only (no enterprise/cloud integration)
- Threshold-based monitoring (no complex correlation analysis)

## Future Enhancements

- Email notification integration
- Periodic background monitoring scheduler
- User authentication and access control
- API versioning tracking
- More advanced reporting and analytics
- Integration with notification channels (Slack, Teams, etc.)

## License

This project is developed as part of academic research for Small and Medium Enterprise API management.

## Author

Darius Ciuciulete - 6COSC023W Project

## Support

For issues, questions, or contributions, please create an issue on the GitHub repository.
