"""
Test script for cluster prediction pipeline.

This script:
1. Prompts the user for text input
2. Uses the AI pipeline to predict the cluster
3. Retrieves all examples from the predicted cluster
4. Displays service type distribution using Counter
"""

import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ai.cluster_predictor import predict_cluster
from app.db.connection import get_conn


def get_cluster_examples(conn, parent_cluster_id, child_cluster_id):
    """
    Retrieve all examples from a specific cluster.
    
    Args:
        conn: Database connection
        parent_cluster_id: Top-level cluster ID
        child_cluster_id: Sub-cluster ID
    
    Returns:
        list: List of tuples (id, service_type, description, ref_number, created_at)
    """
    cursor = conn.cursor()
    
    query = """
        SELECT id, service_type, description, ref_number, created_at
        FROM requests
        WHERE top_cluster_id = %s AND sub_cluster_id = %s
        ORDER BY id
    """
    
    cursor.execute(query, (parent_cluster_id, child_cluster_id))
    results = cursor.fetchall()
    cursor.close()
    
    return results


def analyze_service_types(examples):
    """
    Analyze service types in examples using Counter.
    
    Args:
        examples: List of tuples (id, service_type, description, ref_number, created_at)
    
    Returns:
        Counter: Counter object with service_type counts
    """
    service_types = [service_type for _, service_type, _, _, _ in examples if service_type]
    return Counter(service_types)


def display_service_type_summary(examples, total_in_cluster):
    """
    Display service type summary from cluster examples.
    
    Args:
        examples: List of tuples (id, service_type, description, ref_number, created_at)
        total_in_cluster: Total number of examples in the cluster
    """
    if not examples:
        print("\n[INFO] No examples found in this cluster.")
        return
    
    # Count service types
    service_type_counter = analyze_service_types(examples)
    
    print(f"\n{'='*80}")
    print(f"Service Type Distribution (all {len(examples)} examples in cluster)")
    print(f"{'='*80}\n")
    
    if not service_type_counter:
        print("  No service types found in examples.")
        return
    
    # Sort by count (descending) for better readability
    sorted_types = service_type_counter.most_common()
    
    # Calculate percentages
    total_examples = len(examples)
    
    print(f"{'Service Type':<50} {'Count':<10} {'Percentage':<10}")
    print("-" * 80)
    
    for service_type, count in sorted_types:
        percentage = (count / total_examples) * 100 if total_examples > 0 else 0
        # Truncate long service type names
        display_type = service_type[:47] + "..." if len(service_type) > 50 else service_type
        print(f"{display_type:<50} {count:<10} {percentage:>6.1f}%")
    
    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  Total unique service types: {len(service_type_counter)}")
    print(f"  Most common: {sorted_types[0][0]} ({sorted_types[0][1]} occurrences)")
    print(f"{'='*80}\n")


def get_cluster_stats(conn, parent_cluster_id, child_cluster_id):
    """Get statistics about the cluster."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM requests
        WHERE top_cluster_id = %s AND sub_cluster_id = %s
    """, (parent_cluster_id, child_cluster_id))
    
    count = cursor.fetchone()[0]
    cursor.close()
    
    return count


def main():
    """Main function to test cluster prediction."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test cluster prediction pipeline with text input'
    )
    parser.add_argument(
        '--text',
        type=str,
        help='Text input to predict cluster for (if not provided, will prompt)'
    )
    parser.add_argument(
        '--similarity-threshold',
        type=float,
        default=0.15,
        help='Minimum similarity threshold (default: 0.15 = 15%%)'
    )
    
    args = parser.parse_args()
    
    # Get text input
    if args.text:
        text_input = args.text
    else:
        print("\n" + "="*80)
        print("Cluster Prediction Test")
        print("="*80)
        print("\nEnter text to predict its cluster:")
        print("(This text will be embedded and matched to the closest cluster)")
        print()
        text_input = input("> ").strip()
        
        if not text_input:
            print("[ERROR] No text input provided.")
            return 1
    
    print(f"\n[INFO] Processing text: '{text_input}'")
    print("[INFO] Generating embedding and finding closest cluster...")
    
    try:
        # Connect to database
        conn = get_conn()
        
        # Predict cluster
        result = predict_cluster(text_input, conn=conn)
        
        parent_id = result['parent_cluster_id']
        child_id = result['child_cluster_id']
        parent_sim = result['parent_similarity']
        child_sim = result['child_similarity']
        
        print(f"\n[SUCCESS] Cluster prediction complete!")
        print(f"  Parent Cluster ID: {parent_id}")
        print(f"  Child Cluster ID: {child_id}")
        print(f"  Parent Similarity: {parent_sim:.4f} ({parent_sim*100:.1f}%)")
        print(f"  Child Similarity: {child_sim:.4f} ({child_sim*100:.1f}%)")
        
        # Check similarity threshold
        if child_sim < args.similarity_threshold:
            print(f"\n{'='*80}")
            print("⚠️  Low Confidence Match")
            print(f"{'='*80}")
            print(f"\nCurrently no service requests match the provided description.")
            print(f"Similarity score ({child_sim*100:.1f}%) is below the threshold ({args.similarity_threshold*100:.1f}%).")
            print(f"\nThe closest match found:")
            print(f"  Parent Cluster ID: {parent_id} (similarity: {parent_sim*100:.1f}%)")
            print(f"  Child Cluster ID: {child_id} (similarity: {child_sim*100:.1f}%)")
            print(f"\nConsider refining your description for better matches.")
            print(f"{'='*80}\n")
            conn.close()
            return 0
        
        # Get cluster statistics
        total_count = get_cluster_stats(conn, parent_id, child_id)
        print(f"  Total examples in cluster: {total_count}")
        
        # Retrieve all examples from cluster
        print(f"\n[INFO] Retrieving all examples from cluster...")
        examples = get_cluster_examples(conn, parent_id, child_id)
        print(f"[INFO] Retrieved {len(examples)} examples")
        
        # Display service type summary
        display_service_type_summary(examples, total_count)
        
        conn.close()
        return 0
    
    except Exception as e:
        print(f"\n[ERROR] Failed to predict cluster: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
