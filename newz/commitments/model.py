"""The commitment — identity in a form that can be broken (P4 epic E4.1).

A concern is a question the being pursues. A claim is an answer it commits to
in a form the world can refuse. A **commitment** is neither: it is what the
being holds itself to across both, and the thing that distinguishes it from a
preference is that something could show it had stopped.

Three fields, and 0041 refuses a row missing either of the first two:

  statement   what it keeps caring about, or what it refuses to do
  falsifier   what would show it had stopped — checkable, not felt
  kind        which of those two this is

**Why the falsifier is mandatory.** The being's `who_i_am` today is four items,
three of which are things that happened to it and were recovered afterwards by
a model reading its own episodes. Nothing there could be broken, so nothing
there is being kept. INV-034's discipline — a terminus something can reach —
is carried by concerns as `closing_condition` and by claims as
`resolution_condition`, and this is its third application.

**The two kinds are falsified in opposite directions**, which is why they are
not one column with a flag. A `keeps_caring` commitment is broken by ABSENCE:
the being stopped doing the thing. A `refuses_to_do` commitment is broken by
PRESENCE: the being did it once. Counting them together would average a
direction with a bound.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# keeps_caring: a direction — what it will keep spending itself on.
# refuses_to_do: a bound — what it will not do even when it would be easier.
KINDS = ("keeps_caring", "refuses_to_do")

# standing: live. revised / abandoned: E4.2's, and nothing in E4.1 writes them.
STATUSES = ("standing", "revised", "abandoned")


@dataclass
class Commitment:
    id: int | None
    kind: str
    statement: str
    falsifier: str
    provenance: str                     # perspective:N | work:N | concern:N
    ts: float = 0.0
    status: str = "standing"
    # Which episodes the being said it drew on (E4.3). Resolved from indices
    # the door returns, never inherited from the material it was shown — see
    # migration 0042 for why the union would have suppressed INV-033's flag.
    evidence: list[str] = field(default_factory=list)
    constitution_version: int | None = None
    perspective_version: int | None = None

    @property
    def is_standing(self) -> bool:
        return self.status == "standing"

    @property
    def is_a_bound(self) -> bool:
        """True for what it refuses to do — broken by presence, not absence."""
        return self.kind == "refuses_to_do"
