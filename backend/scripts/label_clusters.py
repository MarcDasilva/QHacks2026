"""
Script to generate and display labels for clusters.

This script:
1. Analyzes requests in each cluster
2. Generates labels using:
   - Gemini LLM for intelligent, concise labels (recommended, --use-llm)
   - Or fallback to simple service type extraction (default)
3. Outputs CSV format with cluster labels

Usage:
python scripts/label_clusters.py
python scripts/label_clusters.py --min-examples 3  # Only show clusters with at least 3 examples
python scripts/label_clusters.py --use-llm          # Use Gemini LLM (requires GEMINI_API_KEY)
python scripts/label_clusters.py --output labels.csv  # Save to file
python scripts/label_clusters.py --use-llm --batch-size 10  # Batch clusters to save credits
"""

import sys
from pathlib import Path
from collections import Counter
import re
import csv
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.db.connection import get_conn


def get_cluster_requests(conn, parent_cluster_id, child_cluster_id):
    """
    Get all requests in a specific cluster.
    
    Args:
        conn: Database connection
        parent_cluster_id: Top-level cluster ID (None for top-level clusters)
        child_cluster_id: Sub-cluster ID (None for top-level clusters)
    
    Returns:
        list: List of tuples (service_type, description)
    """
    cursor = conn.cursor()
    
    if parent_cluster_id is None:
        # Top-level cluster - get all requests in this top cluster
        query = """
            SELECT service_type, description
            FROM requests
            WHERE top_cluster_id = %s
            AND service_type IS NOT NULL
        """
        cursor.execute(query, (child_cluster_id,))
    else:
        # Sub-cluster - get requests in this specific sub-cluster
        query = """
            SELECT service_type, description
            FROM requests
            WHERE top_cluster_id = %s AND sub_cluster_id = %s
            AND service_type IS NOT NULL
        """
        cursor.execute(query, (parent_cluster_id, child_cluster_id))
    
    results = cursor.fetchall()
    cursor.close()
    
    return results


def extract_keywords(descriptions, top_n=5):
    """
    Extract most common keywords from descriptions.
    
    Args:
        descriptions: List of description strings
        top_n: Number of top keywords to return
    
    Returns:
        list: List of (keyword, count) tuples
    """
    if not descriptions:
        return []
    
    # Combine all descriptions
    all_text = ' '.join([desc.lower() for desc in descriptions if desc])
    
    # Remove common stopwords and short words
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all',
        'each', 'every', 'some', 'any', 'no', 'not', 'only', 'just',
        'more', 'most', 'very', 'too', 'so', 'than', 'then', 'now'
    }
    
    # Extract words (alphanumeric sequences)
    words = re.findall(r'\b[a-z]{3,}\b', all_text)
    
    # Filter out stopwords and count
    keywords = [word for word in words if word not in stopwords]
    
    # Count keywords
    keyword_counter = Counter(keywords)
    
    # Return top N keywords
    return keyword_counter.most_common(top_n)


def shorten_service_type(service_type, max_words=3):
    """
    Shorten a service type to a few key words.
    Never ends with connecting words like "and", "or", "/".
    
    Args:
        service_type: Full service type string
        max_words: Maximum number of words to keep
    
    Returns:
        str: Shortened service type
    """
    if not service_type:
        return ""
    
    # Split into words
    words = service_type.split()
    
    # If already short enough, return as is (but clean up trailing connectors)
    if len(words) <= max_words:
        # Remove trailing connecting words
        connecting_words = ['and', 'or', '/', '-', '&']
        while words and words[-1].lower().rstrip('.,;:') in connecting_words:
            words.pop()
        return ' '.join(words) if words else service_type
    
    # Take first few words, but stop before connecting words
    connecting_words = ['and', 'or', '/', '-', '&']
    result_words = []
    
    # Try to take meaningful words (skip common prefixes)
    skip_prefixes = ['service', 'request', 'type', 'for', 'the', 'a', 'an']
    meaningful_words = [w for w in words if w.lower() not in skip_prefixes]
    
    if len(meaningful_words) >= max_words:
        # Take up to max_words, but stop before connecting words
        for word in meaningful_words[:max_words]:
            if word.lower().rstrip('.,;:') not in connecting_words:
                result_words.append(word)
            else:
                break  # Stop before connecting word
    else:
        # Fall back to first words, but stop before connecting words
        for word in words[:max_words]:
            if word.lower().rstrip('.,;:') not in connecting_words:
                result_words.append(word)
            else:
                break  # Stop before connecting word
    
    return ' '.join(result_words) if result_words else service_type


