"""The judgment calls the principles do not settle.

`PLAN.md` Phase 0 item 6: deriving roughly two thousand capability cells from
about ten stated principles is a design task, and every judgment call the
principles do not settle is recorded here as a decision rather than resolved
silently in code.

A rule that merely restates a rule in `SPEC.md` carries `spec_ref` and no
decision id. A rule that had to choose between defensible readings carries a
decision id, and the reasoning is written out — including what it costs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Decision:
    id: str
    question: str
    decision: str
    reasoning: str
    cost: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "cost": self.cost,
        }


DECISIONS: tuple[Decision, ...] = (
    Decision(
        id="D-001",
        question="May an assertion typed `inference` support or contradict a claim?",
        decision="No. `inference` admits `contextualizes` only, for every role.",
        reasoning=(
            "An inference is the source's reasoning over evidence, not the evidence. "
            "Admitting it would let a chain of reasoning enter the graph as a basis "
            "and be counted against a threshold, which is how repetition of one "
            "underlying observation becomes apparent corroboration. Symmetry under "
            "SPEC 7.3 rule 7 makes this bind refutation identically, which is the "
            "half that costs something: a skeptic's well-argued inference is "
            "contextual material here, not a countable contradiction."
        ),
        cost=(
            "Strong analytical work is demoted to context unless its measurements "
            "or documented findings are extracted as their own assertions. That is "
            "extra extraction work, and it is the intended shape: the measurement "
            "is the evidence, the argument about it is not."
        ),
    ),
    Decision(
        id="D-002",
        question="May an assertion typed `prediction` support or contradict a claim?",
        decision="No. `prediction` admits `claimant_says` and `contextualizes` only.",
        reasoning=(
            "A prediction is about a state of the world that has not happened. It can "
            "establish that someone predicted something — which is an attribution "
            "claim, reached by `claimant_says` — and nothing else. A forecast claim is "
            "settled at its horizon by a resolver, never by an earlier prediction "
            "agreeing with it."
        ),
        cost="None identified.",
    ),
    Decision(
        id="D-003",
        question="What may support a capability-or-performance claim?",
        decision=(
            "Only assertions typed `measurement`. A `documented_event` — a patent, a "
            "specification, a press release — cannot support or contradict one."
        ),
        reasoning=(
            "SPEC 7.3 rule 3 says a patent proves a filing and its contents, not "
            "performance. The general form of that rule is that a performance claim "
            "needs a measurement of the performance. Encoding it as a rule about "
            "patents specifically would leave the same error available through any "
            "other document type."
        ),
        cost=(
            "A demonstration attested in a document but never measured cannot reach "
            "`supported`. It reaches `reported`, with the document-existence claim "
            "beside it fully settled, which is the honest decomposition."
        ),
    ),
    Decision(
        id="D-004",
        question="What may support an identity-or-wrongdoing-allegation claim?",
        decision=(
            "Assertions typed `documented_event` from an adjudicator or a primary "
            "record. Everything else is refused, and an assertion that alleges is "
            "typed `allegation` however official the document carrying it is."
        ),
        reasoning=(
            "SPEC 7.3 rule 4 says a complaint proves an allegation was filed, not "
            "guilt. The control is assertion typing rather than source role: a filed "
            "complaint is a real primary record, and what makes it not proof of guilt "
            "is that what it contains is an allegation. `documented_event` is reserved "
            "for what a record establishes as having occurred."
        ),
        cost=(
            "It puts weight on extraction typing an assertion correctly. The controlled "
            "case for a complaint misused as proof of guilt exists to hold that line, "
            "and a mistyping there is a defect with a permanent fixture."
        ),
    ),
    Decision(
        id="D-005",
        question="What may an assertion typed `testimony` support?",
        decision="Attribution and event-or-observation claims only.",
        reasoning=(
            "SPEC 7.3 rule 2: a witness report is evidence that the report occurred, "
            "not by itself that the external event occurred. `By itself` locates the "
            "constraint at the threshold rather than at admission, so testimony is "
            "admitted for the event claim and cannot promote it alone — an ordinary "
            "promotion needs two independent bases including one primary, empirical, "
            "or adjudicative record. For measurement, causal, and capability claims "
            "testimony is refused outright, because no quantity of it reaches those."
        ),
        cost=(
            "A witness account of a measurement is contextual material until the "
            "measurement itself is retained. For a system that investigates anomalous "
            "phenomena this is the most consequential single refusal in the matrix."
        ),
    ),
    Decision(
        id="D-006",
        question="What may settle a document-existence claim?",
        decision=(
            "`documented_event` assertions from a primary record or an adjudicator."
        ),
        reasoning=(
            "The claim is that a document exists and says what it is said to say. The "
            "record itself establishes that; a description of it does not."
        ),
        cost="A document known only through description stays `reported`.",
    ),
    Decision(
        id="D-007",
        question="May the context roles carry countable evidence?",
        decision=(
            "No. `historical_context` and `general_context` admit `claimant_says` and "
            "`contextualizes` only."
        ),
        reasoning=(
            "SPEC 5.1 gives each role a maximum ordinary use, and for these two it is "
            "to supply provenance, chronology, interpretation, and background. A "
            "background source that turns out to carry a primary observation is "
            "miscatalogued, and the repair is a catalog correction with a recorded "
            "reason — not a wider capability for the role."
        ),
        cost=(
            "Encyclopedic and survey material never counts, however accurate. That is "
            "the intended posture: it is the trail behind the claim, not the claim."
        ),
    ),
    Decision(
        id="D-008",
        question=(
            "Does an assertion typed `allegation` support the attribution claim that "
            "the allegation was made?"
        ),
        decision="Yes, and nothing else.",
        reasoning=(
            "`X alleged Y` is exactly an attribution claim, and the allegation is the "
            "record of it. Refusing it here would leave no way to establish that "
            "something was alleged, which is the fact the system most needs to hold "
            "accurately and separately from whether it is true."
        ),
        cost="None identified.",
    ),
    Decision(
        id="D-009",
        question="What counts as strong provenance for the R2 threshold?",
        decision=(
            "Bases carried by the primary-record, empirical-study, or adjudicator "
            "roles. R2 requires two independent bases of which at least two are "
            "strong-provenance; R0-R1 requires two of which at least one is."
        ),
        reasoning=(
            "SPEC 7.3 states the R0-R1 rule explicitly and says every other R2 claim "
            "requires two independent countable bases `with strong provenance`, "
            "without defining the phrase. Reading it as raising the count of strong "
            "bases from one to two is the only reading that makes R2 stricter than "
            "R0-R1 rather than identical to it."
        ),
        cost=(
            "Claims about active institutions will sit at `provisional_support` "
            "longer. That is the intended direction of the error at R2."
        ),
    ),
    Decision(
        id="D-010",
        question="How does the R3 threshold combine its two requirements?",
        decision=(
            "Two independent bases, of which at least one is carried by a primary "
            "record or an adjudicator."
        ),
        reasoning=(
            "SPEC 7.3 requires `a direct primary or adjudicative basis plus an "
            "independent countable basis`, which is two groups with a role constraint "
            "on one of them. The second basis carries no role constraint beyond being "
            "countable at all."
        ),
        cost="None identified; this is close to a transcription.",
    ),
    Decision(
        id="D-011",
        question=(
            "When independence between two resolved bases is unknown, what happens to "
            "the count?"
        ),
        decision=(
            "The two collapse into one for counting. Collapsing is transitive: bases "
            "are grouped by union, so three bases with one justified pair among them "
            "count as two, not three."
        ),
        reasoning=(
            "SPEC 7.2 requires unknown independence to collapse a pair without "
            "invalidating either edge. Transitivity is the conservative closure: "
            "counting a chain of partially-justified pairs as fully distinct would let "
            "a threshold be met by a set no single justification covers."
        ),
        cost=(
            "A large set with sparse justification counts low, and the pilot reports "
            "the share of claims held below promotion by unknown independence alone so "
            "that this shows up as a design finding if it is unsatisfiable in practice."
        ),
    ),
    Decision(
        id="D-012",
        question=(
            "Does membership of a shared independence group void a recorded "
            "justification?"
        ),
        decision="Yes, including an operator-verified one.",
        reasoning=(
            "SPEC 7.2 says independence-group membership blocks independence and never "
            "establishes it. Letting a justification override the block would make the "
            "catalog's syndication knowledge advisory, and syndication is the specific "
            "mechanism by which copied stories look like corroboration."
        ),
        cost=(
            "Two genuinely separate observations published by co-owned outlets count "
            "once. The repair is a catalog correction to the grouping, which is an "
            "operator action with a recorded reason, not a per-claim override."
        ),
    ),
    Decision(
        id="D-013",
        question=(
            "When may an adjudicative record settle a claim under the single-record "
            "exception?"
        ),
        decision=(
            "Only when the edge records that the adjudicator's declared scope covers "
            "the claim. Unknown scope coverage fails closed."
        ),
        reasoning=(
            "SPEC 7.3 admits the exception `within that adjudicator's declared scope`, "
            "and SPEC 5.1 says declared scope carries decision weight in exactly this "
            "one place. Since scope is recorded free text rather than an enumeration, "
            "the coverage judgment cannot be computed from it and is carried on the "
            "edge as a recorded boolean."
        ),
        cost=(
            "Someone must record the coverage judgment. Leaving it unrecorded is safe "
            "in the sense that the claim does not promote, and unsafe in the sense "
            "that a refuted allegation about a living person stays visibly unrefuted, "
            "which is why the R3 controlled case pins it."
        ),
    ),
    Decision(
        id="D-014",
        question="Which evidence lanes does each claim kind require?",
        decision=(
            "The mapping in `newz.policy.lanes`. Normative propositions require none, "
            "because they never promote."
        ),
        reasoning=(
            "`indeterminate` means every required lane looked and found nothing, so "
            "the required set decides what that result asserts. The mapping asks for "
            "the lanes whose silence is informative for that kind of claim: a "
            "counterpart and a skeptical reading wherever a claim could be corroborated "
            "or challenged, a resolver wherever an outside authority settles the "
            "question."
        ),
        cost=(
            "A wider required set makes `indeterminate` rarer and slower to reach. "
            "That is the intended trade: the failure this guards against is a claim "
            "presenting as exhaustively investigated when two lanes were never opened."
        ),
    ),
    Decision(
        id="D-015",
        question="Are edges at R4 refused, or admitted and withheld from publication?",
        decision="Refused at admission.",
        reasoning=(
            "SPEC 8 makes R4 metadata quarantine only, never reproduced or "
            "operationalized. An admitted edge carries a verified span, which is "
            "retained content, and a countable edge is quotable on a claim card. "
            "Refusing at admission keeps the payload out of every downstream path "
            "rather than relying on each of them to remember."
        ),
        cost=(
            "The graph cannot represent why an R4 item was quarantined beyond the "
            "refusal record and its metadata. That is the intended limit."
        ),
    ),
)

BY_ID: dict[str, Decision] = {d.id: d for d in DECISIONS}


def get(decision_id: str) -> Decision:
    return BY_ID[decision_id]
