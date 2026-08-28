"""Metrics composed from what already exists (P4 epic E3.7).

**The shortfall was never collection.** Four of TRUE_NORTH §10's six checkable
items are ratios of figures the store already holds. Counting instruments rather
than derivable quantities is what made the gap look larger than it was, and
this module is the correction:

  volume_against_development       §10 "activity, memory growth, or output volume"
  restatement_rate                 §10 "personality consistency without development"
  consequence_rate                 §10 "novelty without relevance or consequence"
  autonomy_against_world_grounding §10 "autonomy without perspective or purpose"

Each names the failure directly. Volume rising while development is flat is
§10's first item happening; a restatement rate near 1 is the second; advances
accumulating while nothing is ever settled is the third; acting a great deal
while almost nothing held comes from outside is the fourth.

**A derived metric cannot be more trustworthy than what it is derived from.**
`grade_of_derivation` takes the weakest input grade, and a test asserts the
registry agrees — so a mechanical numerator over a model-graded denominator is
model-graded, and cannot quietly carry a decision that neither input could.
That rule is the reason this module exists as code rather than as four more
queries: the composition is where a grade would otherwise be lost.

**A declared input is now the only input** *(R-37c, fixed 2026-08-20)*. Until
today each derivation declared what it was composed from in `DERIVED_FROM` and
then queried the store for whatever it liked, and the two disagreed in three of
four cases: `consequence_rate` declared `advance_acceptance` and `claims_opened`
and read `concern_advances` and `resolutions`; `autonomy_against_world_grounding`
declared two inputs and used three quantities; `volume_against_development`
declared a *share* and divided by a *count*. The grades came out defensible by
luck.

Correcting the declarations would have left a second hand-maintained list
drifting from the thing it describes — the E2.11 problem, inside the module
built to stop grades being lost in composition. So a derivation is now a pure
function of an `Inputs` mapping that exposes **only** the names in its
`DERIVED_FROM` row, and reading anything else raises. The declaration is no
longer a claim about the implementation; it is the implementation's argument
list, and it cannot be wrong quietly.

**What this does not fix**, recorded rather than implied: nothing here checks
that a *primitive* metric's implementation matches its registry text.
`nights_slept` is "Perspective versions written in the window" in the registry
and whatever `mechanical.py` does in fact. The derivation layer was where a
grade could be laundered silently; the primitives are where a number can be
wrong loudly, which is a different and easier failure.
"""

from __future__ import annotations

from collections.abc import Mapping, Iterator

from newz.evidence.mechanical import Value

# Weakest to strongest. Not a quality ranking — a statement about what may carry
# a decision. Only `mechanical` may, so any non-mechanical input makes the
# derivation non-mechanical too (Rule 4, Rule 7).
#
# **`known-biased` sits above `mixed`, which is a judgment worth stating.** A
# known bias is characterised: R-15 says imported episodes are uniformly
# `self`, so a reader knows which way the figure leans and by roughly what.
# `mixed` has a model judgment somewhere upstream — added/revised labels applied
# at consolidation — and nothing characterises which way that leans. A named
# distortion is more tractable than an unnamed judgment, and Rule 4's concern is
# with judgments rather than with error.
GRADE_ORDER = ("model-graded", "mixed", "known-biased", "mechanical")

# Every derived metric and what it is composed from — which is also, now, the
# whole of what its function can see.
DERIVED_FROM = {
    "volume_against_development": ("episodes_recorded", "perspective_items_developed"),
    "restatement_rate": ("perspective_novelty",),
    "consequence_rate": ("claims_settled", "retrodictions_settled",
                         "advances_offered"),
    "autonomy_against_world_grounding": (
        "advances_offered", "pieces_written", "self_grounding_share"),
}


class UndeclaredInput(KeyError):
    """A derivation reached for a figure it does not declare."""


class Inputs(Mapping):
    """The declared inputs of one derivation, and nothing else.

    The point is the `KeyError`: a derivation that grows a new input has to
    declare it in `DERIVED_FROM`, which is what the grade is computed from and
    what the registry is checked against. Silence is not an option the code has.
    """

    def __init__(self, metric: str, values: Mapping[str, Value]):
        self._metric = metric
        self._declared = tuple(DERIVED_FROM[metric])
        missing = [n for n in self._declared if n not in values]
        if missing:
            raise KeyError(
                f"{metric} declares {missing} and the nightly pass did not "
                "produce them — a declared input must be a metric that exists")
        self._values = {n: values[n] for n in self._declared}

    def __getitem__(self, name: str) -> Value:
        if name not in self._declared:
            raise UndeclaredInput(
                f"{self._metric} read {name!r}, which is not in its DERIVED_FROM "
                f"row {self._declared}. Declare it there — the grade and the "
                "registry check are both computed from that row.")
        return self._values[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._declared)

    def __len__(self) -> int:
        return len(self._declared)