def generate_labels_batch_with_gemini(cluster_data_list, model="gemini-2.5-flash"):
    """
    Generate labels for multiple clusters in a single batch request to save credits.
    
    Args:
        cluster_data_list: List of tuples (service_types, descriptions, parent_id, cluster_id)
        model: Gemini model to use (gemini-2.5-flash)
    
    Returns:
        dict: Mapping of (parent_id, cluster_id) -> label
    """
    # Try new package first, fall back to old package
    try:
        import google.genai as genai_new
        use_new_api = True
    except ImportError:
        try:
            import google.generativeai as genai_old
            use_new_api = False
        except ImportError:
            raise ImportError(
                "Neither google-genai nor google-generativeai package found. "
                "Install with: pip install google-genai"
            )
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    if use_new_api:
        client_new = genai_new.Client(api_key=api_key)
    else:
        genai_old.configure(api_key=api_key)
        client_old = genai_old
    
    # Prepare batch prompt with all clusters in a clear format
    # Keep track of cluster keys in order (parent_id, cluster_id)
    cluster_entries = []
    cluster_key_order = []  # Track the order of cluster keys (parent_id, cluster_id)
    
    for service_types, descriptions, parent_id, cluster_id in cluster_data_list:
        if not service_types:
            # Empty cluster - skip from LLM request, will be labeled as "EMPTY"
            continue
            
        service_type_counter = Counter(service_types)
        top_types = service_type_counter.most_common(3)
        top_types_str = ", ".join([f"{name} ({count})" for name, count in top_types])
        
        # Format: Cluster identifier (parent.cluster) and service types
        cluster_key = (parent_id, cluster_id)
        cluster_identifier = f"{parent_id}.{cluster_id}" if parent_id is not None else f"top.{cluster_id}"
        cluster_entries.append(f"{cluster_identifier}|{top_types_str}")
        cluster_key_order.append(cluster_key)  # Track order with unique key
    
    if not cluster_entries:
        # All clusters are empty
        return {}
    
    # Create a simpler batch prompt
    clusters_text = "\n".join([f"Cluster {entry.split('|')[0]}: {entry.split('|')[1]}" 
                               for entry in cluster_entries])
    
    batch_prompt = f"""Generate concise labels (2-4 words each) for these service request clusters.

Requirements:
- Each label should be 2-4 words maximum
- Be descriptive and specific
- Use common terminology
- Examples: "Pothole Repair", "Graffiti Removal", "Street Light Outage", "Tree Maintenance"

Clusters:
{clusters_text}

Output the list of labels surrounded by {{}}, and each individual label surrounded by ().

Format: {{(label1) (label2) (label3) ...}}"""

    try:
        if use_new_api:
            # New google-genai API - use gemini-2.5-flash
            # Set very high token limit to avoid truncation
            print(f"[DEBUG] Requesting 8192 output tokens for {len(cluster_entries)} clusters")
            response = client_new.models.generate_content(
                model="gemini-2.5-flash",
                contents=batch_prompt,
                config={
                    "temperature": 0.3,
                    "max_output_tokens": 8192,  # Very high limit to avoid truncation
                }
            )
        else:
            # Old google-generativeai API
            model_instance = client_old.GenerativeModel("gemini-pro")
            print(f"[DEBUG] Requesting 8192 output tokens for {len(cluster_entries)} clusters")
            response = model_instance.generate_content(
                batch_prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 8192,  # Very high limit to avoid truncation
                }
            )
        
        # Parse response - get full text
        result_text = response.text.strip()
        
        # Debug: check full response
        print(f"[DEBUG] Full response length: {len(result_text)} chars")
        print(f"[DEBUG] Full response:\n{result_text}")
        
        # Check if response was truncated
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            if hasattr(response.usage_metadata, 'candidates_token_count'):
                print(f"[DEBUG] Response tokens used: {response.usage_metadata.candidates_token_count}")
        
        labels_dict = {}
        
        # Parse response - expect format: {(label1) (label2) (label3) ...}
        import re
        
        # Extract all labels from parentheses: (label)
        labels_found = re.findall(r'\(([^)]+)\)', result_text)
        
        # Debug: check what we have
        print(f"[DEBUG] cluster_key_order length: {len(cluster_key_order)}")
        print(f"[DEBUG] labels_found length: {len(labels_found)}")
        
        # Match labels to cluster keys by position (cluster_key_order matches the order in prompt)
        # Use ALL found labels, matching to cluster keys (parent_id, cluster_id) in order
        num_to_match = min(len(labels_found), len(cluster_key_order))
        skipped_labels = 0
        for i in range(num_to_match):
            cluster_key = cluster_key_order[i]
            label = labels_found[i].strip()
            if label and label.lower() not in ['empty', 'n/a', 'none', '']:
                labels_dict[cluster_key] = label
            else:
                skipped_labels += 1
                print(f"[DEBUG] Skipped label at position {i}: '{label}' (empty or invalid)")
        
        # Debug: show parsing results
        print(f"[DEBUG] Successfully assigned {len(labels_dict)} labels to clusters")
        if skipped_labels > 0:
            print(f"[DEBUG] Skipped {skipped_labels} invalid/empty labels")
        if len(labels_found) < len(cluster_key_order):
            print(f"[WARN] Response incomplete - got {len(labels_found)}/{len(cluster_key_order)} labels (response may be truncated)")
        elif len(labels_found) > len(cluster_key_order):
            print(f"[WARN] Got more labels ({len(labels_found)}) than clusters ({len(cluster_key_order)}) - extra labels ignored")
        
        return labels_dict
    
    except Exception as e:
        error_msg = str(e)
        print(f"[WARN] Batch LLM generation failed: {error_msg}")
        
        # Provide helpful error message
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"[INFO] Model '{model}' not found. Trying to list available models...")
            try:
                # Try to list available models (only works with new API)
                if use_new_api:
                    models = client_new.models.list()
                    print(f"[INFO] Available models: {[m.name for m in models][:5]}...")
            except Exception:
                print(f"[INFO] Could not list models. Please check:")
                print(f"  1. GEMINI_API_KEY is set correctly")
                print(f"  2. Package version: pip install --upgrade google-genai")
                print(f"  3. Try model names like: gemini-pro, gemini-1.5-pro-latest")
        
        # Return empty dict, will fall back to simple labels
        return {}


