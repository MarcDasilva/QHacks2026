"""
Compute 2D UMAP projection of request embeddings for cluster visualization.

Only level-1 clusters are included (all 25). Reads requests (id, embedding,
top_cluster_id, sub_cluster_id) for those clusters only, runs UMAP to 2D, and
writes to request_2d. Any existing request_2d rows for other clusters are removed.
Uses 1-in-6 sampling by default within level-1 clusters.
Run migration 003_request_2d.sql first.

Usage:
  python scripts/compute_2d_umap.py                  # 2D, all 25 level-1 clusters, 1-in-6
  python scripts/compute_2d_umap.py --3d              # 3D UMAP (stores z_2d)
  python scripts/compute_2d_umap.py --sample-every 1  # no sampling
  python scripts/compute_2d_umap.py --n-neighbors 30
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from psycopg2.extras import execute_batch

from app.db.connection import get_conn


def parse_vector(embedding):
    """Parse vector from database - handles both string and array formats."""
    if embedding is None:
        return None
    if isinstance(embedding, (list, tuple)):
        return np.array(embedding, dtype=np.float32)
    if isinstance(embedding, str):
        embedding = embedding.strip("[]")
        values = [float(x.strip()) for x in embedding.split(",")]
        return np.array(values, dtype=np.float32)
    try:
        return np.array(embedding, dtype=np.float32)
    except (ValueError, TypeError):
        embedding_str = str(embedding).strip("[]")
        values = [float(x.strip()) for x in embedding_str.split(",")]
        return np.array(values, dtype=np.float32)


LEVEL_1_CLUSTERS_LIMIT = 25


def get_first_level1_cluster_ids(conn, limit=LEVEL_1_CLUSTERS_LIMIT):
    """Return the first `limit` level-1 cluster_ids from the clusters table."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT cluster_id FROM clusters
        WHERE level = 1
        ORDER BY cluster_id
        LIMIT %s
        """,
        (limit,),
    )
    ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return ids


def fetch_embeddings_and_clusters(
    conn, batch_size=5000, sample=None, sample_every=6, top_cluster_ids=None
):
    """Fetch id, embedding, top_cluster_id, sub_cluster_id from requests.
    sample_every: keep every Nth row by id (1 = no sampling, 6 = 1-in-6).
    top_cluster_ids: if set, only fetch requests in these clusters (e.g. all 25 level-1).
    """
    cursor = conn.cursor()
    where = "embedding IS NOT NULL AND top_cluster_id IS NOT NULL"
    if sample_every and sample_every > 1:
        # Use %% so psycopg2 does not treat % as a parameter placeholder
        where += f" AND id %% {int(sample_every)} = 0"
    if top_cluster_ids:
        placeholders = ",".join("%s" for _ in top_cluster_ids)
        where += f" AND top_cluster_id IN ({placeholders})"
    params = tuple(top_cluster_ids) if top_cluster_ids else ()
    cursor.execute(
        f"SELECT COUNT(*) FROM requests WHERE {where}",
        params,
    )
    total = cursor.fetchone()[0]
    if total == 0:
        cursor.close()
        return [], np.array([]), [], []

    limit_clause = f"LIMIT {sample}" if sample else ""
    query = f"""
        SELECT id, embedding, top_cluster_id, sub_cluster_id
        FROM requests
        WHERE {where}
        ORDER BY id
        {limit_clause}
    """
    cursor.execute(query, params)

    ids, top_cluster_ids, sub_cluster_ids = [], [], []
    embeddings_list = []

    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        for row_id, emb, top_cid, sub_cid in rows:
            parsed = parse_vector(emb)
            if parsed is not None:
                ids.append(row_id)
                top_cluster_ids.append(top_cid)
                sub_cluster_ids.append(sub_cid)
                embeddings_list.append(parsed)

    cursor.close()
    if not embeddings_list:
        return [], np.array([]), [], []

    arr = np.array(embeddings_list, dtype=np.float32)
    return ids, arr, top_cluster_ids, sub_cluster_ids


def run_umap(embeddings, n_components=2, n_neighbors=15, min_dist=0.1, random_state=42):
    """Reduce to 2D or 3D with UMAP."""
    try:
        import umap
    except ImportError:
        print("[ERROR] umap-learn not installed. Install with: pip install umap-learn")
        raise

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=min(n_neighbors, len(embeddings) - 1),
        min_dist=min_dist,
        random_state=random_state,
        metric="cosine",
        verbose=True,
    )
    coords = reducer.fit_transform(embeddings)
    return coords


def clear_request_2d_outside_clusters(conn, keep_cluster_ids):
    """Delete from request_2d where top_cluster_id is not in keep_cluster_ids."""
    if not keep_cluster_ids:
        return
    cursor = conn.cursor()
    placeholders = ",".join("%s" for _ in keep_cluster_ids)
    cursor.execute(
        f"DELETE FROM request_2d WHERE top_cluster_id IS NOT NULL AND top_cluster_id NOT IN ({placeholders})",
        tuple(keep_cluster_ids),
    )
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    if deleted:
        print(f"[INFO] Removed {deleted} request_2d rows outside level-1 clusters ({len(keep_cluster_ids)} clusters).")


def write_request_2d(conn, ids, coords, top_cluster_ids, sub_cluster_ids, use_3d=False, batch_size=1000):
    """Upsert into request_2d. coords is (n, 2) or (n, 3); when use_3d=True writes z_2d."""
    cursor = conn.cursor()
    n = len(ids)
    for i in range(0, n, batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_x = coords[i : i + batch_size, 0].tolist()
        batch_y = coords[i : i + batch_size, 1].tolist()
        batch_top = top_cluster_ids[i : i + batch_size]
        batch_sub = sub_cluster_ids[i : i + batch_size]
        if use_3d and coords.shape[1] >= 3:
            batch_z = coords[i : i + batch_size, 2].tolist()
            rows = list(zip(batch_ids, batch_x, batch_y, batch_z, batch_top, batch_sub))
            execute_batch(
                cursor,
                """
                INSERT INTO request_2d (request_id, x_2d, y_2d, z_2d, top_cluster_id, sub_cluster_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE SET
                    x_2d = EXCLUDED.x_2d,
                    y_2d = EXCLUDED.y_2d,
                    z_2d = EXCLUDED.z_2d,
                    top_cluster_id = EXCLUDED.top_cluster_id,
                    sub_cluster_id = EXCLUDED.sub_cluster_id
                """,
                rows,
                page_size=batch_size,
            )
        else:
            rows = list(zip(batch_ids, batch_x, batch_y, batch_top, batch_sub))
            execute_batch(
                cursor,
                """
                INSERT INTO request_2d (request_id, x_2d, y_2d, top_cluster_id, sub_cluster_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE SET
                    x_2d = EXCLUDED.x_2d,
                    y_2d = EXCLUDED.y_2d,
                    top_cluster_id = EXCLUDED.top_cluster_id,
                    sub_cluster_id = EXCLUDED.sub_cluster_id
                """,
                rows,
                page_size=batch_size,
            )
        conn.commit()
        print(f"   Wrote {min(i + batch_size, n)} / {n} rows to request_2d")

    cursor.close()


def main():
    parser = argparse.ArgumentParser(description="Compute 2D UMAP projection for cluster viz")
    parser.add_argument("--sample", type=int, default=None, help="Max N points (optional cap)")
    parser.add_argument(
        "--sample-every",
        type=int,
        default=6,
        metavar="N",
        help="Store every Nth request by id (default: 6 = 1-in-6); use 1 for no sampling",
    )
    parser.add_argument("--3d", dest="use_3d", action="store_true", help="Compute 3D UMAP (store z_2d)")
    parser.add_argument("--n-neighbors", type=int, default=15, help="UMAP n_neighbors")
    parser.add_argument("--min-dist", type=float, default=0.1, help="UMAP min_dist")
    args = parser.parse_args()

    print("[INFO] Connecting to database...")
    conn = get_conn()

    print("[INFO] Getting all level-1 cluster IDs (25)...")
    level1_ids = get_first_level1_cluster_ids(conn)
    if not level1_ids:
        print("[WARN] No level-1 clusters in clusters table. Run clustering first.")
        conn.close()
        return
    print(f"[INFO] Restricting to level-1 clusters: {level1_ids}")

    print(f"[INFO] Fetching requests in those clusters (1-in-{args.sample_every} sampling)...")
    ids, embeddings, top_cids, sub_cids = fetch_embeddings_and_clusters(
        conn,
        sample=args.sample,
        sample_every=args.sample_every,
        top_cluster_ids=level1_ids,
    )
    if not ids:
        print("[WARN] No requests with embedding and top_cluster_id in level-1 clusters.")
        conn.close()
        return

    print(f"[INFO] Loaded {len(ids)} points, shape {embeddings.shape}")

    n_components = 3 if args.use_3d else 2
    print(f"[INFO] Running UMAP (384 -> {n_components}D)...")
    coords = run_umap(
        embeddings,
        n_components=n_components,
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
    )

    print("[INFO] Clearing request_2d for clusters outside level-1...")
    clear_request_2d_outside_clusters(conn, level1_ids)

    print("[INFO] Writing request_2d...")
    write_request_2d(conn, ids, coords, top_cids, sub_cids, use_3d=args.use_3d)

    conn.close()
    print("[SUCCESS] Done. You can now use the Cluster view in the dashboard.")


if __name__ == "__main__":
    main()
