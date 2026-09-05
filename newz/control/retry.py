"""Retry, backoff, and per-host pacing.

Three rules, and the first one is the one that matters: **most refusals are not
retryable.** A scheme that is not allowed will not become allowed, and an
address inside the house will not move. Retrying a policy refusal is how a
system spends its budget re-learning something it already knows, and how a
refusal quietly becomes a rate limiter instead of a decision.

What is retryable is the far side being temporarily unable rather than the
policy being unwilling: an error, a timeout, a rate limit. Backoff is
deterministic — no jitter — because `SPEC.md` section 13 asks for derivations
that reproduce, and a schedule nobody can predict is a schedule nobody can test.
The absence of jitter is safe here at ten reads a day against a catalog of
twenty; it would not be at scale, and that is a reversal condition rather than a
principle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from newz.domain.enums import AttemptOutcome, FetchRefusal

#: Refusals worth trying again: the source was unable, not disallowed.
RETRYABLE_REFUSALS: frozenset[FetchRefusal] = frozenset(
    {FetchRefusal.RATE_LIMITED, FetchRefusal.TIMEOUT}
)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: int = 60
    multiplier: int = 4
    max_delay_seconds: int = 3_600
    #: The politeness floor between two reads of the same host.
    min_host_interval_seconds: int = 30

    def is_retryable(self, outcome: AttemptOutcome, refusal: FetchRefusal | None) -> bool:
        if outcome is AttemptOutcome.ERROR:
            return True
        if outcome is AttemptOutcome.REFUSED:
            return refusal in RETRYABLE_REFUSALS
        return False

    def delay_after(self, attempt: int) -> int:
        """Seconds to wait after `attempt` failures. Deterministic and capped."""
        if attempt < 1:
            raise ValueError("attempts are counted from 1")
        delay = self.base_delay_seconds * (self.multiplier ** (attempt - 1))
        return min(delay, self.max_delay_seconds)

    def due_at(self, last_attempt: datetime, attempt: int) -> datetime:
        return last_attempt + timedelta(seconds=self.delay_after(attempt))

    def exhausted(self, attempts: int) -> bool:
        return attempts >= self.max_attempts


def attempts_for(store, source_revision_id: str) -> int:
    row = store.one(
        "SELECT COUNT(*) AS n FROM attempts a JOIN operations o ON o.id = a.operation_id "
        "WHERE o.source_revision_id = ? AND a.outcome != 'retained'",
        source_revision_id,
    )
    return row["n"] if row else 0


def last_attempt_at(store, host: str) -> datetime | None:
    """When this host was last contacted, whatever the outcome.

    Pacing counts contact rather than success: a host that refuses quickly is
    still a host being asked.
    """
    row = store.one(
        "SELECT MAX(started_at) AS at FROM attempts "
        "WHERE url LIKE ? OR url LIKE ?",
        f"https://{host}/%",
        f"http://{host}/%",
    )
    if row is None or row["at"] is None:
        return None
    return datetime.fromisoformat(row["at"])


def effective_interval(policy: RetryPolicy, crawl_delay: float | None) -> float:
    """The longer of our floor and what the site asked for.

    A shorter crawl-delay is not a licence to go faster than our own floor, and
    a longer one is not a suggestion. One real source in the first survey asks
    for two minutes, four times the floor, and honouring the larger number is
    the whole of the rule.
    """
    return max(float(policy.min_host_interval_seconds), float(crawl_delay or 0))


def pacing_refusal(
    store,
    host: str,
    now: datetime,
    policy: RetryPolicy | None = None,
    crawl_delay: float | None = None,
) -> FetchRefusal | None:
    """Refuse a read that would arrive too soon after the last one."""
    policy = policy or RetryPolicy()
    previous = last_attempt_at(store, host)
    if previous is None:
        return None
    elapsed = (now - previous).total_seconds()
    # A negative elapsed time means the clock moved backwards, which fails
    # closed here: a clock that went backwards is not a licence to read again.
    if elapsed < effective_interval(policy, crawl_delay):
        return FetchRefusal.RATE_LIMITED
    return None
