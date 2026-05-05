-- Add content_type column to uploads so ai_service can send the correct
-- MIME type to GPT-4o Vision (instead of hardcoding image/png for all images).
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS content_type TEXT;
