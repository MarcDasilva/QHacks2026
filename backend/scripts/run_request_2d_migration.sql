-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Creates request_2d table for UMAP visualization. Then run: python scripts/compute_2d_umap.py

CREATE TABLE IF NOT EXISTS request_2d (
  request_id INTEGER PRIMARY KEY REFERENCES requests(id) ON DELETE CASCADE,
  x_2d DOUBLE PRECISION NOT NULL,
  y_2d DOUBLE PRECISION NOT NULL,
  z_2d DOUBLE PRECISION,
  top_cluster_id INTEGER,
  sub_cluster_id INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_request_2d_top_cluster ON request_2d(top_cluster_id);
CREATE INDEX IF NOT EXISTS idx_request_2d_sub_cluster ON request_2d(sub_cluster_id);

COMMENT ON TABLE request_2d IS '2D/3D projection of request embeddings (UMAP) for cluster visualization';
-- If table already existed without z_2d, run: ALTER TABLE request_2d ADD COLUMN IF NOT EXISTS z_2d DOUBLE PRECISION;
