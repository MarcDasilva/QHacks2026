"""
Print how many level-1 (and level-2) cluster nodes exist in the database.

Level-1 = top-level clusters (parent_cluster_id IS NULL).
Level-2 = sub-clusters under each level-1 (parent_cluster_id = level-1 cluster_id).

Run from repo root or backend/: python scripts/count_level1_clusters.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.connection import get_conn


def main():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM clusters WHERE level = 1")
    level1_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM clusters WHERE level = 2")
    level2_count = cur.fetchone()[0]

    cur.execute(
        """
        SELECT cluster_id, size
        FROM clusters
        WHERE level = 1
        ORDER BY cluster_id
        """
    )
    level1_rows = cur.fetchall()

    cur.close()
    conn.close()

    print("Level-1 clusters (top-level nodes):")
    print(f"  Total count: {level1_count}")
    print()
    if level1_rows:
        print("  cluster_id | size (requests)")
        print("  -----------+----------------")
        for cid, size in level1_rows:
            print(f"  {cid:>10} | {size:>14,}")
        print()
    print(f"Level-2 clusters (sub-clusters): {level2_count}")
    print(f"Total cluster rows (level 1 + 2):  {level1_count + level2_count}")


if __name__ == "__main__":
    main()
