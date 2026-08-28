"""The claim — the unit of being wrong (P3 epic E1.1).

A concern is a question the being pursues; a claim is an answer it commits to
in a form the world can refuse. The difference is the whole of Phase 1. The
being's grounding mix is 50% itself and 33% the operator, and nothing in that
loop can tell it that it is wrong about anything outside itself.

Four fields make a claim settleable, and the schema (0023) refuses a claim
missing any of them:

  claim                 what is asserted, specifically enough to fail
  resolution_condition  what would settle it, stated before the answer is known
  resolver              the world source that will say
  due_at                when to go and look

`resolver` is a source, not a judge: "the EIA weekly petroleum status report",
"the Fed's H.4.1 release", "the paper's published erratum". Rule 4 — the being
is not graded by the being — is enforced in the writer, because a claim the
substrate settles by opinion is the being marking its own homework with extra
steps.
"""

from __future__ import annotations

from dataclasses import dataclass

# What a resolution can say. Deliberately two: `held` and `contradicted`.
#
# There is no `ambiguous` outcome, and that is a decision rather than an
# omission. E1.3 fails closed — an unreadable source, a missing resolver or an
# answer that does not clearly settle the claim leaves it OPEN, to be looked at
# again. An `ambiguous` outcome would be a third way to close a claim without
# the world having said anything, and the being's record of error is exactly
# where a soft exit must not exist.
OUTCOMES = ("held", "contradicted")
STATUSES = ("open", "resolved")

# What a claim is about in time (E1.9, 2026-08-28).
#
# `forecast` is every claim written before this: something the world has not
# said yet, dated 2 to 45 days out. `retrodiction` is a claim about what is
# ALREADY the case and the being does not yet know — just as ungraded by the
# being, and settled on the next resolver pass instead of in a month.
#
# They are named apart because they test different things and must never be
# averaged: a forecast tests the being's model of where things are going, a
# retrodiction tests whether its assertions about the world are true. E1.10 is
# where the metric split lands; this is where the fact is recorded.
KINDS = ("forecast", "retrodiction")


@dataclass
class Claim:
    id: int | None
    claim: str
    resolution_condition: str
    resolver: str
    due_at: float
    provenance: str                    # concern:N | position:N | work:N | conversation:N
    kind: str = "forecast"             # forecast | retrodiction (E1.9)
    opened_at: float = 0.0
    status: str = "open"
    outcome: str | None = None
    settled_at: float | None = None
    settled_by: str | None = None      # the source actually consulted
    settled_note: str | None = None
    could_be_wrong: str | None = None   # what the other outcome looks like (R-35)
    # E1.3's honest bookkeeping: a claim tried and not settled is not the same
    # as one whose date has not arrived, and both are `open`.
    attempts: int = 0
    last_attempt_at: float | None = None
    last_failure: str | None = None

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def went_against_me(self) -> bool:
        """The read E1.4 acts on and E1.5 keeps forever."""
        return self.status == "resolved" and self.outcome == "contradicted"

    def is_due(self, now: float) -> bool:
        return self.is_open and self.due_at <= now

    @property
    def is_retrodiction(self) -> bool:
        """Already true when it was claimed, so due the moment it is opened."""
        return self.kind == "retrodiction"
