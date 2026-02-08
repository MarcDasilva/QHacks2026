"""
Scheduled data update script for fetching from ArcGIS API and updating Supabase.

This script:
1. Fetches latest data from the ArcGIS CRMServiceRequests API
2. Updates the Supabase requests table (inserts new, updates existing)
3. Generates vector embeddings for all rows without embeddings
4. Logs the update process

Designed to run every 24 hours via cron or systemd timer.

Usage:
python scripts/scheduled_data_update.py
python scripts/scheduled_data_update.py --dry-run  # Test without making changes
python scripts/scheduled_data_update.py --force-embeddings  # Regenerate all embeddings
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Any, List
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import pandas as pd
from app.db.connection import get_conn
from sentence_transformers import SentenceTransformer
from psycopg2.extras import execute_batch


# Configure logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"scheduled_update_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ArcGIS API Configuration
ARCGIS_API_URL = "https://services1.arcgis.com/5GRYvurYYUwAecLQ/arcgis/rest/services/CRMServiceRequests/FeatureServer/0/query"
ARCGIS_PARAMS = {
    "outFields": "*",
    "where": "1=1",
    "f": "json"  # Request JSON format
}

# Embedding model configuration
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_BATCH_SIZE = 100


class DataUpdateError(Exception):
    """Custom exception for data update errors"""
    pass


def fetch_arcgis_data() -> List[Dict[str, Any]]:
    """
    Fetch data from the ArcGIS API.
    
    Returns:
        List of feature dictionaries with attributes
        
    Raises:
        DataUpdateError: If the API request fails
    """
    logger.info(f"Fetching data from ArcGIS API: {ARCGIS_API_URL}")
    
    try:
        response = requests.get(ARCGIS_API_URL, params=ARCGIS_PARAMS, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        
        if "error" in data:
            raise DataUpdateError(f"ArcGIS API error: {data['error']}")
        
        features = data.get("features", [])
        logger.info(f"Successfully fetched {len(features)} features from ArcGIS API")
        
        # Extract attributes from features
        records = []
        for feature in features:
            attributes = feature.get("attributes", {})
            if attributes:
                records.append(attributes)
        
        logger.info(f"Extracted {len(records)} records with attributes")
        return records
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch data from ArcGIS API: {e}")
        raise DataUpdateError(f"API request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching ArcGIS data: {e}")
        raise DataUpdateError(f"Unexpected error: {e}")


def parse_timestamp(timestamp_ms: Optional[int]) -> Optional[datetime]:
    """
    Parse ArcGIS timestamp (milliseconds since epoch) to datetime.
    
    Args:
        timestamp_ms: Timestamp in milliseconds
        
    Returns:
        datetime object or None
    """
    if timestamp_ms is None:
        return None
    
    try:
        # Convert milliseconds to seconds
        timestamp_sec = timestamp_ms / 1000
        return datetime.fromtimestamp(timestamp_sec, tz=timezone.utc).date()
    except (ValueError, OSError):
        return None


def transform_arcgis_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Transform ArcGIS record to match requests table schema.
    
    Args:
        record: Raw ArcGIS feature attributes
        
    Returns:
        Transformed record dictionary or None if invalid
    """
    # Map ArcGIS fields to database columns
    # Adjust field names based on actual API response
    service_request_id = record.get('ServiceRequestID') or record.get('Service_Request_ID') or record.get('OBJECTID')
    
    if not service_request_id:
        logger.warning(f"Skipping record without service request ID: {record}")
        return None
    
    service_type = record.get('ServiceType') or record.get('Service_Type')
    if not service_type:
        logger.warning(f"Skipping record {service_request_id} without service type")
        return None
    
    # Parse timestamps (ArcGIS typically uses milliseconds since epoch)
    created_at = parse_timestamp(record.get('DateCreated') or record.get('Date_Created') or record.get('CreatedDate'))
    if not created_at:
        logger.warning(f"Skipping record {service_request_id} without valid creation date")
        return None
    
    resolved_at = parse_timestamp(record.get('DateClosed') or record.get('Date_Closed') or record.get('ClosedDate'))
    
    # Build description from service levels
    description_parts = []
    for i in range(1, 6):
        level = record.get(f'ServiceLevel{i}') or record.get(f'Service_Level_{i}')
        if level:
            description_parts.append(str(level).strip())
    description = ' > '.join(description_parts) if description_parts else None
    
    # Build location
    location_parts = []
    electoral_district = record.get('ElectoralDistrict') or record.get('Electoral_District')
    neighbourhood = record.get('Neighbourhood')
    
    if electoral_district:
        location_parts.append(str(electoral_district).strip())
    if neighbourhood:
        location_parts.append(str(neighbourhood).strip())
    
    location = ', '.join(location_parts) if location_parts else None
    
    # Reference number
    ref_number = record.get('ReferenceNumber') or record.get('Reference_Number')
    
    return {
        'service_request_id': str(service_request_id),
        'ref_number': str(ref_number) if ref_number else None,
        'service_type': str(service_type),
        'description': description,
        'created_at': created_at,
        'resolved_at': resolved_at,
        'location': location
    }


