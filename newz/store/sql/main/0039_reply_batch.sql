-- 0039_reply_batch — R-37d, P4 W2.
-- Writer: newz/ambient/loop.py::_work_batch, once per successful reply.
-- Reader: newz/evidence/agreement.py::_pairs, which groups exchanges by it.
--
-- **An exchange is one reply and everything it answered.** The drainer
-- coalesces every pending message into a single reply — it logs when it does —
-- and `_pairs` reconstructed the pairing by taking the next outbound message
-- after each inbound one. Three messages answered by one reply became three
-- exchanges judged against the same text, inflating whatever the denominator
-- said by the being's own batching behaviour.
--
-- The drainer knows the batch. It was throwing the fact away and the
-- instrument was inferring it back, badly. This records it.
--
-- Expand-only: the column is added, nothing is dropped or renamed, and rows
-- written before this migration carry NULL. Those exchanges are never judged —
-- backfilling them under the old pairing would fill the first window with
-- exactly the figure this exists to remove (W2, forward-only).

ALTER TABLE messages ADD COLUMN answered_by INTEGER REFERENCES messages(id);

CREATE INDEX idx_messages_answered_by ON messages (answered_by);
