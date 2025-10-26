import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List
import json

class DatabaseManager:
    def __init__(self, db_path: str = "epanet_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                input_data TEXT,
                results TEXT,
                error_message TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS real_time_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                node_id TEXT NOT NULL,
                pressure REAL,
                flow REAL,
                demand REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                node_id TEXT,
                time_step INTEGER,
                pressure REAL,
                flow REAL,
                head REAL,
                FOREIGN KEY (run_id) REFERENCES simulation_runs (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_simulation_run(self, status: str, input_data: Dict[str, Any] = None, 
                          results: Dict[str, Any] = None, error_message: str = None) -> int:
        """Save simulation run to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert datetime objects and Pydantic models to strings for JSON serialization
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'dict'):  # Pydantic models
                return obj.dict()
            elif hasattr(obj, '__dict__'):  # Objects with __dict__
                return obj.__dict__
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        cursor.execute('''
            INSERT INTO simulation_runs (status, input_data, results, error_message)
            VALUES (?, ?, ?, ?)
        ''', (status, json.dumps(input_data, default=json_serial) if input_data else None,
              json.dumps(results, default=json_serial) if results else None, error_message))
        
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return run_id
    
    def save_real_time_data(self, node_id: str, pressure: float = None, 
                          flow: float = None, demand: float = None):
        """Save real-time sensor data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO real_time_data (node_id, pressure, flow, demand)
            VALUES (?, ?, ?, ?)
        ''', (node_id, pressure, flow, demand))
        
        conn.commit()
        conn.close()
    
    def get_latest_real_time_data(self, node_id: str = None) -> List[Dict[str, Any]]:
        """Get latest real-time data for a specific node or all nodes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if node_id:
            cursor.execute('''
                SELECT * FROM real_time_data 
                WHERE node_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (node_id,))
        else:
            cursor.execute('''
                SELECT * FROM real_time_data 
                ORDER BY timestamp DESC 
                LIMIT 100
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(zip([col[0] for col in cursor.description], row)) for row in results]

# Global database instance
db_manager = DatabaseManager()

def init_db():
    """Initialize database"""
    db_manager.init_database()