def generate_label_with_gemini(service_types, descriptions, model="gemini-2.5-flash"):
    """
    Generate a concise label using Gemini LLM (single cluster).
    
    Args:
        service_types: List of service type strings
        descriptions: List of description strings (not used to save tokens)
        model: Gemini model to use
    
    Returns:
        str: Generated label (2-4 words)
    """
    # Try new package first, fall back to old package
    try:
        import google.genai as genai_new
        use_new_api = True
    except ImportError:
        try:
            import google.generativeai as genai_old
            use_new_api = False
        except ImportError:
            raise ImportError(
                "Neither google-genai nor google-generativeai package found. "
                "Install with: pip install google-genai"
            )
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    if use_new_api:
        client_new = genai_new.Client(api_key=api_key)
    else:
        genai_old.configure(api_key=api_key)
        client_old = genai_old
    
    # Prepare context - only use service types to save tokens
    service_type_counter = Counter(service_types)
    top_types = service_type_counter.most_common(3)
    top_types_str = ", ".join([f"{name} ({count})" for name, count in top_types])
    
    # Create prompt (minimal to save credits)
    prompt = f"""Generate a concise label (2-4 words) for a service request cluster.

Service types: {top_types_str}

Label (2-4 words only):"""

    try:
        if use_new_api:
            # New google-genai API - use gemini-2.5-flash
            response = client_new.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "temperature": 0.3,
                    "max_output_tokens": 50,  # Enough for 2-4 word labels
                }
            )
        else:
            # Old google-generativeai API
            model_instance = client_old.GenerativeModel("gemini-pro")
            response = model_instance.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 50,  # Enough for 2-4 word labels
                }
            )
        
        label = response.text.strip()
        # Clean up label (remove quotes, extra whitespace)
        label = label.strip('"\'')
        # Remove any trailing incomplete words or numbers
        label = label.rstrip(' (0123456789')
        return label
    
    except Exception as e:
        print(f"[WARN] LLM generation failed: {e}")
        # Fall back to simple label
        return generate_label(service_types, descriptions, use_keywords=False)


