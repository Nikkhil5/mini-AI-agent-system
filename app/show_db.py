# Create show_db_fixed.py in app folder
import sqlite3
import os

def find_and_show_database():
    # Try different database file names
    possible_dbs = [
        "ai_agent_reports.db",
        "reports.db", 
        "simple_reports.db"
    ]
    
    print("🔍 Searching for database files...")
    
    for db_file in possible_dbs:
        if os.path.exists(db_file):
            print(f"📁 Found: {db_file}")
            
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Check if reports table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports';")
                if not cursor.fetchone():
                    print(f"❌ Table 'reports' not found in {db_file}")
                    conn.close()
                    continue
                
                # Get count
                cursor.execute("SELECT COUNT(*) FROM reports")
                count = cursor.fetchone()[0]
                
                # Get recent reports
                cursor.execute("SELECT id, query, created_at FROM reports ORDER BY id DESC LIMIT 5")
                recent = cursor.fetchall()
                
                conn.close()
                
                # Display results
                print("="*60)
                print(f"📊 AI Research Agent Database Status")  
                print("="*60)
                print(f"📂 Database File: {db_file}")
                print(f"📊 Total Reports: {count}")
                print()
                print("📋 Recent Research Queries:")
                print("-"*40)
                
                for i, (report_id, query, created_at) in enumerate(recent, 1):
                    print(f"{i}. {query}")
                    print(f"   📅 {created_at[:19]}")
                    print(f"   🆔 ID: {report_id}")
                    print()
                
                print("✅ Database persistence working perfectly!")
                print("="*60)
                return
                
            except Exception as e:
                print(f"❌ Error accessing {db_file}: {e}")
                continue
    
    print("❌ No valid database found!")
    print(f"📂 Searched in: {os.getcwd()}")

if __name__ == "__main__":
    find_and_show_database()
