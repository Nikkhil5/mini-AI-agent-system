import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os

# Global database path
DB_PATH = os.path.join(os.getcwd(), "ai_agent_reports.db")

def init_db():
    """Initialize database with error handling"""
    global DB_PATH
    
    try:
        # Remove corrupted file if exists
        if os.path.exists(DB_PATH):
            try:
                # Test if database is valid
                conn = sqlite3.connect(DB_PATH)
                conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
                conn.close()
                print(f"✅ Existing database is valid: {DB_PATH}")
                return
            except sqlite3.DatabaseError:
                print(f"🗑️  Removing corrupted database: {DB_PATH}")
                os.remove(DB_PATH)
        
        # Create fresh database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Create tables
        c.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                created_at TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                report_json TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Database initialized: {DB_PATH}")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        # Use backup path
        backup_path = f"reports_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        print(f"🔄 Using backup database: {backup_path}")
        
        DB_PATH = backup_path
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                created_at TEXT NOT NULL,
                title TEXT,
                summary TEXT,
                report_json TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        print(f"✅ Backup database created: {DB_PATH}")

def save_report(query: str, title: str, summary: str, report_obj: Dict[str, Any]) -> int:
    """Save report with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        c.execute(
            "INSERT INTO reports (query, created_at, title, summary, report_json) VALUES (?, ?, ?, ?, ?)",
            (query, now, title, summary, json.dumps(report_obj))
        )
        
        conn.commit()
        report_id = c.lastrowid
        conn.close()
        return report_id
    except Exception as e:
        print(f"❌ Save report failed: {e}")
        return -1

def list_reports(limit: int = 50) -> List[Dict[str, Any]]:
    """List reports with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute(
            "SELECT id, query, created_at, title, summary FROM reports ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        
        rows = c.fetchall()
        conn.close()
        
        reports = []
        for row in rows:
            reports.append({
                "id": row[0],
                "query": row[1],
                "created_at": row[2],
                "title": row[3],
                "summary": row[4]
            })
        
        return reports
    except Exception as e:
        print(f"❌ List reports failed: {e}")
        return []

def get_report(report_id: int) -> Optional[Dict[str, Any]]:
    """Get single report with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute(
            "SELECT id, query, created_at, title, summary, report_json FROM reports WHERE id = ?",
            (report_id,)
        )
        
        row = c.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "query": row[1],
                "created_at": row[2],
                "title": row[3],
                "summary": row[4],
                "report_data": json.loads(row[5])
            }
        return None
    except Exception as e:
        print(f"❌ Get report failed: {e}")
        return None

# Test database creation
if __name__ == "__main__":
    print("🧪 Testing database...")
    init_db()
    print("✅ Database test successful!")
