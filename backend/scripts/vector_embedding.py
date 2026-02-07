"""
Generate vector embeddings for requests table based on service_type and description.

Optimizations:
- Batch processing (processes multiple rows at once)
- Only processes rows without embeddings
- Uses batch UPDATE statements
- Generates embeddings in batches for efficiency

Usage:
python scripts/vector_embedding.py
python scripts/vector_embedding.py --batch-size 500
python scripts/vector_embedding.py --limit 10000  # Process only first 10k rows
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import execute_batch
import numpy as np
from app.db.connection import get_conn


def get_embedding_model():
    """Load the embedding model (lazy loading to avoid loading if not needed)."""
    try:
        from sentence_transformers import SentenceTransformer
        # Using all-MiniLM-L6-v2 (384 dimensions) instead of all-mpnet-base-v2 (768 dimensions)
        # to stay within Supabase plan limits while maintaining good quality
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("[INFO] Loaded embedding model: all-MiniLM-L6-v2 (384 dimensions)")
        return model
    except ImportError:
        print("[ERROR] sentence-transformers not installed. Install with: pip install sentence-transformers")
        raise


def build_embedding_text(service_type, description):
    """Build the text to embed from service_type and description."""
    parts = []
    
    if service_type:
        parts.append(str(service_type).strip())
    
    if description:
        parts.append(str(description).strip())
    
    return ' | '.join(parts) if parts else None


def fetch_rows_needing_embeddings(conn, batch_size=1000, limit=None):
    """Fetch rows that need embeddings in batches."""
    cursor = conn.cursor()
    
    query = """
        SELECT id, service_type, description
        FROM requests
        WHERE embedding IS NULL
        ORDER BY id
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        yield rows
    
    cursor.close()


def generate_embeddings_batch(model, texts):
    """Generate embeddings for a batch of texts."""
    if not texts:
        return []
    
    # Filter out None/empty texts
    valid_texts = [text for text in texts if text]
    if not valid_texts:
        return [None] * len(texts)
    
    # Generate embeddings in batch
    embeddings = model.encode(valid_texts, show_progress_bar=False, convert_to_numpy=True)
    
    # Map back to original positions (handling None values)
    result = []
    valid_idx = 0
    for text in texts:
        if text:
            result.append(embeddings[valid_idx].tolist())
            valid_idx += 1
        else:
            result.append(None)
    
    return result


def update_embeddings_batch(conn, rows_with_embeddings):
    """Update embeddings in the database using batch update."""
    if not rows_with_embeddings:
        return
    
    cursor = conn.cursor()
    
    # Prepare data for batch update
    update_data = [
        (embedding, row_id) 
        for row_id, embedding in rows_with_embeddings 
        if embedding is not None
    ]
    
    if not update_data:
        cursor.close()
        return
    
    # Use batch update for efficiency
    update_query = """
        UPDATE requests
        SET embedding = %s::vector
        WHERE id = %s
    """
    
    execute_batch(cursor, update_query, update_data, page_size=500)
    conn.commit()
    cursor.close()


def process_embeddings(conn, model, batch_size=1000, limit=None):
    """Process embeddings for all rows that need them."""
    total_processed = 0
    total_updated = 0
    
    print(f"[INFO] Starting embedding generation (batch_size={batch_size})...")
    
    for batch_rows in fetch_rows_needing_embeddings(conn, batch_size=batch_size, limit=limit):
        if not batch_rows:
            break
        
        # Extract data for this batch
        row_ids = [row[0] for row in batch_rows]
        service_types = [row[1] for row in batch_rows]
        descriptions = [row[2] for row in batch_rows]
        
        # Build texts to embed
        texts_to_embed = [
            build_embedding_text(st, desc) 
            for st, desc in zip(service_types, descriptions)
        ]
        
        # Generate embeddings for this batch
        embeddings = generate_embeddings_batch(model, texts_to_embed)
        
        # Prepare rows with embeddings
        rows_with_embeddings = list(zip(row_ids, embeddings))
        
        # Update database
        update_embeddings_batch(conn, rows_with_embeddings)
        
        # Track progress
        batch_updated = sum(1 for _, emb in rows_with_embeddings if emb is not None)
        total_processed += len(batch_rows)
        total_updated += batch_updated
        
        print(f"[INFO] Processed {total_processed} rows ({total_updated} updated)...")
    
    return total_processed, total_updated


def get_stats(conn):
    """Get statistics about embeddings in the requests table."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM requests")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE embedding IS NOT NULL")
    with_embeddings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM requests WHERE embedding IS NULL")
    without_embeddings = cursor.fetchone()[0]
    
    cursor.close()
    
    return total, with_embeddings, without_embeddings


def main():
    """Main function to generate embeddings."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate vector embeddings for requests table')
    parser.add_argument('--batch-size', type=int, default=1000, 
                       help='Number of rows to process in each batch (default: 1000)')
    parser.add_argument('--limit', type=int, 
                       help='Limit the number of rows to process (for testing)')
    
    args = parser.parse_args()
    
    try:
        print("[INFO] Connecting to database...")
        conn = get_conn()
        print("[SUCCESS] Connected to database")
        
        # Get statistics
        total, with_embeddings, without_embeddings = get_stats(conn)
        print(f"[INFO] Total rows: {total}")
        print(f"[INFO] Rows with embeddings: {with_embeddings}")
        print(f"[INFO] Rows without embeddings: {without_embeddings}")
        
        if without_embeddings == 0:
            print("[INFO] All rows already have embeddings. Nothing to do.")
            conn.close()
            return 0
        
        # Load embedding model
        print("[INFO] Loading embedding model...")
        model = get_embedding_model()
        
        # Process embeddings
        processed, updated = process_embeddings(
            conn, 
            model, 
            batch_size=args.batch_size,
            limit=args.limit
        )
        
        print(f"[SUCCESS] Processed {processed} rows, updated {updated} rows")
        
        # Get final statistics
        total, with_embeddings, without_embeddings = get_stats(conn)
        print(f"[INFO] Final stats - Total: {total}, With embeddings: {with_embeddings}, Without: {without_embeddings}")
        
        conn.close()
        return 0
    
    except Exception as e:
        print(f"[ERROR] Failed to generate embeddings: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
