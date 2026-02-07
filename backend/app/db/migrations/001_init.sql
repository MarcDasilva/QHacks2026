CREATE TABLE requests (
  id SERIAL PRIMARY KEY,
  service_request_id TEXT UNIQUE,
  ref_number TEXT,
  service_type TEXT NOT NULL,
  description TEXT,
  created_at DATE NOT NULL,
  resolved_at DATE,
  location TEXT,
  embedding VECTOR(384)
);

CREATE TABLE alerts (
  id SERIAL PRIMARY KEY,
  service_type TEXT NOT NULL,
  severity INT NOT NULL,
  reason TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  acknowledged BOOLEAN DEFAULT FALSE
);