def is_simple_service_type(service_type):
    """
    Check if a service type is simple (2-3 words) and can be used directly as a label.
    
    Args:
        service_type: Service type string
    
    Returns:
        bool: True if service type is 2-3 words
    """
    if not service_type:
        return False
    
    words = service_type.split()
    # Check if it's 2-3 words (after removing common prefixes)
    word_count = len(words)
    
    # If it's exactly 2-3 words, it's simple
    if 2 <= word_count <= 3:
        return True
    
    # If it's longer but starts with common prefixes, check the meaningful part
    skip_prefixes = ['service', 'request', 'type', 'for', 'the', 'a', 'an']
    meaningful_words = [w for w in words if w.lower() not in skip_prefixes]
    
    return 2 <= len(meaningful_words) <= 3


def needs_llm_labeling(service_types, descriptions):
    """
    Determine if a cluster needs LLM labeling.
    
    Simple rule: Use service type directly ONLY if:
    - Service type is 2-3 words
    - Service type dominates (>= 70%)
    - Descriptions are short (<= 3 words average)
    
    Everything else uses LLM.
    
    Args:
        service_types: List of service type strings
        descriptions: List of description strings
    
    Returns:
        bool: True if LLM labeling is needed
    """
    if not service_types:
        return False  # Empty cluster, will be labeled as "EMPTY"
    
    service_type_counter = Counter(service_types)
    most_common_type, most_common_count = service_type_counter.most_common(1)[0]
    total_count = len(service_types)
    percentage = (most_common_count / total_count) * 100 if total_count > 0 else 0
    
    # Check if service type is simple (2-3 words)
    if not is_simple_service_type(most_common_type):
        return True  # Use LLM
    
    # Check if it dominates
    if percentage < 70:
        return True  # Use LLM
    
    # Check if descriptions are short (<= 3 words average)
    if descriptions:
        valid_descriptions = [d for d in descriptions if d]
        if valid_descriptions:
            total_desc_words = sum(len(desc.split()) for desc in valid_descriptions)
            avg_desc_words = total_desc_words / len(valid_descriptions)
            if avg_desc_words > 3:
                return True  # Use LLM
    
    # All conditions met: use service type directly
    return False


def get_simple_label(service_types):
    """
    Get a simple label from service types (2-3 words, use directly).
    
    This should only be called when we know the service type is already 2-3 words.
    Returns the full service type, cleaned up if needed.
    
    Args:
        service_types: List of service type strings
    
    Returns:
        str: Simple label (2-3 words, full text)
    """
    if not service_types:
        return "Unlabeled"
    
    service_type_counter = Counter(service_types)
    most_common_type, most_common_count = service_type_counter.most_common(1)[0]
    total_count = len(service_types)
    percentage = (most_common_count / total_count) * 100 if total_count > 0 else 0
    
    # Only use if it dominates
    if percentage >= 70:
        # Clean up the service type (remove common prefixes) but keep full meaningful words
        words = most_common_type.split()
        skip_prefixes = ['service', 'request', 'type', 'for', 'the', 'a', 'an']
        meaningful_words = [w for w in words if w.lower() not in skip_prefixes]
        
        # If we have 2-3 meaningful words, use them (full words, not truncated)
        if 2 <= len(meaningful_words) <= 3:
            return ' '.join(meaningful_words)  # Full words, not truncated
        # If original is already 2-3 words, use it as-is
        elif 2 <= len(words) <= 3:
            return most_common_type
    
    # If we get here, something went wrong - this shouldn't be called for non-simple types
    # But return the most common type anyway (don't truncate)
    return most_common_type


