"""
Read from raw_requests table (default)
python scripts/request_processing.py

Read from raw_requests table with service type filter
python scripts/request_processing.py --service-type "Some Service Type"

Read from CSV file
python scripts/request_processing.py --csv path/to/file.csv

Read from CSV with service type filter
python scripts/request_processing.py --csv path/to/file.csv --service-type "Some Service Type"
"""

import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from app.db.connection import get_conn


def parse_date(date_str):
    """Parse date string to date object. Returns None if invalid."""
    if not date_str or pd.isna(date_str):
        return None
    
    date_formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    
    return None


def build_description(row):
    levels = []
    for i in range(1, 6):
        level = row.get(f'Service Level {i}')
        if level and pd.notna(level) and str(level).strip():
            levels.append(str(level).strip())
    
    return ' > '.join(levels) if levels else None


def build_location(row):
    parts = []
    
    electoral_district = row.get('Electoral District')
    if electoral_district and pd.notna(electoral_district):
        parts.append(str(electoral_district).strip())
    
    neighbourhood = row.get('Neighbourhood')
    if neighbourhood and pd.notna(neighbourhood):
        parts.append(str(neighbourhood).strip())
    
    return ', '.join(parts) if parts else None


def process_from_raw_requests_table(conn, service_type_filter=None):
    print(f"[INFO] Reading from raw_requests table...")
    
    query = "SELECT * FROM raw_requests"
    if service_type_filter:
        query += f" WHERE \"Service Type\" = %s"
        df = pd.read_sql_query(query, conn, params=(service_type_filter,))
    else:
        df = pd.read_sql_query(query, conn)
    
    print(f"[INFO] Found {len(df)} rows in raw_requests table")
    
    if len(df) == 0:
        print("[WARNING] No data found in raw_requests table")
        return 0
    
    return insert_requests(conn, df)


def process_from_csv(csv_path, conn, service_type_filter=None):
    print(f"[INFO] Reading CSV file: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"[INFO] Found {len(df)} rows in CSV file")
    
    if service_type_filter:
        df = df[df['Service Type'] == service_type_filter]
        print(f"[INFO] Filtered to {len(df)} rows matching service type: {service_type_filter}")
    
    return insert_requests(conn, df)


def insert_requests(conn, df):
    """Insert DataFrame rows into requests table."""
    cursor = conn.cursor()
    
    inserted_count = 0
    skipped_count = 0
    
    insert_query = """
        INSERT INTO requests (
            service_request_id,
            ref_number,
            service_type,
            description,
            created_at,
            resolved_at,
            location
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (service_request_id) DO NOTHING
    """
    
    print(f"[INFO] Processing {len(df)} rows...")
    
    for idx, row in df.iterrows():
        service_request_id = row.get('Service Request ID')
        service_type = row.get('Service Type')
        
        # Skip rows without required fields
        if not service_request_id or pd.isna(service_request_id):
            skipped_count += 1
            continue
        
        if not service_type or pd.isna(service_type):
            skipped_count += 1
            continue
        
        # Parse dates
        created_at = parse_date(row.get('Date Created'))
        if not created_at:
            skipped_count += 1
            continue  # created_at is required
        
        resolved_at = parse_date(row.get('Date Closed'))
        
        # Build other fields
        ref_number = row.get('Reference Number')
        if ref_number and pd.isna(ref_number):
            ref_number = None
        else:
            ref_number = str(ref_number).strip() if ref_number else None
        
        description = build_description(row)
        location = build_location(row)
        
        try:
            cursor.execute(insert_query, (
                str(service_request_id).strip(),
                ref_number,
                str(service_type).strip(),
                description,
                created_at,
                resolved_at,
                location
            ))
            inserted_count += 1
            
            if (inserted_count + skipped_count) % 100 == 0:
                print(f"[INFO] Processed {inserted_count + skipped_count} rows... ({inserted_count} inserted, {skipped_count} skipped)")
        
        except Exception as e:
            print(f"[ERROR] Failed to insert row {idx}: {e}")
            skipped_count += 1
            continue
    
    conn.commit()
    cursor.close()
    
    print(f"[SUCCESS] Inserted {inserted_count} rows, skipped {skipped_count} rows")
    return inserted_count


def verify_insertion(conn):
    """Verify that requests table has data."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM requests;")
    count = cursor.fetchone()[0]
    cursor.close()
    
    print(f"[INFO] Total rows in requests table: {count}")
    return count > 0


def main():
    """Main function to process requests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process requests from CSV or raw_requests table')
    parser.add_argument('--csv', type=str, help='Path to CSV file (optional, defaults to raw_requests table)')
    parser.add_argument('--service-type', type=str, help='Filter by service type (optional)')
    
    args = parser.parse_args()
    
    try:
        print("[INFO] Connecting to database...")
        conn = get_conn()
        print("[SUCCESS] Connected to database")
        
        # Process data
        if args.csv:
            if not os.path.exists(args.csv):
                print(f"[ERROR] CSV file not found: {args.csv}")
                return 1
            inserted = process_from_csv(args.csv, conn, args.service_type)
        else:
            inserted = process_from_raw_requests_table(conn, args.service_type)
        
        # Verify insertion
        if verify_insertion(conn):
            print("[SUCCESS] Phase 3 complete! Requests table has data.")
        else:
            print("[WARNING] Requests table is still empty. Check for errors above.")
        
        conn.close()
        return 0 if inserted > 0 else 1
    
    except Exception as e:
        print(f"[ERROR] Failed to process requests: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
