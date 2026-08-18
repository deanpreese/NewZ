-- 0004_tg_message_id — Phase 0.4 slow-reply alignment.
-- Writer: the ambient loop (inbound persist). Reader: the drainer, which
-- passes it as reply_to so a late reply visibly anchors to the message it
-- answers when the thread has moved on.

ALTER TABLE messages ADD COLUMN tg_message_id INTEGER;