def generate_label(service_types, descriptions=None, use_keywords=False):
    """
    Generate a simple label without LLM (fallback).
    Returns complete, meaningful labels - never ends with "and", "or", etc.
    
    Args:
        service_types: List of service type strings
        descriptions: Not used in simple mode
        use_keywords: Not used in simple mode
    
    Returns:
        str: Simple label (complete, no trailing connectors)
    """
    if not service_types:
        return "Unlabeled"
    
    # Count service types
    service_type_counter = Counter(service_types)
    most_common_type, most_common_count = service_type_counter.most_common(1)[0]
    total_count = len(service_types)
    
    # Calculate percentage
    percentage = (most_common_count / total_count) * 100 if total_count > 0 else 0
    
    # For homogeneous clusters (>= 60%), use the most common type (cleaned up)
    if percentage >= 60:
        # Clean up: remove common prefixes and trailing connectors
        words = most_common_type.split()
        skip_prefixes = ['service', 'request', 'type', 'for', 'the', 'a', 'an']
        connecting_words = ['and', 'or', '/', '-', '&']
        
        meaningful_words = []
        for word in words:
            word_lower = word.lower().rstrip('.,;:')
            if word_lower not in skip_prefixes and word_lower not in connecting_words:
                meaningful_words.append(word)
            elif word_lower in connecting_words:
                break  # Stop at connecting words
        
        # Return first 2-3 meaningful words, or full if already short
        if 2 <= len(meaningful_words) <= 3:
            return ' '.join(meaningful_words)
        elif len(meaningful_words) > 3:
            return ' '.join(meaningful_words[:3])
        else:
            # Fallback: just use first 2-3 words of original, stopping before connectors
            result = []
            for word in words[:3]:
                if word.lower().rstrip('.,;:') not in connecting_words:
                    result.append(word)
                else:
                    break
            return ' '.join(result) if result else most_common_type
    
    # For mixed clusters, just use the most common type (don't try to combine)
    # Better to have one complete label than a truncated combination
    words = most_common_type.split()
    connecting_words = ['and', 'or', '/', '-', '&']
    result = []
    for word in words[:3]:  # Take up to 3 words
        if word.lower().rstrip('.,;:') not in connecting_words:
            result.append(word)
        else:
            break  # Stop before connecting word
    return ' '.join(result) if result else most_common_type


def generate_label(service_types, descriptions=None, use_llm=False, llm_model="gpt-4o-mini"):
    """
    Generate a short label (just a few words) for a cluster.
    
    Args:
        service_types: List of service type strings
        descriptions: Optional list of description strings (not used for short labels)
        use_keywords: Whether to include keywords (ignored for short labels)
    
    Returns:
        str: Short label (2-4 words)
    """
    if not service_types:
        return "Unlabeled"
    
    # Count service types
    service_type_counter = Counter(service_types)
    most_common_type, most_common_count = service_type_counter.most_common(1)[0]
    total_count = len(service_types)
    
    # Calculate percentage
    percentage = (most_common_count / total_count) * 100 if total_count > 0 else 0
    
    # Shorten the most common service type
    short_type = shorten_service_type(most_common_type, max_words=3)
    
    # For very homogeneous clusters (>= 60%), just use the shortened type
    if percentage >= 60:
        return short_type
    
    # For mostly one type (40-60%), use the type name
    elif percentage >= 40:
        return short_type
    
    # For mixed clusters (< 40%), show top 2 types (shortened)
    else:
        top_types = service_type_counter.most_common(2)
        if len(top_types) == 1:
            return shorten_service_type(top_types[0][0], max_words=2)
        else:
            type1 = shorten_service_type(top_types[0][0], max_words=2)
            type2 = shorten_service_type(top_types[1][0], max_words=2)
            # Combine into max 4 words total
            words1 = type1.split()[:2]
            words2 = type2.split()[:2]
            combined = ' '.join(words1 + words2)
            # Limit to 4 words max
            all_words = combined.split()
            return ' '.join(all_words[:4])


def get_all_clusters(conn):
    """
    Get all clusters from the database.
    
    Returns:
        list: List of tuples (cluster_id, parent_cluster_id, level)
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT cluster_id, parent_cluster_id, level
        FROM clusters
        ORDER BY level, parent_cluster_id NULLS FIRST, cluster_id
    """)
    
    results = cursor.fetchall()
    cursor.close()
    
    return results


