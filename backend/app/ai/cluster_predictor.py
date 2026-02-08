"""
Cluster prediction pipeline for text input.

This module provides functionality to:
1. Generate embeddings for user text input
2. Find the closest parent (top-level) cluster
3. Find the closest child (sub-level) cluster within that parent
4. Return cluster indices for retrieval
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.connection import get_conn


def get_embedding_model():
    """Load the embedding model (lazy loading to avoid loading if not needed)."""
    try:
        from sentence_transformers import SentenceTransformer
        # Using the same model as vector_embedding.py for consistency
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model
    except ImportError:
        raise ImportError(
            "sentence-transformers not installed. Install with: pip install sentence-transformers"
        )


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


def get_all_cluster_centroids(conn):
    """
    Fetch all cluster centroids from the database.
    
    Returns:
        tuple: (top_clusters_dict, sub_clusters_dict)
            - top_clusters_dict: {cluster_id: centroid_vector}
            - sub_clusters_dict: {(parent_id, cluster_id): centroid_vector}
    """
    cursor = conn.cursor()
    
    # Fetch top-level clusters (level=1)
    cursor.execute("""
        SELECT cluster_id, centroid
        FROM clusters
        WHERE level = 1 AND centroid IS NOT NULL
        ORDER BY cluster_id
    """)
    top_clusters = {}
    for cluster_id, centroid in cursor.fetchall():
        parsed_centroid = parse_vector(centroid)
        if parsed_centroid is not None:
            top_clusters[int(cluster_id)] = parsed_centroid
    
    # Fetch sub-clusters (level=2)
    cursor.execute("""
        SELECT parent_cluster_id, cluster_id, centroid
        FROM clusters
        WHERE level = 2 AND centroid IS NOT NULL
        ORDER BY parent_cluster_id, cluster_id
    """)
    sub_clusters = {}
    for parent_id, cluster_id, centroid in cursor.fetchall():
        parsed_centroid = parse_vector(centroid)
        if parsed_centroid is not None:
            sub_clusters[(int(parent_id), int(cluster_id))] = parsed_centroid
    
    cursor.close()
    
    return top_clusters, sub_clusters


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    vec1_norm = np.linalg.norm(vec1)
    vec2_norm = np.linalg.norm(vec2)
    
    if vec1_norm == 0 or vec2_norm == 0:
        return 0.0
    
    return np.dot(vec1, vec2) / (vec1_norm * vec2_norm)


def find_closest_cluster(query_embedding, cluster_centroids):
    """
    Find the closest cluster to the query embedding using cosine similarity.
    
    Args:
        query_embedding: numpy array of the query embedding
        cluster_centroids: dict mapping cluster_id -> centroid vector
    
    Returns:
        tuple: (closest_cluster_id, similarity_score)
    """
    if not cluster_centroids:
        return None, 0.0
    
    best_cluster_id = None
    best_similarity = -1.0
    
    for cluster_id, centroid in cluster_centroids.items():
        similarity = cosine_similarity(query_embedding, centroid)
        if similarity > best_similarity:
            best_similarity = similarity
            best_cluster_id = cluster_id
    
    return best_cluster_id, best_similarity


def find_closest_clusters_sorted(query_embedding, cluster_centroids, exclude_ids=None):
    """
    Find all clusters sorted by similarity (descending).
    
    Args:
        query_embedding: numpy array of the query embedding
        cluster_centroids: dict mapping cluster_id -> centroid vector
        exclude_ids: set of cluster IDs to exclude from results
    
    Returns:
        list: List of tuples (cluster_id, similarity_score) sorted by similarity descending
    """
    if not cluster_centroids:
        return []
    
    exclude_ids = exclude_ids or set()
    
    similarities = []
    for cluster_id, centroid in cluster_centroids.items():
        if cluster_id not in exclude_ids:
            similarity = cosine_similarity(query_embedding, centroid)
            similarities.append((cluster_id, similarity))
    
    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    return similarities


def cluster_has_examples(conn, parent_cluster_id, child_cluster_id):
    """
    Check if a cluster has any examples.
    
    Args:
        conn: Database connection
        parent_cluster_id: Top-level cluster ID
        child_cluster_id: Sub-cluster ID
    
    Returns:
        bool: True if cluster has examples, False otherwise
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM requests
        WHERE top_cluster_id = %s AND sub_cluster_id = %s
    """, (parent_cluster_id, child_cluster_id))
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0


def predict_cluster(text_input, conn=None, model=None):
    """
    Predict the cluster for a given text input.
    
    Args:
        text_input: String text input from user
        conn: Database connection (optional, will create if not provided)
        model: SentenceTransformer model (optional, will load if not provided)
    
    Returns:
        dict: {
            'parent_cluster_id': int,
            'child_cluster_id': int,
            'parent_similarity': float,
            'child_similarity': float,
            'text_embedding': numpy array
        }
    """
    # Load model if not provided
    if model is None:
        model = get_embedding_model()
    
    # Generate embedding for input text
    query_embedding = model.encode(text_input, show_progress_bar=False, convert_to_numpy=True)
    query_embedding = query_embedding.astype(np.float32)
    
    # Get database connection if not provided
    should_close_conn = False
    if conn is None:
        conn = get_conn()
        should_close_conn = True
    
    try:
        # Get all cluster centroids
        top_clusters, sub_clusters = get_all_cluster_centroids(conn)
        
        if not top_clusters:
            raise ValueError("No top-level clusters found in database. Run clustering first.")
        
        # Find closest top-level cluster
        parent_cluster_id, parent_similarity = find_closest_cluster(query_embedding, top_clusters)
        
        if parent_cluster_id is None:
            raise ValueError("Could not find a matching parent cluster.")
        
        # Find closest sub-cluster within the parent cluster
        # Filter sub_clusters to only those with matching parent_id
        parent_sub_clusters = {
            (p_id, c_id): centroid
            for (p_id, c_id), centroid in sub_clusters.items()
            if p_id == parent_cluster_id
        }
        
        child_cluster_id = None
        child_similarity = 0.0
        
        if parent_sub_clusters:
            # Find closest sub-cluster
            # We need to extract just the cluster_id from the tuple key
            sub_clusters_simple = {
                c_id: centroid
                for (p_id, c_id), centroid in parent_sub_clusters.items()
            }
            child_cluster_id, child_similarity = find_closest_cluster(query_embedding, sub_clusters_simple)
        else:
            # If no sub-clusters exist for this parent, default to 0
            child_cluster_id = 0
            child_similarity = 0.0
        
        # Check if the predicted cluster has examples, if not find the next closest non-empty cluster
        if not cluster_has_examples(conn, parent_cluster_id, child_cluster_id):
            # Try to find a non-empty child cluster within the same parent
            if parent_sub_clusters:
                sub_clusters_simple = {
                    c_id: centroid
                    for (p_id, c_id), centroid in parent_sub_clusters.items()
                }
                sorted_child_clusters = find_closest_clusters_sorted(
                    query_embedding, 
                    sub_clusters_simple,
                    exclude_ids={child_cluster_id} if child_cluster_id is not None else None
                )
                
                # Try each child cluster until we find one with examples
                found_non_empty = False
                for candidate_child_id, candidate_similarity in sorted_child_clusters:
                    if cluster_has_examples(conn, parent_cluster_id, candidate_child_id):
                        child_cluster_id = candidate_child_id
                        child_similarity = candidate_similarity
                        found_non_empty = True
                        break
                
                # If no child clusters in this parent have examples, try other parents
                if not found_non_empty:
                    sorted_parent_clusters = find_closest_clusters_sorted(
                        query_embedding,
                        top_clusters,
                        exclude_ids={parent_cluster_id}
                    )
                    
                    # Try each parent cluster until we find one with a non-empty child cluster
                    for candidate_parent_id, candidate_parent_sim in sorted_parent_clusters:
                        # Get child clusters for this parent
                        candidate_parent_sub_clusters = {
                            (p_id, c_id): centroid
                            for (p_id, c_id), centroid in sub_clusters.items()
                            if p_id == candidate_parent_id
                        }
                        
                        if candidate_parent_sub_clusters:
                            candidate_sub_simple = {
                                c_id: centroid
                                for (p_id, c_id), centroid in candidate_parent_sub_clusters.items()
                            }
                            sorted_candidate_children = find_closest_clusters_sorted(
                                query_embedding,
                                candidate_sub_simple
                            )
                            
                            # Try each child cluster in this parent
                            for candidate_child_id, candidate_child_sim in sorted_candidate_children:
                                if cluster_has_examples(conn, candidate_parent_id, candidate_child_id):
                                    parent_cluster_id = candidate_parent_id
                                    parent_similarity = candidate_parent_sim
                                    child_cluster_id = candidate_child_id
                                    child_similarity = candidate_child_sim
                                    found_non_empty = True
                                    break
                            
                            if found_non_empty:
                                break
                    
                    if not found_non_empty:
                        raise ValueError("No non-empty clusters found in database.")
            else:
                # No sub-clusters for this parent, try other parents
                sorted_parent_clusters = find_closest_clusters_sorted(
                    query_embedding,
                    top_clusters,
                    exclude_ids={parent_cluster_id}
                )
                
                found_non_empty = False
                for candidate_parent_id, candidate_parent_sim in sorted_parent_clusters:
                    # Get child clusters for this parent
                    candidate_parent_sub_clusters = {
                        (p_id, c_id): centroid
                        for (p_id, c_id), centroid in sub_clusters.items()
                        if p_id == candidate_parent_id
                    }
                    
                    if candidate_parent_sub_clusters:
                        candidate_sub_simple = {
                            c_id: centroid
                            for (p_id, c_id), centroid in candidate_parent_sub_clusters.items()
                        }
                        sorted_candidate_children = find_closest_clusters_sorted(
                            query_embedding,
                            candidate_sub_simple
                        )
                        
                        # Try each child cluster in this parent
                        for candidate_child_id, candidate_child_sim in sorted_candidate_children:
                            if cluster_has_examples(conn, candidate_parent_id, candidate_child_id):
                                parent_cluster_id = candidate_parent_id
                                parent_similarity = candidate_parent_sim
                                child_cluster_id = candidate_child_id
                                child_similarity = candidate_child_sim
                                found_non_empty = True
                                break
                        
                        if found_non_empty:
                            break
                
                if not found_non_empty:
                    raise ValueError("No non-empty clusters found in database.")
        
        result = {
            'parent_cluster_id': parent_cluster_id,
            'child_cluster_id': child_cluster_id if child_cluster_id is not None else 0,
            'parent_similarity': float(parent_similarity),
            'child_similarity': float(child_similarity),
            'text_embedding': query_embedding
        }
        
        return result
    
    finally:
        if should_close_conn:
            conn.close()


if __name__ == "__main__":
    # Test the prediction function
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python cluster_predictor.py <text_input>")
        sys.exit(1)
    
    text_input = " ".join(sys.argv[1:])
    
    print(f"[INFO] Predicting cluster for: '{text_input}'")
    
    try:
        result = predict_cluster(text_input)
        print(f"\n[SUCCESS] Cluster prediction:")
        print(f"   Parent Cluster ID: {result['parent_cluster_id']}")
        print(f"   Child Cluster ID: {result['child_cluster_id']}")
        print(f"   Parent Similarity: {result['parent_similarity']:.4f}")
        print(f"   Child Similarity: {result['child_similarity']:.4f}")
    except Exception as e:
        print(f"[ERROR] Failed to predict cluster: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
