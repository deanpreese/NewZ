"""The research plane: what the system does about a gap once it sees one.

Phase 2 could answer "what does the record establish". This is what makes the
system go and look — investigations with exit conditions, tasks per evidence
lane, leads that are only ever leads, and resolvers whose silence is recorded as
carefully as their answers.
"""

from newz.research.investigations import (
    add_claim_to_investigation,
    close_investigation,
    open_investigation,
)
from newz.research.packets import evidence_packet
from newz.research.resolution import apply_retraction, record_resolution
from newz.research.tasks import expirable, generate_tasks, transition_task

__all__ = [
    "add_claim_to_investigation",
    "apply_retraction",
    "close_investigation",
    "evidence_packet",
    "expirable",
    "generate_tasks",
    "open_investigation",
    "record_resolution",
    "transition_task",
]