def print_cluster_csv(cluster_data, output_file=None):
    """
    Print clusters in CSV format.
    
    Args:
        cluster_data: List of tuples (level, parent_id, cluster_id, examples, label, top_types)
        output_file: Optional file path to write CSV to. If None, prints to stdout.
    """
    if not cluster_data:
        print("\n[INFO] No clusters to display")
        return
    
    # Prepare CSV data
    csv_rows = []
    csv_rows.append(['Level', 'Parent Cluster ID', 'Cluster ID', 'Examples', 'Label', 'Top Service Types'])
    
    for level, parent_id, cluster_id, examples, label, top_types in cluster_data:
        level_str = "Top-level" if level == 1 else "Sub-cluster"
        parent_str = str(parent_id) if parent_id is not None else ""
        csv_rows.append([level_str, parent_str, str(cluster_id), str(examples), label, top_types or ""])
    
    # Write to file or stdout
    if output_file:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(csv_rows)
        print(f"\n[SUCCESS] Wrote {len(csv_rows)-1} clusters to {output_file}")
    else:
        # Print to stdout
        writer = csv.writer(sys.stdout)
        writer.writerows(csv_rows)


def main():
    """Main function to label clusters."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate and display labels for clusters')
    parser.add_argument('--use-llm', action='store_true', default=False,
                       help='Use Gemini LLM for label generation (requires GEMINI_API_KEY)')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of clusters to batch together for LLM (default: 50, saves credits)')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output CSV file path (default: stdout)')
    
    args = parser.parse_args()
    
    try:
        print("[INFO] Connecting to database...")
        conn = get_conn()
        print("[SUCCESS] Connected to database")
        
        # Get all clusters
        print("\n[INFO] Fetching clusters...")
        clusters = get_all_clusters(conn)
        print(f"[INFO] Found {len(clusters)} clusters")
        
        # Collect ALL cluster data (including empty ones)
        cluster_info = []
        
        print("[INFO] Analyzing all clusters...")
        
        for cluster_id, parent_id, level in clusters:
            # Get requests in this cluster
            requests = get_cluster_requests(conn, parent_id, cluster_id)
            
            # Extract service types and descriptions
            service_types = [req[0] for req in requests if req[0]]
            descriptions = [req[1] for req in requests if req[1]]
            
            cluster_info.append({
                'level': level,
                'parent_id': parent_id,
                'cluster_id': cluster_id,
                'examples': len(requests),
                'service_types': service_types,
                'descriptions': descriptions
            })
        
        empty_count = sum(1 for c in cluster_info if c['examples'] == 0)
        print(f"[INFO] Processing {len(cluster_info)} clusters ({empty_count} empty, {len(cluster_info) - empty_count} with data)")
        
        # Generate labels
        cluster_data = []
        llm_count = 0
        simple_count = 0
        
        if args.use_llm:
            print(f"[INFO] Using Gemini LLM with batch size {args.batch_size}...")
            
            # Categorize clusters:
            # 1. Empty clusters -> "EMPTY"
            # 2. Simple service types (2-3 words) -> use directly
            # 3. Complex cases -> use LLM
            empty_clusters = []
            simple_clusters = []
            complex_clusters = []
            
            for info in cluster_info:
                if info['examples'] == 0:
                    empty_clusters.append(info)
                elif not needs_llm_labeling(info['service_types'], info['descriptions']):
                    simple_clusters.append(info)
                else:
                    complex_clusters.append(info)
            
            print(f"[INFO] {len(empty_clusters)} empty clusters → 'EMPTY'")
            print(f"[INFO] {len(simple_clusters)} simple clusters → use service type directly")
            print(f"[INFO] {len(complex_clusters)} complex clusters → use LLM labeling")
            
            # Process simple clusters (use service type directly)
            for info in simple_clusters:
                label = get_simple_label(info['service_types'])
                
                if info['service_types']:
                    top_types = Counter(info['service_types']).most_common(3)
                    top_types_str = ", ".join([f"{name} ({count})" for name, count in top_types])
                else:
                    top_types_str = ""
                
                cluster_data.append((
                    info['level'],
                    info['parent_id'],
                    info['cluster_id'],
                    info['examples'],
                    label,
                    top_types_str
                ))
            
            # Process complex clusters with LLM in batches
            if complex_clusters:
                for i in range(0, len(complex_clusters), args.batch_size):
                    batch = complex_clusters[i:i + args.batch_size]
                    batch_num = (i // args.batch_size) + 1
                    total_batches = (len(complex_clusters) + args.batch_size - 1) // args.batch_size
                    
                    print(f"[INFO] Processing LLM batch {batch_num}/{total_batches} ({len(batch)} clusters)...")
                    
                    # Prepare batch data for LLM (include parent_id for unique identification)
                    batch_data = [
                        (info['service_types'], info['descriptions'], info['parent_id'], info['cluster_id'])
                        for info in batch
                    ]
                    
                    # Generate labels in batch
                    llm_labels = generate_labels_batch_with_gemini(batch_data)
                    
                    # Debug: show how many labels we got
                    if len(llm_labels) < len(batch):
                        missing = len(batch) - len(llm_labels)
                        print(f"[WARN] Only got {len(llm_labels)}/{len(batch)} labels from LLM ({missing} missing)")
                    
                    # Process results
                    for info in batch:
                        cluster_id = info['cluster_id']
                        parent_id = info['parent_id']
                        cluster_key = (parent_id, cluster_id)
                        
                        # Use LLM label if available (lookup by unique key)
                        if cluster_key in llm_labels:
                            label = llm_labels[cluster_key]
                            # Clean up label - remove trailing connectors
                            connecting_words = ['and', 'or', '/', '-', '&']
                            label_words = label.split()
                            while label_words and label_words[-1].lower().rstrip('.,;:') in connecting_words:
                                label_words.pop()
                            label = ' '.join(label_words) if label_words else label
                        else:
                            # LLM failed for this cluster - this shouldn't happen often!
                            print(f"[WARN] LLM label missing for cluster {cluster_id}, using fallback")
                            # Fallback: if LLM failed, use simple label (which now handles connectors properly)
                            if is_simple_service_type(Counter(info['service_types']).most_common(1)[0][0]):
                                label = get_simple_label(info['service_types'])
                            else:
                                label = generate_label(info['service_types'], info['descriptions'])
                        
                        # Get top service types for display
                        if info['service_types']:
                            top_types = Counter(info['service_types']).most_common(3)
                            top_types_str = ", ".join([f"{name} ({count})" for name, count in top_types])
                        else:
                            top_types_str = ""
                        
                        cluster_data.append((
                            info['level'],
                            info['parent_id'],
                            cluster_id,
                            info['examples'],
                            label,
                            top_types_str
                        ))
            
            # Add empty clusters with "EMPTY" label
            for info in empty_clusters:
                cluster_data.append((
                    info['level'],
                    info['parent_id'],
                    info['cluster_id'],
                    info['examples'],
                    "EMPTY",
                    ""
                ))
        else:
            # Simple label generation (no LLM)
            print("[INFO] Generating simple labels...")
            for info in cluster_info:
                if info['examples'] == 0:
                    label = "EMPTY"
                elif is_simple_service_type(Counter(info['service_types']).most_common(1)[0][0]):
                    # Use simple service type directly
                    label = get_simple_label(info['service_types'])
                else:
                    label = generate_label(info['service_types'], info['descriptions'])
                
                # Get top service types for display
                if info['service_types']:
                    top_types = Counter(info['service_types']).most_common(3)
                    top_types_str = ", ".join([f"{name} ({count})" for name, count in top_types])
                else:
                    top_types_str = ""
                
                cluster_data.append((
                    info['level'],
                    info['parent_id'],
                    info['cluster_id'],
                    info['examples'],
                    label,
                    top_types_str
                ))
        
        labeled_count = len(cluster_data)
        
        # Print CSV
        if args.output:
            print(f"\n[INFO] Writing CSV to {args.output}...")
        else:
            print("\n[INFO] Cluster labels (CSV format):")
        
        # Sort cluster_data by level, then parent_id, then cluster_id for consistent output
        cluster_data.sort(key=lambda x: (x[0], x[1] if x[1] is not None else 0, x[2]))
        
        print_cluster_csv(cluster_data, output_file=args.output)
        
        if not args.output:
            print(f"\n[INFO] Generated labels for {len(cluster_data)} clusters (all clusters included)")
            if args.use_llm:
                empty_count = sum(1 for c in cluster_data if c[4] == "EMPTY")
                print(f"[INFO] Labeling summary:")
                print(f"  - {empty_count} empty clusters → 'EMPTY'")
                print(f"  - {simple_count} simple clusters → used service type directly")
                print(f"  - {llm_count} complex clusters → used Gemini LLM")
                print(f"[INFO] Batch size: {args.batch_size} (fewer API calls = lower cost)")
            print(f"[INFO] Use --output <file.csv> to save to a file")
        
        conn.close()
        return 0
    
    except Exception as e:
        print(f"\n[ERROR] Failed to label clusters: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
