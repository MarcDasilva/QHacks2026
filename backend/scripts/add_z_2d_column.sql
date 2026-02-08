-- Run this in Supabase SQL Editor if request_2d already exists but has no z_2d column.
-- Required before: python scripts/compute_2d_umap.py --3d

ALTER TABLE request_2d ADD COLUMN IF NOT EXISTS z_2d DOUBLE PRECISION;
