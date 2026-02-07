ALTER TABLE requests ADD COLUMN IF NOT EXISTS top_cluster_id INTEGER;
ALTER TABLE requests ADD COLUMN IF NOT EXISTS sub_cluster_id INTEGER;

CREATE TABLE IF NOT EXISTS clusters (
  id SERIAL PRIMARY KEY,
  cluster_id INTEGER NOT NULL,
  parent_cluster_id INTEGER,
  level INTEGER NOT NULL,
  centroid VECTOR(384),
  size INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(cluster_id, parent_cluster_id, level)
);