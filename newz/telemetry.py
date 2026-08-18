"""Budget telemetry (S2 §14.4, P2 Phase 1.4) — the economy read, not excavated.

v1's finding that 82% of its cognition went to ingest bookkeeping had to be
dug out of a call log after the fact. Here token share by function is
computed continuously from `logs/llm_calls.jsonl`, which every call writes.

The number that matters downstream is S2 §9.1's diet invariant:

    ingest ≤ deliberation + consolidation   (rolling window)

Before Phase 2 there is no ingest, and the invariant's right-hand side is
what sets the ceiling on how much reading the being may ever do. This module
reports both the current shares and the ingest budget they imply, so the
diet is sized from measurement rather than guessed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

# Which functions count on each side of the S2 §9.1 invariant.
INGEST = {"ingest", "extraction", "classification", "noticing"}
EARNS_INGEST = {"sleep", "deliberation"}   # consolidation + deliberation

# S2 §9.1's OTHER ceiling, in the same sentence as the ratio:
#
#   "ingest cognition may not exceed deliberation + consolidation cognition
#    over a rolling window (target: ≤50% of tokens; measured continuously;
#    breach pauses ingest, never deliberation)"
#
# Those two are the same number only if deliberation + consolidation is
# roughly half the being's cognition. Measured 2026-08-16 it is NINE PERCENT:
# conversation 42%, gate 15%, unspecified 17%, ingest 11%, deliberation 9%.
# So the ratio alone caps ingest at about a fifth of the share the same
# sentence names as the target.
#
# P2 Phase 2.4 required this be sized once deliberation existed — "size the
# diet last against what the denominator actually is; do not set the diet
# from an estimate again" — and that step had never run.
INGEST_SHARE_CEILING = 0.50


@dataclass
class BudgetReport:
    window_hours: float
    calls: int = 0
    tokens: int = 0
    by_function: dict[str, dict] = field(default_factory=dict)

    @property
    def ingest_tokens(self) -> int:
        return sum(v["tokens"] for k, v in self.by_function.items() if k in INGEST)

    @property
    def earning_tokens(self) -> int:
        return sum(v["tokens"] for k, v in self.by_function.items() if k in EARNS_INGEST)

    @property
    def share_ceiling_tokens(self) -> int:
        """S2 §9.1's stated target, as an absolute number of tokens."""
        return int(self.tokens * INGEST_SHARE_CEILING)

    def ingest_ceiling(self) -> int:
        """How much reading is permitted — the LOOSER of §9.1's two ceilings.

        Sized 2026-08-16, which is P2 Phase 2.4's outstanding step. The ratio
        alone was written for an economy where deliberation and consolidation
        are roughly half of cognition; they are nine percent, because
        conversation and the gate are fifty-seven. Taking the looser of the
        two is reading §9.1's sentence as written rather than reading only its
        first clause.

        **This is not the loosening P2 forbade.** P2's "the resolution is
        sequencing, not loosening" was written 2026-08-11, when deliberation
        did not exist and a circular start could only be broken by building
        it. Deliberation is built; the sequencing is done; the sizing it
        deferred to is this.

        **And the diet is not the only bound**, which is what makes it safe.
        Triage keeps ≤3 items a harvest, MAX_EXTRACTIONS is 4,
        MAX_RESULTS_PER_SOURCE is 2, feeds have poll intervals, the share cap
        holds any outlet to 10%, and R1 stops re-reading. Those bound the RATE
        by construction. The diet had become a second bound that bit first and
        hardest; raising it lets the structural bounds be the operative ones,
        which is what they were designed to be.

        v1's failure was 82% ingest against 4.6% life — an 18:1 ratio. A 50%
        ceiling is 1:1 at worst, and far below that in practice.

        **Zero earning is still zero ceiling**, and that is not an edge case
        to tidy — it is P2 §1's arithmetic, which the first draft of this
        change broke and two existing tests caught: "before sleep and
        deliberation exist that denominator is zero, so any ingest whatsoever
        breaches… feeds before Phase 1 are not merely unwise, they are
        unsatisfiable without disabling the governor." Without this guard a
        being that had only ever held conversations could read half of them
        back, having never thought at all, which repeals the whole point of
        §9.1 rather than sizing it. Reading is still earned by thinking; what
        changed is how much a given amount of thinking buys.
        """
        if self.earning_tokens <= 0:
            return 0
        return max(self.earning_tokens, self.share_ceiling_tokens)

    def invariant_holds(self) -> bool:
        return self.ingest_tokens <= self.ingest_ceiling()

    def ingest_headroom(self) -> int:
        """Tokens of reading the being may still spend in this window."""
        return max(0, self.ingest_ceiling() - self.ingest_tokens)

    def binding_ceiling(self) -> str:
        """Which of the two ceilings is currently the operative one."""
        return ("share" if self.share_ceiling_tokens > self.earning_tokens
                else "ratio")

    def share(self, function: str) -> float:
        return self.by_function.get(function, {}).get("tokens", 0) / self.tokens \
            if self.tokens else 0.0


def diet_line(b: BudgetReport) -> str:
    """The §9.1 line, naming the ceiling that actually applied.

    It used to read `ingest {x} <= earning {y}  headroom {z}` and that stopped
    being true when #33 sized the diet on 2026-08-16. Since then ingest is
    permitted below the LOOSER of the earning sum and §9.1's stated 50%-of-
    tokens target, so the line could print `736,948 <= 422,402` beside a
    positive headroom — an arithmetic contradiction on the face of a check
    that was working correctly. The verdict was always right; only the words
    were wrong, which is the worse failure for an instrument, because it is
    the words that are read. It made me distrust a correct number twice in
    one day before I looked at the code.

    Kept as a separate function so it can be tested at all: health.py had no
    tests, which is exactly how the stale wording survived the change that
    invalidated it.
    """
    if b.ingest_ceiling() <= 0:
        return (f"ingest {b.ingest_tokens:,} — nothing earned yet, so no "
                f"ingest is permitted")
    verb = "<=" if b.invariant_holds() else ">"
    return (f"ingest {b.ingest_tokens:,} {verb} {b.binding_ceiling()} ceiling "
            f"{b.ingest_ceiling():,}  headroom {b.ingest_headroom():,}")


def read_budget(log_path: Path, window_hours: float = 168.0) -> BudgetReport:
    report = BudgetReport(window_hours=window_hours)
    if not Path(log_path).exists():
        return report
    floor = time.time() - window_hours * 3600
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("ts", 0) < floor:
                continue
            fn = row.get("function") or "unspecified"
            tok = (row.get("prompt_tokens") or 0) + (row.get("completion_tokens") or 0)
            slot = report.by_function.setdefault(
                fn, {"calls": 0, "tokens": 0, "seconds": 0.0})
            slot["calls"] += 1
            slot["tokens"] += tok
            slot["seconds"] += row.get("duration_s") or 0.0
            report.calls += 1
            report.tokens += tok
    return report