def grade_of_derivation(inputs) -> str:
    """The weakest grade among the inputs. A ratio is only as good as its parts."""
    return min(inputs, key=lambda g: GRADE_ORDER.index(g))


def _ratio(numerator: Value, denominator: Value, *, no_denominator: str,
           digits: int = 3) -> Value:
    """A ratio, or the honest reason there isn't one.

    An unreadable input makes the ratio unreadable and says which one — a
    derivation cannot be measured over a figure that was not.
    """
    for v in (numerator, denominator):
        if v.unreadable:
            return Value(unreadable=v.unreadable)
    if not denominator.value:
        return Value(unreadable=no_denominator)
    return Value(round(numerator.value / denominator.value, digits))


def volume_against_development(i: Inputs) -> Value:
    """Episodes recorded per Perspective item added or revised.

    §10's "activity, memory growth, or output volume". A rising number is the
    being doing more and holding no more for it — which is the shape of the
    failure, not a proxy for it.
    """
    return _ratio(
        i["episodes_recorded"], i["perspective_items_developed"],
        no_denominator=(
            "no Perspective item was added or revised in the window — the ratio "
            "has no denominator, and reporting the episode count alone would be "
            "the volume figure §10 warns about with nothing to divide it by"))


def restatement_rate(i: Inputs) -> Value:
    """1 − novelty: the share of what is held that is being restated.

    §10's "personality consistency without development". Already computed by
    the Perspective window; the derivation is only that it be looked at.
    """
    novelty = i["perspective_novelty"]
    if novelty.unreadable:
        return Value(unreadable=novelty.unreadable)
    return Value(round(1.0 - novelty.value, 4))


def _sum_counts(*values: Value) -> Value:
    """Add counts, propagating UNREADABLE rather than treating it as zero.

    INV-044's discipline in arithmetic: a numerator missing one of its terms is
    not a smaller numerator, it is a figure nobody can read.
    """
    total = 0.0
    for v in values:
        if v is None or getattr(v, "unreadable", None):
            return Value(unreadable=(getattr(v, "unreadable", None)
                                     or "a term of the sum is missing"))
        if v.value is None:
            return Value(unreadable="a term of the sum has no value")
        total += v.value
    return Value(total)


def consequence_rate(i: Inputs) -> Value:
    """Claims of EITHER kind settled per advance accepted.

    §10's "novelty without relevance or consequence". Advances accumulating
    while nothing is ever settled is that item, measured — and until 2026-09-02
    it is exactly zero, which is S1-E stated as a ratio.

    **Definition 3, and this is the one place E1.10 changes a meaning.** The
    other claim metrics are scoped to `kind='forecast'` and keep their series
    unbroken, because every row before migration 0045 was a forecast in fact.
    This one is different: consequence is consequence whichever kind produced
    it — a retrodiction settled against the world is the world telling the
    being something it did not manufacture, which is exactly what §10's item
    asks about — so counting only forecasts here would understate the thing the
    metric exists to measure. Adding the second numerator ends the v2 series and
    `definitions.sync` records the seam.

    The two kinds are still never averaged: they are separate series everywhere
    they are reported, and this is a sum rather than a mean.
    """
    settled = _sum_counts(i["claims_settled"], i["retrodictions_settled"])
    return _ratio(settled, i["advances_offered"], digits=4,
                  no_denominator="no advance was accepted in the window")


def autonomy_against_world_grounding(i: Inputs) -> Value:
    """Unprompted acts per unit of world-grounded position.

    §10's "autonomy without perspective or purpose". Acting a great deal while
    almost nothing held comes from outside is that item — and it is why the
    denominator is the WORLD share rather than the count of positions: a being
    can hold a great many positions and still be talking to itself.
    """
    advances, pieces, own = (i["advances_offered"], i["pieces_written"],
                             i["self_grounding_share"])
    for v in (advances, pieces, own):
        if v.unreadable:
            return Value(unreadable=v.unreadable)
    world_share = 1.0 - own.value
    if world_share <= 0:
        return Value(unreadable=(
            "nothing held is grounded outside the being — the ratio has no "
            "denominator, and that state is itself the finding"))
    return Value(round((advances.value + pieces.value) / world_share, 2))


DERIVATIONS = {
    "volume_against_development": volume_against_development,
    "restatement_rate": restatement_rate,
    "consequence_rate": consequence_rate,
    "autonomy_against_world_grounding": autonomy_against_world_grounding,
}


def all_derived(values: Mapping[str, Value]) -> dict[str, Value]:
    """Every derivation, over the primitives the same nightly pass produced.

    It takes values rather than a connection **because a derivation may not go
    to the store**: an input it can query is an input it can use without
    declaring, which is R-37c's fault with a new spelling.
    """
    return {name: fn(Inputs(name, values)) for name, fn in DERIVATIONS.items()}