def upsert_requests(conn, records: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, int]:
    """
    Insert or update requests in the database.
    
    Args:
        conn: Database connection
        records: List of transformed records
        dry_run: If True, don't commit changes
        
    Returns:
        Dictionary with counts of inserted/updated/skipped records
    """
    cursor = conn.cursor()
    
    upsert_query = """
        INSERT INTO requests (
            service_request_id,
            ref_number,
            service_type,
            description,
            created_at,
            resolved_at,
            location
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (service_request_id) DO UPDATE SET
            ref_number = EXCLUDED.ref_number,
            service_type = EXCLUDED.service_type,
            description = EXCLUDED.description,
            resolved_at = EXCLUDED.resolved_at,
            location = EXCLUDED.location
    """
    
    inserted_count = 0
    skipped_count = 0
    
    logger.info(f"Upserting {len(records)} records into requests table...")
    
    for record in records:
        try:
            cursor.execute(upsert_query, (
                record['service_request_id'],
                record['ref_number'],
                record['service_type'],
                record['description'],
                record['created_at'],
                record['resolved_at'],
                record['location']
            ))
            inserted_count += 1
            
        except Exception as e:
            logger.warning(f"Failed to upsert record {record['service_request_id']}: {e}")
            skipped_count += 1
    
    if not dry_run:
        conn.commit()
        logger.info(f"Committed {inserted_count} records to database")
    else:
        conn.rollback()
        logger.info(f"Dry run: Would have committed {inserted_count} records")
    
    cursor.close()
    
    return {
        'upserted': inserted_count,
        'skipped': skipped_count
    }


def build_embedding_text(service_type: str, description: Optional[str]) -> Optional[str]:
    """Build text for embedding from service_type and description."""
    parts = []
    
    if service_type:
        parts.append(str(service_type).strip())
    
    if description:
        parts.append(str(description).strip())
    
    return ' | '.join(parts) if parts else None


def generate_embeddings(conn, force_regenerate: bool = False, dry_run: bool = False) -> int:
    """
    Generate vector embeddings for records without embeddings.
    
    Args:
        conn: Database connection
        force_regenerate: If True, regenerate embeddings for all records
        dry_run: If True, don't commit changes
        
    Returns:
        Number of embeddings generated
    """
    logger.info("Loading embedding model...")
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(f"Loaded model: {EMBEDDING_MODEL_NAME} (384 dimensions)")
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise DataUpdateError(f"Could not load embedding model: {e}")
    
    cursor = conn.cursor()
    
    # Fetch rows needing embeddings
    if force_regenerate:
        query = "SELECT id, service_type, description FROM requests ORDER BY id"
        logger.info("Fetching ALL records for embedding regeneration...")
    else:
        query = "SELECT id, service_type, description FROM requests WHERE embedding IS NULL ORDER BY id"
        logger.info("Fetching records without embeddings...")
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    logger.info(f"Found {len(rows)} rows needing embeddings")
    
    if len(rows) == 0:
        cursor.close()
        return 0
    
    # Process in batches
    total_updated = 0
    
    for i in range(0, len(rows), EMBEDDING_BATCH_SIZE):
        batch = rows[i:i + EMBEDDING_BATCH_SIZE]
        
        # Build texts for embedding
        texts = []
        ids = []
        
        for row_id, service_type, description in batch:
            text = build_embedding_text(service_type, description)
            if text:
                texts.append(text)
                ids.append(row_id)
        
        if not texts:
            continue
        
        # Generate embeddings
        try:
            embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            
            # Update database
            update_query = "UPDATE requests SET embedding = %s WHERE id = %s"
            update_data = [(embeddings[j].tolist(), ids[j]) for j in range(len(ids))]
            
            execute_batch(cursor, update_query, update_data)
            total_updated += len(update_data)
            
            logger.info(f"Generated embeddings for batch {i//EMBEDDING_BATCH_SIZE + 1} ({len(update_data)} records)")
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings for batch: {e}")
            continue
    
    if not dry_run:
        conn.commit()
        logger.info(f"Committed {total_updated} embedding updates to database")
    else:
        conn.rollback()
        logger.info(f"Dry run: Would have committed {total_updated} embeddings")
    
    cursor.close()
    
    return total_updated


