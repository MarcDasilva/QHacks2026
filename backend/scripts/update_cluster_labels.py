"""
Script to update cluster labels in the database from a CSV file.

This script reads cluster_labels.csv and updates the label column in the clusters table
for matching cluster_id and parent_cluster_id combinations.

Usage:
python scripts/update_cluster_labels.py
python scripts/update_cluster_labels.py --csv path/to/cluster_labels.csv
python scripts/update_cluster_labels.py --dry-run  # Preview changes without updating
"""

import sys
import csv
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.db.connection import get_conn


def update_cluster_labels(conn, csv_path, dry_run=False):
    """
    Update cluster labels from CSV file.
    
    Args:
        conn: Database connection
        csv_path: Path to the CSV file with cluster labels
        dry_run: If True, only preview changes without updating database
    """
    cursor = conn.cursor()
    
    # Read CSV file
    labels_data = []
    skipped_empty = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            level = row['Level'].strip()
            parent_id = row['Parent Cluster ID'].strip() if row['Parent Cluster ID'].strip() else None
            cluster_id = int(row['Cluster ID'].strip())
            label = row['Label'].strip()
            
            # Skip empty labels (don't set "EMPTY" as a string in database)
            if not label or label == 'EMPTY':
                skipped_empty += 1
                continue
            
            labels_data.append({
                'level': level,
                'parent_id': int(parent_id) if parent_id else None,
                'cluster_id': cluster_id,
                'label': label
            })
    
    print(f"[INFO] Found {len(labels_data)} clusters to update ({skipped_empty} EMPTY rows skipped)")
    
    if dry_run:
        print("\n[DRY RUN] Would update the following labels:")
        print("-" * 80)
    
    updated_count = 0
    not_found_count = 0
    
    for label_info in labels_data:
        parent_id = label_info['parent_id']
        cluster_id = label_info['cluster_id']
        label = label_info['label']
        
        # Check if cluster exists
        if parent_id is None:
            # Top-level cluster
            cursor.execute("""
                SELECT id, cluster_id, parent_cluster_id, level, label
                FROM clusters
                WHERE cluster_id = %s AND parent_cluster_id IS NULL AND level = 1
            """, (cluster_id,))
        else:
            # Sub-cluster
            cursor.execute("""
                SELECT id, cluster_id, parent_cluster_id, level, label
                FROM clusters
                WHERE cluster_id = %s AND parent_cluster_id = %s AND level = 2
            """, (cluster_id, parent_id))
        
        cluster = cursor.fetchone()
        
        if cluster:
            cluster_db_id, db_cluster_id, db_parent_id, db_level, current_label = cluster
            
            if dry_run:
                print(f"Cluster ID: {cluster_id}, Parent: {parent_id or 'NULL'}, "
                      f"Current Label: {current_label or '(empty)'}, "
                      f"New Label: {label}")
            else:
                # Update the label
                cursor.execute("""
                    UPDATE clusters
                    SET label = %s, updated_at = NOW()
                    WHERE id = %s
                """, (label, cluster_db_id))
                updated_count += 1
        else:
            if dry_run:
                print(f"[WARNING] Cluster not found - ID: {cluster_id}, Parent: {parent_id or 'NULL'}")
            not_found_count += 1
    
    if not dry_run:
        conn.commit()
        print(f"\n[SUCCESS] Updated {updated_count} cluster labels")
        if not_found_count > 0:
            print(f"[WARNING] {not_found_count} clusters from CSV were not found in database")
    else:
        print(f"\n[DRY RUN] Would update {len(labels_data) - not_found_count} clusters")
        print(f"[DRY RUN] {not_found_count} clusters from CSV were not found in database")
    
    cursor.close()


def main():
    parser = argparse.ArgumentParser(description='Update cluster labels from CSV file')
    parser.add_argument(
        '--csv',
        type=str,
        default='cluster_labels.csv',
        help='Path to CSV file with cluster labels (default: cluster_labels.csv)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating database'
    )
    
    args = parser.parse_args()
    
    # Resolve CSV path relative to backend directory
    csv_path = Path(__file__).parent.parent / args.csv
    if not csv_path.exists():
        print(f"[ERROR] CSV file not found: {csv_path}")
        sys.exit(1)
    
    print(f"[INFO] Reading labels from: {csv_path}")
    
    try:
        conn = get_conn()
        print("[INFO] Connected to database")
        
        update_cluster_labels(conn, csv_path, dry_run=args.dry_run)
        
        conn.close()
        print("[INFO] Database connection closed")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to update cluster labels: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
