-- Add label column to clusters table
ALTER TABLE clusters ADD COLUMN IF NOT EXISTS label TEXT;
