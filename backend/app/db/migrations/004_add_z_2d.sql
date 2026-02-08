-- Add optional 3D coordinate for UMAP (n_components=3).
-- Run after 003_request_2d.sql. Populated by: python scripts/compute_2d_umap.py --3d
ALTER TABLE request_2d ADD COLUMN IF NOT EXISTS z_2d DOUBLE PRECISION;

COMMENT ON COLUMN request_2d.z_2d IS 'Third UMAP component when using --3d; NULL for 2D-only runs';
