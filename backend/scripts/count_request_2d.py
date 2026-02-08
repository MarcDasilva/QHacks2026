"""Print row counts for request_2d (UMAP dots). Run from repo root or backend/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.connection import get_conn

def main():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM request_2d")
    total = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM request_2d WHERE z_2d IS NOT NULL"
    )
    with_z = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(f"request_2d total rows (2D UMAP dots): {total:,}")
    print(f"request_2d with z_2d (3D):            {with_z:,}")

if __name__ == "__main__":
    main()
