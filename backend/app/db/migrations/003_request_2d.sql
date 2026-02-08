-- Precomputed 2D coordinates for embedding visualization (e.g. UMAP from 384D).
-- Populated by scripts/compute_2d_umap.py. Enables scatter-plot visualization by cluster.
CREATE TABLE IF NOT EXISTS request_2d (
  request_id INTEGER PRIMARY KEY REFERENCES requests(id) ON DELETE CASCADE,
  x_2d DOUBLE PRECISION NOT NULL,
  y_2d DOUBLE PRECISION NOT NULL,
  top_cluster_id INTEGER,
  sub_cluster_id INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_request_2d_top_cluster ON request_2d(top_cluster_id);
CREATE INDEX IF NOT EXISTS idx_request_2d_sub_cluster ON request_2d(sub_cluster_id);

COMMENT ON TABLE request_2d IS '2D projection of request embeddings (e.g. UMAP) for cluster visualization';
