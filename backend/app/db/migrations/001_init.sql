CREATE TABLE raw_requests (
  "Service Request ID" TEXT,
  "Reference Number" TEXT,
  "Electoral District" TEXT,
  "Neighbourhood" TEXT,
  "Channel" TEXT,
  "Date Closed" TEXT,
  "Date Created" TEXT,
  "Date Last Updated" TEXT,
  "Service Type" TEXT,
  "Service Level 1" TEXT,
  "Service Level 2" TEXT,
  "Service Level 3" TEXT,
  "Service Level 4" TEXT,
  "Service Level 5" TEXT,
  "Status Type" TEXT,
  "First call resolution" TEXT,
  "OBJECTID" BIGINT
);

CREATE TABLE requests (
  id SERIAL PRIMARY KEY,
  service_request_id TEXT UNIQUE,
  ref_number TEXT,
  service_type TEXT NOT NULL,
  description TEXT,
  created_at DATE NOT NULL,
  resolved_at DATE,
  location TEXT,
  embedding VECTOR(768)
);

CREATE TABLE alerts (
  id SERIAL PRIMARY KEY,
  service_type TEXT NOT NULL,
  severity INT NOT NULL,
  reason TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  acknowledged BOOLEAN DEFAULT FALSE
);
