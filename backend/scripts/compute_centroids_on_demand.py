"""
Compute cluster centroids on-demand from embeddings.

Use this script if you've removed centroids from storage to save space,
but need to compute them for visualization or analysis.

Usage:
python scripts/compute_centroids_on_demand.py  # Compute all missing centroids
python scripts/compute_centroids_on_demand.py --level 1  # Only top-level
python scripts/compute_centroids_on_demand.py --level 2  # Only sub-clusters
python scripts/compute_centroids_on_demand.py --top-cluster 5  # Specific top cluster
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import execute_batch
import numpy as np
from app.db.connection import get_conn


def parse_vector(embedding):
    """Parse vector from database."""
    if embedding is None:
        return None
    
    if isinstance(embedding, (list, tuple)):
        return np.array(embedding, dtype=np.float32)
    
    if isinstance(embedding, str):
        embedding = embedding.strip('[]')
        values = [float(x.strip()) for x in embedding.split(',')]
        return np.array(values, dtype=np.float32)
    
    try:
        return np.array(embedding, dtype=np.float32)
    except (ValueError, TypeError):
        embedding_str = str(embedding).strip('[]')
        values = [float(x.strip()) for x in embedding_str.split(',')]
        return np.array(values, dtype=np.float32)


def compute_top_cluster_centroid(conn, top_cluster_id):
    """Compute centroid for a top-level cluster from embeddings."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT embedding
        FROM requests
        WHERE top_cluster_id = %s AND embedding IS NOT NULL
    """, (top_cluster_id,))
    
    rows = cursor.fetchall()
    if not rows:
        cursor.close()
        return None
    
    embeddings = [parse_vector(row[0]) for row in rows]
    embeddings_array = np.vstack(embeddings)
    centroid = embeddings_array.mean(axis=0)
    
    cursor.close()
    return centroid.tolist()


def compute_sub_cluster_centroid(conn, top_cluster_id, sub_cluster_id):
    """Compute centroid for a sub-cluster from embeddings."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT embedding
        FROM requests
        WHERE top_cluster_id = %s AND sub_cluster_id = %s AND embedding IS NOT NULL
    """, (top_cluster_id, sub_cluster_id))
    
    rows = cursor.fetchall()
    if not rows:
        cursor.close()
        return None
    
    embeddings = [parse_vector(row[0]) for row in rows]
    embeddings_array = np.vstack(embeddings)
    centroid = embeddings_array.mean(axis=0)
    
    cursor.close()
    return centroid.tolist()


def update_centroids(conn, level=None, top_cluster_id=None):
    """Update centroids in the clusters table."""
    cursor = conn.cursor()
    
    if level == 1:
        # Update top-level clusters
        cursor.execute("SELECT DISTINCT cluster_id FROM clusters WHERE level = 1")
        cluster_ids = [row[0] for row in cursor.fetchall()]
        
        updates = []
        for cluster_id in cluster_ids:
            centroid = compute_top_cluster_centroid(conn, cluster_id)
            if centroid:
                updates.append((centroid, cluster_id))
        
        if updates:
            update_query = """
                UPDATE clusters
                SET centroid = %s::vector, updated_at = NOW()
                WHERE cluster_id = %s AND level = 1
            """
            execute_batch(cursor, update_query, updates, page_size=100)
            conn.commit()
            print(f"[SUCCESS] Updated {len(updates)} top-level cluster centroids")
        
    elif level == 2:
        # Update sub-clusters
        if top_cluster_id is not None:
            cursor.execute("""
                SELECT DISTINCT cluster_id 
                FROM clusters 
                WHERE level = 2 AND parent_cluster_id = %s
            """, (top_cluster_id,))
        else:
            cursor.execute("SELECT DISTINCT parent_cluster_id, cluster_id FROM clusters WHERE level = 2")
        
        if top_cluster_id is not None:
            cluster_pairs = [(top_cluster_id, row[0]) for row in cursor.fetchall()]
        else:
            cluster_pairs = cursor.fetchall()
        
        updates = []
        for parent_id, cluster_id in cluster_pairs:
            centroid = compute_sub_cluster_centroid(conn, parent_id, cluster_id)
            if centroid:
                updates.append((centroid, cluster_id, parent_id))
        
        if updates:
            update_query = """
                UPDATE clusters
                SET centroid = %s::vector, updated_at = NOW()
                WHERE cluster_id = %s AND parent_cluster_id = %s AND level = 2
            """
            execute_batch(cursor, update_query, updates, page_size=100)
            conn.commit()
            print(f"[SUCCESS] Updated {len(updates)} sub-cluster centroids")
    
    else:
        # Update all clusters
        # Top-level first
        cursor.execute("SELECT DISTINCT cluster_id FROM clusters WHERE level = 1")
        top_cluster_ids = [row[0] for row in cursor.fetchall()]
        
        top_updates = []
        for cluster_id in top_cluster_ids:
            centroid = compute_top_cluster_centroid(conn, cluster_id)
            if centroid:
                top_updates.append((centroid, cluster_id))
        
        if top_updates:
            update_query = """
                UPDATE clusters
                SET centroid = %s::vector, updated_at = NOW()
                WHERE cluster_id = %s AND level = 1
            """
            execute_batch(cursor, update_query, top_updates, page_size=100)
            print(f"[INFO] Updated {len(top_updates)} top-level cluster centroids")
        
        # Then sub-clusters
        cursor.execute("SELECT DISTINCT parent_cluster_id, cluster_id FROM clusters WHERE level = 2")
        sub_cluster_pairs = cursor.fetchall()
        
        sub_updates = []
        for parent_id, cluster_id in sub_cluster_pairs:
            centroid = compute_sub_cluster_centroid(conn, parent_id, cluster_id)
            if centroid:
                sub_updates.append((centroid, cluster_id, parent_id))
        
        if sub_updates:
            update_query = """
                UPDATE clusters
                SET centroid = %s::vector, updated_at = NOW()
                WHERE cluster_id = %s AND parent_cluster_id = %s AND level = 2
            """
            execute_batch(cursor, update_query, sub_updates, page_size=100)
            print(f"[INFO] Updated {len(sub_updates)} sub-cluster centroids")
        
        conn.commit()
        print(f"[SUCCESS] Updated {len(top_updates)} top-level and {len(sub_updates)} sub-cluster centroids")
    
    cursor.close()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Compute cluster centroids on-demand from embeddings')
    parser.add_argument('--level', type=int, choices=[1, 2],
                       help='Compute centroids for specific level (1=top, 2=sub)')
    parser.add_argument('--top-cluster', type=int,
                       help='Compute centroids only for sub-clusters of this top cluster')
    
    args = parser.parse_args()
    
    try:
        print("[INFO] Connecting to database...")
        conn = get_conn()
        print("[SUCCESS] Connected to database")
        
        if args.level == 2 and args.top_cluster:
            print(f"[INFO] Computing centroids for sub-clusters of top cluster {args.top_cluster}...")
            update_centroids(conn, level=2, top_cluster_id=args.top_cluster)
        elif args.level:
            print(f"[INFO] Computing centroids for level {args.level} clusters...")
            update_centroids(conn, level=args.level)
        else:
            print("[INFO] Computing centroids for all clusters...")
            update_centroids(conn)
        
        conn.close()
        return 0
    
    except Exception as e:
        print(f"[ERROR] Failed to compute centroids: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
