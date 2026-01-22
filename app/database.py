"""
API Sentinel Database Module
Handles SQLite database operations for inventory and monitoring
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = Path(__file__).resolve().parent.parent / "api_sentinel.db"


class Database:
    """Database manager for API Sentinel"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # API Endpoints Inventory Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_endpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                path TEXT NOT NULL,
                method TEXT NOT NULL,
                description TEXT,
                auth_type TEXT,
                is_internal BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                discovery_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(base_url, path, method)
            )
        ''')
        
        # Monitoring Results Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id INTEGER NOT NULL,
                status_code INTEGER,
                response_time_ms REAL,
                success BOOLEAN,
                error_message TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (endpoint_id) REFERENCES api_endpoints (id) ON DELETE CASCADE
            )
        ''')
        
        # Alerts Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                threshold_value REAL,
                actual_value REAL,
                is_resolved BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (endpoint_id) REFERENCES api_endpoints (id) ON DELETE CASCADE
            )
        ''')
        
        # Logs/Events Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                endpoint_id INTEGER,
                message TEXT NOT NULL,
                details TEXT,
                severity TEXT DEFAULT 'INFO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (endpoint_id) REFERENCES api_endpoints (id) ON DELETE SET NULL
            )
        ''')
        
        # Monitoring Configuration Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id INTEGER NOT NULL UNIQUE,
                check_interval_seconds INTEGER DEFAULT 300,
                timeout_seconds INTEGER DEFAULT 30,
                latency_threshold_ms REAL DEFAULT 1000,
                error_rate_threshold REAL DEFAULT 0.1,
                enabled BOOLEAN DEFAULT 1,
                last_check TIMESTAMP,
                FOREIGN KEY (endpoint_id) REFERENCES api_endpoints (id) ON DELETE CASCADE
            )
        ''')
        
        # Alert Thresholds Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_thresholds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id INTEGER,
                threshold_type TEXT NOT NULL,
                threshold_value REAL NOT NULL,
                comparison TEXT DEFAULT 'greater_than',
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (endpoint_id) REFERENCES api_endpoints (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    # ==================== API Endpoints CRUD ====================
    
    def add_endpoint(self, service_name: str, base_url: str, path: str, 
                     method: str, description: str = None, auth_type: str = None,
                     is_internal: bool = False, discovery_source: str = None) -> int:
        """Add a new API endpoint to inventory"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO api_endpoints 
                (service_name, base_url, path, method, description, auth_type, is_internal, discovery_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (service_name, base_url, path, method, description, auth_type, is_internal, discovery_source))
            
            endpoint_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Added endpoint: {service_name} - {method} {path}")
            return endpoint_id
            
        except sqlite3.IntegrityError:
            # Endpoint already exists, update it instead
            cursor.execute('''
                UPDATE api_endpoints 
                SET service_name = ?, description = ?, auth_type = ?, 
                    is_internal = ?, discovery_source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE base_url = ? AND path = ? AND method = ?
            ''', (service_name, description, auth_type, is_internal, discovery_source, base_url, path, method))
            
            cursor.execute('''
                SELECT id FROM api_endpoints 
                WHERE base_url = ? AND path = ? AND method = ?
            ''', (base_url, path, method))
            
            endpoint_id = cursor.fetchone()[0]
            conn.commit()
            
            self.log_event("DISCOVERY", endpoint_id, 
                          f"Endpoint updated: {method} {path}", 
                          f"Source: {discovery_source}")
            
            logger.info(f"Updated existing endpoint: {service_name} - {method} {path}")
            return endpoint_id
        finally:
            conn.close()
    
    def get_all_endpoints(self, active_only: bool = False) -> List[Dict]:
        """Get all API endpoints"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM api_endpoints"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY service_name, path"
        
        cursor.execute(query)
        endpoints = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return endpoints
    
    def get_endpoint_by_id(self, endpoint_id: int) -> Optional[Dict]:
        """Get endpoint by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM api_endpoints WHERE id = ?", (endpoint_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def update_endpoint(self, endpoint_id: int, **kwargs) -> bool:
        """Update endpoint fields"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ['service_name', 'base_url', 'path', 'method', 'description', 
                       'auth_type', 'is_internal', 'is_active']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(endpoint_id)
        
        query = f"UPDATE api_endpoints SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            self.log_event("INVENTORY", endpoint_id, f"Endpoint updated", f"Fields: {', '.join(kwargs.keys())}")
        
        return success
    
    def delete_endpoint(self, endpoint_id: int) -> bool:
        """Delete an endpoint"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM api_endpoints WHERE id = ?", (endpoint_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            self.log_event("INVENTORY", None, f"Endpoint deleted (ID: {endpoint_id})")
        
        return success
    
    # ==================== Monitoring Results ====================
    
    def add_monitoring_result(self, endpoint_id: int, status_code: int = None,
                             response_time_ms: float = None, success: bool = True,
                             error_message: str = None) -> int:
        """Add a monitoring result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO monitoring_results 
            (endpoint_id, status_code, response_time_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (endpoint_id, status_code, response_time_ms, success, error_message))
        
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return result_id
    
    def get_monitoring_results(self, endpoint_id: int = None, limit: int = 100) -> List[Dict]:
        """Get monitoring results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if endpoint_id:
            cursor.execute('''
                SELECT * FROM monitoring_results 
                WHERE endpoint_id = ? 
                ORDER BY checked_at DESC 
                LIMIT ?
            ''', (endpoint_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM monitoring_results 
                ORDER BY checked_at DESC 
                LIMIT ?
            ''', (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_monitoring_stats(self) -> Dict:
        """Get overall monitoring statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_checks,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_checks,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_checks,
                AVG(response_time_ms) as avg_response_time,
                MAX(checked_at) as last_check
            FROM monitoring_results
            WHERE checked_at >= datetime('now', '-24 hours')
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row['total_checks'] > 0:
            return {
                'total_checks': row['total_checks'],
                'successful_checks': row['successful_checks'],
                'failed_checks': row['failed_checks'],
                'availability': round((row['successful_checks'] / row['total_checks']) * 100, 2),
                'avg_response_time': round(row['avg_response_time'], 2) if row['avg_response_time'] else 0,
                'last_check': row['last_check']
            }
        
        return {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'availability': 0,
            'avg_response_time': 0,
            'last_check': None
        }
    
    # ==================== Alerts ====================
    
    def create_alert(self, endpoint_id: int, alert_type: str, severity: str,
                    message: str, threshold_value: float = None, 
                    actual_value: float = None) -> int:
        """Create a new alert"""
        # Implementation pending
        return 0
    
    def get_active_alerts(self, endpoint_id: int = None) -> List[Dict]:
        """Get active alerts"""
        # Implementation pending
        return []
    
    def resolve_alert(self, alert_id: int) -> bool:
        """Mark an alert as resolved"""
        # Implementation pending
        return False
    
    # ==================== Logging ====================
    
    def log_event(self, event_type: str, endpoint_id: int = None, 
                  message: str = "", details: str = None, severity: str = "INFO") -> int:
        """Log an event"""
        # Implementation pending
        return 0
    
    def get_logs(self, event_type: str = None, limit: int = 100) -> List[Dict]:
        """Get event logs"""
        # Implementation pending
        return []
    
    # ==================== Monitoring Configuration ====================
    
    def set_monitoring_config(self, endpoint_id: int, check_interval_seconds: int = 300,
                             timeout_seconds: int = 30, latency_threshold_ms: float = 1000,
                             error_rate_threshold: float = 0.1) -> int:
        """Set monitoring configuration for an endpoint"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO monitoring_config 
            (endpoint_id, check_interval_seconds, timeout_seconds, 
             latency_threshold_ms, error_rate_threshold)
            VALUES (?, ?, ?, ?, ?)
        ''', (endpoint_id, check_interval_seconds, timeout_seconds, 
              latency_threshold_ms, error_rate_threshold))
        
        config_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return config_id
    
    def get_monitoring_config(self, endpoint_id: int) -> Optional[Dict]:
        """Get monitoring configuration for an endpoint"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM monitoring_config WHERE endpoint_id = ?
        ''', (endpoint_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # ==================== Dashboard Statistics ====================
    
    def get_dashboard_stats(self) -> Dict:
        """Get statistics for dashboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total APIs and endpoints
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT service_name) as total_apis,
                COUNT(*) as total_endpoints,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_endpoints
            FROM api_endpoints
        ''')
        inventory_stats = dict(cursor.fetchone())
        
        # Get monitoring stats
        monitoring_stats = self.get_monitoring_stats()
        
        conn.close()
        
        return {
            'total_apis': inventory_stats['total_apis'],
            'total_endpoints': inventory_stats['total_endpoints'],
            'active_endpoints': inventory_stats['active_endpoints'],
            'avg_response_time': monitoring_stats['avg_response_time']
        }


# Global database instance
db = Database()
