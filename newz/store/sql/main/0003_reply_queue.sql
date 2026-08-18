-- 0003_reply_queue — durable reply queue (v1's operator_inbox lesson,
-- ported as columns on messages rather than a parallel table).
-- Writer: the ambient loop (marks pending / replied / poisoned).
-- Reader: the queue drainer, which replays unanswered messages on boot and
-- retries failures with a poison-guard.

ALTER TABLE messages ADD COLUMN reply_status TEXT;      -- inbound: pending|replied|poisoned
ALTER TABLE messages ADD COLUMN reply_attempts INTEGER NOT NULL DEFAULT 0;

-- Backfill: an inbound message linked to an exchange episode was answered;
-- any other inbound message is still owed a reply.
UPDATE messages SET reply_status='replied'
  WHERE direction='in' AND episode_id IS NOT NULL;
UPDATE messages SET reply_status='pending'
  WHERE direction='in' AND episode_id IS NULL;

CREATE INDEX idx_messages_pending ON messages (reply_status, ts)
  WHERE reply_status='pending';