def get_update_stats(conn) -> Dict[str, Any]:
    """Get statistics about the requests table."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM requests")
    total_records = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE embedding IS NOT NULL")
    records_with_embeddings = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(created_at) FROM requests")
    latest_created = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT service_type) FROM requests")
    unique_service_types = cursor.fetchone()[0]
    
    cursor.close()
    
    return {
        'total_records': total_records,
        'records_with_embeddings': records_with_embeddings,
        'records_without_embeddings': total_records - records_with_embeddings,
        'latest_created_date': latest_created,
        'unique_service_types': unique_service_types
    }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Scheduled update: Fetch ArcGIS data and update Supabase with embeddings'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test run without committing changes to database'
    )
    parser.add_argument(
        '--force-embeddings',
        action='store_true',
        help='Regenerate embeddings for all records (not just new ones)'
    )
    parser.add_argument(
        '--skip-api',
        action='store_true',
        help='Skip API fetch, only generate embeddings'
    )
    
    args = parser.parse_args()
    
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"Starting scheduled data update at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 80)
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = get_conn()
        logger.info("Database connection established")
        
        # Step 1: Fetch and upsert data from API
        if not args.skip_api:
            try:
                raw_records = fetch_arcgis_data()
                
                # Transform records
                logger.info("Transforming records to database schema...")
                transformed_records = []
                for record in raw_records:
                    transformed = transform_arcgis_record(record)
                    if transformed:
                        transformed_records.append(transformed)
                
                logger.info(f"Successfully transformed {len(transformed_records)} records")
                
                # Upsert into database
                upsert_stats = upsert_requests(conn, transformed_records, dry_run=args.dry_run)
                logger.info(f"Upsert complete: {upsert_stats['upserted']} upserted, {upsert_stats['skipped']} skipped")
                
            except DataUpdateError as e:
                logger.error(f"Data update failed: {e}")
                return 1
        else:
            logger.info("Skipping API fetch (--skip-api flag set)")
        
        # Step 2: Generate embeddings
        logger.info("\nGenerating vector embeddings...")
        embeddings_generated = generate_embeddings(
            conn,
            force_regenerate=args.force_embeddings,
            dry_run=args.dry_run
        )
        logger.info(f"Embedding generation complete: {embeddings_generated} embeddings generated")
        
        # Step 3: Get final statistics
        logger.info("\nFetching update statistics...")
        stats = get_update_stats(conn)
        
        logger.info("\n" + "=" * 80)
        logger.info("UPDATE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total records in database: {stats['total_records']:,}")
        logger.info(f"Records with embeddings: {stats['records_with_embeddings']:,}")
        logger.info(f"Records without embeddings: {stats['records_without_embeddings']:,}")
        logger.info(f"Unique service types: {stats['unique_service_types']}")
        logger.info(f"Latest created date: {stats['latest_created_date']}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"\nDuration: {duration:.2f} seconds")
        logger.info("=" * 80)
        
        conn.close()
        return 0
        
    except Exception as e:
        logger.error(f"Unexpected error during scheduled update: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
