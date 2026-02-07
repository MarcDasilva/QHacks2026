"""
Reduce requests table by dropping half the data, then re-cluster.

This script:
1. Shows you how many rows you have
2. Drops half the requests (oldest by created_at, or random)
3. Clears cluster assignments
4. You then re-run clustering on the remaining data

Usage:
python scripts/reduce_requests_data.py --strategy oldest  # Drop oldest 50%
python scripts/reduce_requests_data.py --strategy random  # Drop random 50%
python scripts/reduce_requests_data.py --strategy oldest --percent 30  # Drop oldest 30%
python scripts/reduce_requests_data.py --dry-run  # Just show what would be deleted
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from app.db.connection import get_conn


def get_stats(conn):
    """Get statistics about requests table."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM requests")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE embedding IS NOT NULL")
    with_embeddings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE top_cluster_id IS NOT NULL")
    with_clusters = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM requests WHERE created_at IS NOT NULL")
    date_range = cursor.fetchone()
    
    cursor.close()
    
    return {
        'total': total,
        'with_embeddings': with_embeddings,
        'with_clusters': with_clusters,
        'min_date': date_range[0],
        'max_date': date_range[1]
    }


def get_ids_to_delete(conn, strategy='oldest', percent=50):
    """Get IDs of rows to delete."""
    cursor = conn.cursor()
    
    total = get_stats(conn)['total']
    delete_count = int(total * percent / 100)
    
    if strategy == 'oldest':
        # Delete oldest records by created_at
        cursor.execute("""
            SELECT id 
            FROM requests 
            WHERE created_at IS NOT NULL
            ORDER BY created_at ASC
            LIMIT %s
        """, (delete_count,))
    elif strategy == 'random':
        # Delete random records
        cursor.execute("""
            SELECT id 
            FROM requests 
            ORDER BY RANDOM()
            LIMIT %s
        """, (delete_count,))
    elif strategy == 'newest':
        # Delete newest records by created_at
        cursor.execute("""
            SELECT id 
            FROM requests 
            WHERE created_at IS NOT NULL
            ORDER BY created_at DESC
            LIMIT %s
        """, (delete_count,))
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    return ids


def delete_requests(conn, ids, dry_run=False):
    """Delete requests by IDs."""
    if not ids:
        print("[INFO] No rows to delete")
        return 0
    
    cursor = conn.cursor()
    
    if dry_run:
        print(f"[DRY RUN] Would delete {len(ids)} requests")
        # Show sample of what would be deleted
        cursor.execute("""
            SELECT id, service_type, created_at 
            FROM requests 
            WHERE id = ANY(%s)
            ORDER BY created_at
            LIMIT 10
        """, (ids,))
        samples = cursor.fetchall()
        print("\n[DRY RUN] Sample of rows that would be deleted:")
        for row_id, service_type, created_at in samples:
            print(f"  ID {row_id}: {service_type} - {created_at}")
        if len(ids) > 10:
            print(f"  ... and {len(ids) - 10} more")
        cursor.close()
        return len(ids)
    
    # Delete in batches to avoid long transactions
    batch_size = 1000
    deleted = 0
    
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        cursor.execute("DELETE FROM requests WHERE id = ANY(%s)", (batch,))
        deleted += cursor.rowcount
    
    conn.commit()
    cursor.close()
    
    return deleted


def clear_cluster_assignments(conn, dry_run=False):
    """Clear cluster assignments from requests table."""
    cursor = conn.cursor()
    
    if dry_run:
        cursor.execute("SELECT COUNT(*) FROM requests WHERE top_cluster_id IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"[DRY RUN] Would clear cluster assignments from {count} requests")
        cursor.close()
        return
    
    cursor.execute("UPDATE requests SET top_cluster_id = NULL, sub_cluster_id = NULL")
    affected = cursor.rowcount
    conn.commit()
    cursor.close()
    
    print(f"[SUCCESS] Cleared cluster assignments from {affected} requests")


def clear_clusters_table(conn, dry_run=False):
    """Clear the clusters table."""
    cursor = conn.cursor()
    
    if dry_run:
        cursor.execute("SELECT COUNT(*) FROM clusters")
        count = cursor.fetchone()[0]
        print(f"[DRY RUN] Would delete {count} cluster records")
        cursor.close()
        return
    
    cursor.execute("DELETE FROM clusters")
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    
    print(f"[SUCCESS] Deleted {deleted} cluster records")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reduce requests table size by dropping data')
    parser.add_argument('--strategy', choices=['oldest', 'newest', 'random'], default='oldest',
                       help='Which records to delete (default: oldest)')
    parser.add_argument('--percent', type=int, default=50,
                       help='Percentage of records to delete (default: 50)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    if args.percent <= 0 or args.percent >= 100:
        print("[ERROR] Percent must be between 1 and 99")
        return 1
    
    try:
        print("[INFO] Connecting to database...")
        conn = get_conn()
        print("[SUCCESS] Connected to database")
        
        # Show current stats
        stats = get_stats(conn)
        print(f"\n[INFO] Current statistics:")
        print(f"   Total requests: {stats['total']:,}")
        print(f"   With embeddings: {stats['with_embeddings']:,}")
        print(f"   With clusters: {stats['with_clusters']:,}")
        if stats['min_date']:
            print(f"   Date range: {stats['min_date']} to {stats['max_date']}")
        
        # Calculate what will be deleted
        delete_count = int(stats['total'] * args.percent / 100)
        keep_count = stats['total'] - delete_count
        
        print(f"\n[INFO] Plan:")
        print(f"   Strategy: {args.strategy}")
        print(f"   Will delete: {delete_count:,} requests ({args.percent}%)")
        print(f"   Will keep: {keep_count:,} requests ({100 - args.percent}%)")
        
        if not args.dry_run:
            response = input("\n[WARNING] This will permanently delete data. Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("[CANCELLED] Operation cancelled")
                conn.close()
                return 0
        
        # Get IDs to delete
        print(f"\n[INFO] Finding records to delete...")
        ids_to_delete = get_ids_to_delete(conn, args.strategy, args.percent)
        print(f"[INFO] Found {len(ids_to_delete):,} records to delete")
        
        # Clear cluster assignments first (if not dry run)
        if not args.dry_run:
            print("\n[INFO] Clearing cluster assignments...")
            clear_cluster_assignments(conn, dry_run=False)
            
            print("\n[INFO] Clearing clusters table...")
            clear_clusters_table(conn, dry_run=False)
        
        # Delete requests
        print(f"\n[INFO] Deleting {len(ids_to_delete):,} requests...")
        deleted = delete_requests(conn, ids_to_delete, dry_run=args.dry_run)
        
        if args.dry_run:
            print("\n[DRY RUN] No data was actually deleted")
            print("[INFO] Run without --dry-run to perform the deletion")
        else:
            print(f"\n[SUCCESS] Deleted {deleted:,} requests")
            
            # Show new stats
            new_stats = get_stats(conn)
            print(f"\n[INFO] New statistics:")
            print(f"   Total requests: {new_stats['total']:,}")
            print(f"   With embeddings: {new_stats['with_embeddings']:,}")
            
            print("\n[INFO] Next steps:")
            print("   1. Run VACUUM FULL to reclaim storage:")
            print("      VACUUM FULL requests;")
            print("   2. Re-run clustering on remaining data:")
            print("      python scripts/cluster_vectors_hierarchical.py")
        
        conn.close()
        return 0
    
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
