"""
Set up database tables by running migrations.
This script creates the requests and alerts tables (from migration 001_init.sql).

Usage:
python scripts/setup_database.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.connection import get_conn


def run_migration_001(conn):
    """Run migration 001_init.sql to create requests and alerts tables."""
    cursor = conn.cursor()
    
    print("[INFO] Running migration 001_init.sql...")
    
    # Create requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id SERIAL PRIMARY KEY,
            service_request_id TEXT UNIQUE,
            ref_number TEXT,
            service_type TEXT NOT NULL,
            description TEXT,
            created_at DATE NOT NULL,
            resolved_at DATE,
            location TEXT,
            embedding VECTOR(384)
        );
    """)
    
    # Create alerts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            service_type TEXT NOT NULL,
            severity INT NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            acknowledged BOOLEAN DEFAULT FALSE
        );
    """)
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_requests_service_request_id ON requests(service_request_id);
        CREATE INDEX IF NOT EXISTS idx_requests_service_type ON requests(service_type);
        CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests(created_at);
    """)
    
    conn.commit()
    cursor.close()
    
    print("[SUCCESS] Migration 001 complete!")
    print("[INFO] Created tables: requests, alerts")


def verify_tables(conn):
    """Verify that tables were created successfully."""
    cursor = conn.cursor()
    
    # Check requests table
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'requests'
        );
    """)
    requests_exists = cursor.fetchone()[0]
    
    # Check alerts table
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'alerts'
        );
    """)
    alerts_exists = cursor.fetchone()[0]
    
    # Get column info for requests table
    if requests_exists:
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'requests'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        print("\n[INFO] Requests table columns:")
        for col_name, col_type in columns:
            print(f"   - {col_name}: {col_type}")
    
    cursor.close()
    
    return requests_exists and alerts_exists


def main():
    """Main function."""
    try:
        print("[INFO] Connecting to database...")
        conn = get_conn()
        print("[SUCCESS] Connected to database")
        
        # Run migration
        run_migration_001(conn)
        
        # Verify tables
        if verify_tables(conn):
            print("\n[SUCCESS] Database setup complete!")
            print("[INFO] Tables are ready for data upload")
        else:
            print("\n[WARNING] Some tables may not have been created correctly")
        
        conn.close()
        return 0
    
    except Exception as e:
        print(f"[ERROR] Failed to set up database: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
