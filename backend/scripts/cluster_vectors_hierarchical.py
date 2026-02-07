"""
Hierarchical clustering of vector embeddings using two-level MiniBatchKMeans.

This script performs hierarchical clustering:
- Level 1: Clusters all embeddings into ~25 top-level clusters
- Level 2: Clusters each top-level cluster into ~10 sub-clusters
- Result: ~250 total clusters with better granularity

Usage:
python scripts/cluster_vectors_hierarchical.py
python scripts/cluster_vectors_hierarchical.py --top-clusters 25 --sub-clusters 10
python scripts/cluster_vectors_hierarchical.py --top-clusters 30 --sub-clusters 8 --batch-size 10000
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
    """Parse vector from database - handles both string and array formats."""
    if embedding is None:
        return None
    
    # If it's already a list/array, convert directly
    if isinstance(embedding, (list, tuple)):
        return np.array(embedding, dtype=np.float32)
    
    # If it's a string (common with pgvector), parse it
    if isinstance(embedding, str):
        # Remove brackets and split by comma
        embedding = embedding.strip('[]')
        values = [float(x.strip()) for x in embedding.split(',')]
        return np.array(values, dtype=np.float32)
    
    # Try to convert directly (might work for some types)
    try:
        return np.array(embedding, dtype=np.float32)
    except (ValueError, TypeError):
        # Last resort: try parsing as string
        embedding_str = str(embedding).strip('[]')
        values = [float(x.strip()) for x in embedding_str.split(',')]
        return np.array(values, dtype=np.float32)


def fetch_all_embeddings(conn, batch_size=5000):
    """Fetch all embeddings and their IDs in batches.
    
    Uses smaller batch_size to reduce Supabase memory pressure during SELECT.
    The database streams results, so smaller batches = less memory per fetch.
    
    Memory optimization: Pre-allocates numpy array to avoid list overhead.
    """
    cursor = conn.cursor()
    
    # First, get the count to pre-allocate array
    cursor.execute("SELECT COUNT(*) FROM requests WHERE embedding IS NOT NULL")
    total_count = cursor.fetchone()[0]
    
    if total_count == 0:
        cursor.close()
        return [], np.array([])
    
    query = """
        SELECT id, embedding
        FROM requests
        WHERE embedding IS NOT NULL
        ORDER BY id
    """
    
    cursor.execute(query)
    
    all_ids = []
    # Pre-allocate numpy array for better memory efficiency
    # Shape: (total_count, 384) for 384-dimensional embeddings
    # Using float32 to save memory (4 bytes per value)
    embeddings_list = []
    valid_count = 0
    
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        
        for row_id, embedding in rows:
            parsed_embedding = parse_vector(embedding)
            if parsed_embedding is not None:
                all_ids.append(row_id)
                embeddings_list.append(parsed_embedding)
                valid_count += 1
            else:
                print(f"[WARN] Skipping row {row_id} - embedding is None")
    
    cursor.close()
    
    if not embeddings_list:
        return [], np.array([])
    
    # Convert to numpy array for clustering (more memory efficient than vstack)
    # This creates a contiguous array which is better for memory and performance
    embeddings_array = np.array(embeddings_list, dtype=np.float32)
    
    # Free the list from memory
    del embeddings_list
    
    return all_ids, embeddings_array


def perform_clustering(embeddings, n_clusters, random_state=42, verbose=True):
    """Perform MiniBatchKMeans clustering on embeddings."""
    try:
        from sklearn.cluster import MiniBatchKMeans
    except ImportError:
        print("[ERROR] scikit-learn not installed. Install with: pip install scikit-learn")
        raise
    
    if verbose:
        print(f"[INFO] Performing MiniBatchKMeans clustering with {n_clusters} clusters...")
        print(f"[INFO] Input shape: {embeddings.shape}")
    
    # Use MiniBatchKMeans for efficiency with large datasets
    # Reduced batch_size and n_init to save memory
    kmeans = MiniBatchKMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        batch_size=min(500, len(embeddings) // 20),  # Reduced from 1000 to save memory
        n_init=5,  # Reduced from 10 to save memory
        max_iter=100,
        verbose=1 if verbose else 0
    )
    
    cluster_labels = kmeans.fit_predict(embeddings)
    centroids = kmeans.cluster_centers_
    
    # Free memory
    del kmeans
    
    if verbose:
        print(f"[SUCCESS] Clustering complete!")
        print(f"[INFO] Cluster labels shape: {cluster_labels.shape}")
        print(f"[INFO] Centroids shape: {centroids.shape}")
    
    return cluster_labels, centroids


def perform_hierarchical_clustering(ids, embeddings, n_top_clusters=25, n_sub_clusters=10, random_state=42):
    """
    Perform two-level hierarchical clustering.
    
    Returns:
        - top_cluster_labels: Array of top-level cluster assignments
        - sub_cluster_labels: Array of sub-cluster assignments
        - top_centroids: Centroids for top-level clusters
        - sub_centroids_dict: Dict mapping top_cluster_id -> sub-cluster centroids
    """
    print(f"[INFO] Starting hierarchical clustering...")
    print(f"[INFO] Level 1: {n_top_clusters} top-level clusters")
    print(f"[INFO] Level 2: {n_sub_clusters} sub-clusters per top cluster")
    print(f"[INFO] Expected total clusters: {n_top_clusters * n_sub_clusters}")
    
    # Level 1: Cluster all embeddings into top-level clusters
    print("\n" + "="*60)
    print("[LEVEL 1] Clustering into top-level clusters...")
    print("="*60)
    top_cluster_labels, top_centroids = perform_clustering(
        embeddings,
        n_clusters=n_top_clusters,
        random_state=random_state,
        verbose=True
    )
    
    # Level 2: Cluster each top-level cluster into sub-clusters
    print("\n" + "="*60)
    print("[LEVEL 2] Clustering each top-level cluster into sub-clusters...")
    print("="*60)
    
    sub_cluster_labels = np.full(len(ids), -1, dtype=np.int32)  # Initialize with -1
    sub_centroids_dict = {}
    
    unique_top_clusters = np.unique(top_cluster_labels)
    
    for top_cluster_id in unique_top_clusters:
        # Get indices of all points in this top cluster
        top_cluster_mask = top_cluster_labels == top_cluster_id
        top_cluster_indices = np.where(top_cluster_mask)[0]
        top_cluster_embeddings = embeddings[top_cluster_mask]
        
        if len(top_cluster_embeddings) < n_sub_clusters:
            # If cluster is too small, assign all to sub-cluster 0
            print(f"[WARN] Top cluster {top_cluster_id} has only {len(top_cluster_embeddings)} points, "
                  f"skipping sub-clustering (all assigned to sub-cluster 0)")
            sub_cluster_labels[top_cluster_indices] = 0
            # Use the mean as the centroid
            sub_centroids_dict[top_cluster_id] = [top_cluster_embeddings.mean(axis=0)]
            # Free memory
            del top_cluster_embeddings
            continue
        
        print(f"[INFO] Clustering top cluster {top_cluster_id} ({len(top_cluster_embeddings)} points)...")
        
        # Cluster this top cluster into sub-clusters
        sub_labels, sub_centroids = perform_clustering(
            top_cluster_embeddings,
            n_clusters=n_sub_clusters,
            random_state=random_state + int(top_cluster_id),  # Different seed per top cluster
            verbose=False
        )
        
        # Store sub-cluster labels (mapped to global indices)
        sub_cluster_labels[top_cluster_indices] = sub_labels
        sub_centroids_dict[top_cluster_id] = sub_centroids
        
        # Free memory after processing each top cluster
        del top_cluster_embeddings, sub_labels
    
    print("\n[SUCCESS] Hierarchical clustering complete!")
    
    return top_cluster_labels, sub_cluster_labels, top_centroids, sub_centroids_dict


def update_cluster_assignments(conn, ids, top_cluster_labels, sub_cluster_labels):
    """Update top_cluster_id and sub_cluster_id for all requests."""
    if len(ids) != len(top_cluster_labels) or len(ids) != len(sub_cluster_labels):
        raise ValueError("IDs and cluster_labels must have the same length")
    
    cursor = conn.cursor()
    
    # Prepare data for batch update
    update_data = [
        (int(top_cluster_id), int(sub_cluster_id), row_id)
        for row_id, top_cluster_id, sub_cluster_id in zip(ids, top_cluster_labels, sub_cluster_labels)
    ]
    
    # Use batch update for efficiency
    # Reduced page_size from 5000 to 1000 to reduce Supabase memory pressure
    # Smaller batches = less database memory per transaction
    update_query = """
        UPDATE requests
        SET top_cluster_id = %s, sub_cluster_id = %s
        WHERE id = %s
    """
    
    print(f"[INFO] Updating {len(update_data)} cluster assignments (batch size: 1000)...")
    execute_batch(cursor, update_query, update_data, page_size=1000)
    conn.commit()
    cursor.close()
    
    print(f"[SUCCESS] Updated cluster assignments for {len(update_data)} requests")


def update_cluster_metadata(conn, top_centroids, sub_centroids_dict, top_cluster_labels, sub_cluster_labels, store_centroids=True):
    """
    Create or update cluster metadata in the clusters table.
    
    Args:
        store_centroids: If False, don't store centroids to save storage (can compute on-demand).
                        Default True for performance, but set False if storage is tight.
    """
    cursor = conn.cursor()
    
    # Clear existing clusters
    cursor.execute("DELETE FROM clusters")
    
    # Calculate cluster sizes
    unique_top_clusters, top_counts = np.unique(top_cluster_labels, return_counts=True)
    top_cluster_sizes = dict(zip(unique_top_clusters, top_counts))
    
    cluster_data = []
    
    # Insert top-level clusters (level=1, parent_cluster_id=NULL)
    for top_cluster_id in unique_top_clusters:
        centroid = top_centroids[int(top_cluster_id)].tolist() if store_centroids else None
        size = int(top_cluster_sizes[top_cluster_id])
        cluster_data.append((int(top_cluster_id), None, 1, centroid, size))
    
    # Insert sub-clusters (level=2, parent_cluster_id=top_cluster_id)
    # Only store centroids if store_centroids=True (for storage optimization)
    for top_cluster_id, sub_centroids in sub_centroids_dict.items():
        # Get sub-cluster sizes for this top cluster
        # Memory efficient: only create mask for current top cluster
        top_mask = top_cluster_labels == top_cluster_id
        sub_labels_for_top = sub_cluster_labels[top_mask]
        unique_subs, sub_counts = np.unique(sub_labels_for_top, return_counts=True)
        sub_cluster_sizes = dict(zip(unique_subs, sub_counts))
        # Free mask after use
        del top_mask, sub_labels_for_top
        
        for sub_cluster_id, sub_centroid in enumerate(sub_centroids):
            size = int(sub_cluster_sizes.get(sub_cluster_id, 0))
            centroid_value = sub_centroid.tolist() if store_centroids else None
            cluster_data.append((
                int(sub_cluster_id),
                int(top_cluster_id),
                2,
                centroid_value,
                size
            ))
    
    insert_query = """
        INSERT INTO clusters (cluster_id, parent_cluster_id, level, centroid, size, updated_at)
        VALUES (%s, %s, %s, %s::vector, %s, NOW())
        ON CONFLICT (cluster_id, parent_cluster_id, level)
        DO UPDATE SET 
            centroid = EXCLUDED.centroid::vector,
            size = EXCLUDED.size,
            updated_at = NOW()
    """
    
    if store_centroids:
        print(f"[INFO] Updating metadata for {len(cluster_data)} clusters (with centroids)...")
    else:
        print(f"[INFO] Updating metadata for {len(cluster_data)} clusters (without centroids to save storage)...")
    execute_batch(cursor, insert_query, cluster_data, page_size=100)
    conn.commit()
    cursor.close()
    
    print(f"[SUCCESS] Updated cluster metadata")


def get_clustering_stats(conn):
    """Get statistics about clustering."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE embedding IS NOT NULL")
    total_with_embeddings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE top_cluster_id IS NOT NULL")
    total_clustered = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM clusters WHERE level = 1")
    num_top_clusters = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM clusters WHERE level = 2")
    num_sub_clusters = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT 
            AVG(size) as avg_size,
            MIN(size) as min_size,
            MAX(size) as max_size
        FROM clusters
        WHERE level = 1
    """)
    top_stats = cursor.fetchone()
    
    cursor.execute("""
        SELECT 
            AVG(size) as avg_size,
            MIN(size) as min_size,
            MAX(size) as max_size
        FROM clusters
        WHERE level = 2
    """)
    sub_stats = cursor.fetchone()
    
    cursor.close()
    
    return {
        'total_with_embeddings': total_with_embeddings,
        'total_clustered': total_clustered,
        'num_top_clusters': num_top_clusters,
        'num_sub_clusters': num_sub_clusters,
        'top_avg_size': top_stats[0] if top_stats[0] else 0,
        'top_min_size': top_stats[1] if top_stats[1] else 0,
        'top_max_size': top_stats[2] if top_stats[2] else 0,
        'sub_avg_size': sub_stats[0] if sub_stats[0] else 0,
        'sub_min_size': sub_stats[1] if sub_stats[1] else 0,
        'sub_max_size': sub_stats[2] if sub_stats[2] else 0,
    }


def main():
    """Main function to perform hierarchical clustering."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hierarchical clustering of vector embeddings')
    parser.add_argument('--top-clusters', type=int, default=25,
                       help='Number of top-level clusters (default: 25)')
    parser.add_argument('--sub-clusters', type=int, default=10,
                       help='Number of sub-clusters per top cluster (default: 10)')
    parser.add_argument('--batch-size', type=int, default=5000,
                       help='Batch size for fetching embeddings (default: 5000, reduced for Supabase memory efficiency)')
    parser.add_argument('--random-state', type=int, default=42,
                       help='Random state for reproducibility (default: 42)')
    parser.add_argument('--no-centroids', action='store_true', default=False,
                       help='Do not store centroids in database (saves storage, but slower queries)')
    
    args = parser.parse_args()
    
    try:
        print("[INFO] Connecting to database...")
        conn = get_conn()
        print("[SUCCESS] Connected to database")
        
        # Get initial statistics
        stats = get_clustering_stats(conn)
        print(f"[INFO] Total requests with embeddings: {stats['total_with_embeddings']}")
        print(f"[INFO] Currently clustered: {stats['total_clustered']}")
        
        if stats['total_with_embeddings'] == 0:
            print("[ERROR] No requests with embeddings found. Run vector_embedding.py first.")
            conn.close()
            return 1
        
        # Fetch all embeddings
        print(f"\n[INFO] Fetching embeddings (batch_size={args.batch_size})...")
        ids, embeddings = fetch_all_embeddings(conn, batch_size=args.batch_size)
        
        if len(ids) == 0:
            print("[ERROR] No embeddings found to cluster.")
            conn.close()
            return 1
        
        print(f"[SUCCESS] Fetched {len(ids)} embeddings")
        
        # Estimate memory usage
        import sys
        embeddings_mb = embeddings.nbytes / (1024 * 1024)
        print(f"[INFO] Estimated memory usage: ~{embeddings_mb:.1f} MB for embeddings")
        print(f"[INFO] Total estimated memory: ~{embeddings_mb * 1.5:.1f} MB (including overhead)")
        
        # Perform hierarchical clustering
        top_cluster_labels, sub_cluster_labels, top_centroids, sub_centroids_dict = perform_hierarchical_clustering(
            ids,
            embeddings,
            n_top_clusters=args.top_clusters,
            n_sub_clusters=args.sub_clusters,
            random_state=args.random_state
        )
        
        # Free embeddings from memory after clustering (keep for updates)
        # Note: We keep embeddings in memory for now as it's needed for metadata calculation
        
        # Update cluster assignments
        print("\n[INFO] Updating database with cluster assignments...")
        update_cluster_assignments(conn, ids, top_cluster_labels, sub_cluster_labels)
        
        # Free memory immediately after updates (embeddings no longer needed)
        # This frees ~100-200 MB depending on dataset size
        del embeddings
        import gc
        gc.collect()  # Force garbage collection to free memory immediately
        
        # Update cluster metadata
        update_cluster_metadata(conn, top_centroids, sub_centroids_dict, top_cluster_labels, sub_cluster_labels,
                               store_centroids=not args.no_centroids)
        
        # Get final statistics
        final_stats = get_clustering_stats(conn)
        print("\n" + "="*60)
        print("[SUCCESS] Hierarchical clustering complete!")
        print("="*60)
        print(f"[INFO] Final statistics:")
        print(f"   Total clustered: {final_stats['total_clustered']}")
        print(f"   Top-level clusters: {final_stats['num_top_clusters']}")
        print(f"   Sub-clusters: {final_stats['num_sub_clusters']}")
        print(f"   Total clusters: {final_stats['num_top_clusters'] + final_stats['num_sub_clusters']}")
        print(f"\n   Top-level cluster sizes:")
        print(f"      Average: {final_stats['top_avg_size']:.1f}")
        print(f"      Min: {final_stats['top_min_size']}")
        print(f"      Max: {final_stats['top_max_size']}")
        print(f"\n   Sub-cluster sizes:")
        print(f"      Average: {final_stats['sub_avg_size']:.1f}")
        print(f"      Min: {final_stats['sub_min_size']}")
        print(f"      Max: {final_stats['sub_max_size']}")
        
        conn.close()
        return 0
    
    except Exception as e:
        print(f"[ERROR] Failed to perform clustering: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
