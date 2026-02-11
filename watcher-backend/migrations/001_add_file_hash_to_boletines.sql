-- Migration: Add file_hash and file_size_bytes to boletines table
-- Epic 1.1 - SHA256 deduplication
-- Date: 2026-02-10

-- Add file_hash column (SHA256, 64 characters)
ALTER TABLE boletines ADD COLUMN file_hash VARCHAR(64);

-- Add file_size_bytes column
ALTER TABLE boletines ADD COLUMN file_size_bytes INTEGER;

-- Create index on file_hash for efficient deduplication lookups
CREATE INDEX IF NOT EXISTS idx_boletines_file_hash ON boletines(file_hash);
