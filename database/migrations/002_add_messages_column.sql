-- Migration: Add messages JSONB column for full conversation content
-- Purpose: Store full conversation in DB for search/filtering (not just in JSON files)

BEGIN;

-- Add JSONB column for full message content
ALTER TABLE learning.ai_chat_conversations
ADD COLUMN IF NOT EXISTS messages JSONB DEFAULT NULL;

-- Create GIN index for JSONB queries (fast JSON searches)
CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_gin
ON learning.ai_chat_conversations USING GIN (messages);

-- Add comment
COMMENT ON COLUMN learning.ai_chat_conversations.messages IS
'Full conversation messages in JSONB format [{role, content, ...}]';

COMMIT;
