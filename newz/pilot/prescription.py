"""The diet, made executable: what twenty slots the specification asks for.

`SPEC.md` section 3 sets the topic menu targets and section 5.2 sets the role
distribution, and between them the pilot slate is already prescribed. Nobody has
to decide that four of the twenty should be UAP sources or that six should be
primary or adjudicative — the documents said so, and this derives it.

Two properties matter more than the arithmetic.

**The allocation is deterministic and shows its working.** Twenty slots against
eight weighted topics does not divide evenly, so the remainder is allocated by
the largest-remainder method and the derivation is reported. An operator asking
"why four UAP slots" gets 18% of 20 is 3.6, and the fourth came from the largest
remainder.

**The two tables agree, and the test says so.** Section 5.1's scheduling buckets
(25/30/20/15/10) and section 5.2's slot counts (5/6/4/3/2 of twenty) are the
same distribution stated twice. If they ever diverge, that is a specification
defect rather than a rounding question, and it should fail here loudly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.pilot.catalog_review import REQUIRED_SLOTS, REQUIRED_TOPICS

#: `SPEC.md` section 3. The offered discovery menu targets.
TOPIC_TARGETS: dict[str, float] = {
    "uap_and_aerospace_anomalies": 0.18,
    "psi_and_consciousness_claims": 0.15,
    "alternative_physics_and_energy": 0.15,
    "forteana_cryptids_and_anomalous_natural_events": 0.12,
    "anomalous_history_and_archaeology": 0.10,
    "declassified_material_and_historical_secrecy": 0.10,
    "metascience_methods_and_replication": 0.10,
    "general_scientific_and_institutional_context": 0.10,
}

#: `SPEC.md` section 5.1. The same distribution as section 5.2's slot counts,
#: stated as scheduling shares. Asserted equal in the tests.
BUCKET_TARGETS: dict[str, float] = {
    "claimant_or_firsthand": 0.25,
    "primary_or_adjudicative": 0.30,
    "empirical_or_replication": 0.20,
    "skeptical_or_forensic": 0.15,
    "historical_or_general_context": 0.10,
}

SLATE_SIZE = 20


@dataclass(frozen=True, slots=True)
class SlotSpec:
    """One slot the diet asks for: a bucket and a topic, and why."""

    index: int
    bucket: str
    topic: str
    rationale: str

    def as_record(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "bucket": self.bucket,
            "topic": self.topic,
            "rationale": self.rationale,
        }


def topic_allocation(size: int = SLATE_SIZE) -> tuple[dict[str, int], list[str]]:
    """Allocate slots across topics by largest remainder, and show the working."""
    exact = {topic: share * size for topic, share in TOPIC_TARGETS.items()}
    floors = {topic: int(value) for topic, value in exact.items()}
    remaining = size - sum(floors.values())

    # Ties broken by topic name so the allocation is the same every run.
    ranked = sorted(
        exact.items(), key=lambda item: (-(item[1] - int(item[1])), item[0])
    )
    working = [
        f"{topic}: {TOPIC_TARGETS[topic]:.0%} of {size} is {value:.2f}"
        for topic, value in sorted(exact.items())
    ]
    for topic, _ in ranked[:remaining]:
        floors[topic] += 1
        working.append(f"{topic}: +1 from the largest remainder")

    # Every topic must appear: SPEC 5.2 requires all eight covered, and a
    # share small enough to floor to zero would silently drop one.
    for topic in TOPIC_TARGETS:
        if floors[topic] == 0:
            raise ValueError(
                f"{topic} allocated no slot; all eight initial topics must be covered"
            )
    return floors, working


#: Buckets whose bases can carry a promotion. `SPEC.md` 7.3: an ordinary R0-R1
#: promotion needs at least one primary, empirical or adjudicative basis, so a
#: topic with neither can never reach `supported` however much it reads.
EVIDENCE_WEIGHTED = frozenset({"primary_or_adjudicative", "empirical_or_replication"})

SKEPTICAL = "skeptical_or_forensic"
CLAIMANT = "claimant_or_firsthand"

#: A topic with at least this many slots gets the full symmetrical treatment:
#: a claimant, a skeptic, and something that can carry a promotion.
#:
#: The threshold does the allocating rather than a judgment about which fields
#: deserve a claimant. Five claimant slots cannot cover eight topics, so some
#: topic goes without one, and the menu targets already say which topics matter
#: most — the three the specification weights heaviest are the three that get
#: represented from both sides. `TRUE_NORTH.md` asks for a claimant's strongest
#: actual position to be recorded and for support and refutation to face the
#: same burden; below the threshold, neither is possible, and that is a stated
#: cost rather than an oversight.
CONTESTED_THRESHOLD = 3
SKEPTICAL_THRESHOLD = CONTESTED_THRESHOLD


def _score(assignment: dict[str, dict[str, int]], allocation: dict[str, int]) -> tuple[int, ...]:
    """How well an assignment serves the specification, highest first.

    Lexicographic, and the order is the argument. Promotion capacity comes
    first because a topic that cannot reach `supported` at all is worse off than
    one that cannot be contradicted. A refutation lane comes before a claimant
    voice because an unopposed claim is the failure this system exists to
    prevent, and an unheard claimant is a failure it can at least report. Spread
    comes last: it is a property of the reading rather than of what can be shown.
    """
    promotable = sum(
        1 for topic in allocation if set(assignment[topic]) & EVIDENCE_WEIGHTED
    )
    refutable = sum(
        1
        for topic, count in allocation.items()
        if count < CONTESTED_THRESHOLD or SKEPTICAL in assignment[topic]
    )
    represented = sum(
        1
        for topic, count in allocation.items()
        if count < CONTESTED_THRESHOLD or CLAIMANT in assignment[topic]
    )
    spread = sum(len(assignment[topic]) for topic in allocation)
    concentrated = sum(
        max(count - 1, 0) for topic in allocation for count in assignment[topic].values()
    )
    return (promotable, refutable, represented, spread, -concentrated)


def _ideal(allocation: dict[str, int]) -> tuple[int, ...]:
    """The best score any assignment could reach, used to stop searching early."""
    spread = sum(min(count, len(REQUIRED_SLOTS)) for count in allocation.values())
    return (len(allocation), len(allocation), len(allocation), spread, 0)


def assign(
    allocation: dict[str, int], pins: frozenset[tuple[str, str]] = frozenset()
) -> dict[str, dict[str, int]]:
    """Place each topic's slots into buckets, best assignment by `_score`.

    A search rather than a deal. Round-robin dealing spreads topics evenly and
    considers fit not at all, and the first version of this function did exactly
    that: it gave anomalous history no primary or empirical source, so nothing
    in that topic could ever have been supported, and it gave declassified
    material — the topic most defined by primary documents — no primary slot.

    The search is ordered so the best candidates come first and stops as soon as
    it reaches a score nothing could beat. Exhausting the space took minutes;
    reaching the ceiling takes no time at all, and a search that has provably
    hit its ceiling has nothing left to find.
    """
    for bucket, topic in sorted(pins):
        if bucket not in REQUIRED_SLOTS:
            raise ValueError(f"{bucket} is not a slot bucket")
        if topic not in allocation:
            raise ValueError(f"{topic} has no slots allocated")

    topics = sorted(allocation, key=lambda topic: (-allocation[topic], topic))
    buckets = sorted(REQUIRED_SLOTS, key=lambda bucket: (-REQUIRED_SLOTS[bucket], bucket))
    evidence_index = [i for i, bucket in enumerate(buckets) if bucket in EVIDENCE_WEIGHTED]
    skeptical_index = buckets.index(SKEPTICAL)
    claimant_index = buckets.index(CLAIMANT)
    ceiling = _ideal(allocation)

    best: tuple[tuple[int, ...], list[tuple[str, tuple[int, ...]]]] | None = None

    def distributions(topic: str, capacity: list[int]) -> list[tuple[int, ...]]:
        """Ways to place this topic's slots, most promising first."""
        count = allocation[topic]
        options: list[tuple[int, ...]] = []

        def walk(index: int, left: int, taken: list[int]) -> None:
            if index == len(capacity):
                if left == 0:
                    options.append(tuple(taken))
                return
            for take in range(min(left, capacity[index]), -1, -1):
                walk(index + 1, left - take, [*taken, take])

        walk(0, count, [])

        required = {
            buckets.index(bucket) for bucket, pinned in pins if pinned == topic
        }
        if required:
            options = [option for option in options if all(option[i] for i in required)]

        def rank(option: tuple[int, ...]) -> tuple:
            has_evidence = any(option[i] for i in evidence_index)
            contested = count >= CONTESTED_THRESHOLD
            return (
                not has_evidence,
                contested and not option[skeptical_index],
                contested and not option[claimant_index],
                -sum(1 for value in option if value),
                option,
            )

        options.sort(key=rank)
        return options

    def search(index: int, capacity: list[int], chosen: list[tuple[str, tuple[int, ...]]]) -> bool:
        nonlocal best
        if index == len(topics):
            assignment = {
                topic: {buckets[i]: value for i, value in enumerate(counts) if value}
                for topic, counts in chosen
            }
            score = _score(assignment, allocation)
            if best is None or score > best[0]:
                best = (score, list(chosen))
            return best[0] >= ceiling
        for option in distributions(topics[index], capacity):
            if search(
                index + 1,
                [capacity[i] - option[i] for i in range(len(capacity))],
                [*chosen, (topics[index], option)],
            ):
                return True
        return False

    search(0, [REQUIRED_SLOTS[bucket] for bucket in buckets], [])
    if best is None:
        raise ValueError(
            "no assignment satisfies the slot counts with these pins: "
            + ", ".join(f"{bucket}/{topic}" for bucket, topic in sorted(pins))
        )

    return {
        topic: {buckets[i]: value for i, value in enumerate(counts) if value}
        for topic, counts in best[1]
    }


def prescribe(
    size: int = SLATE_SIZE, pins: frozenset[tuple[str, str]] = frozenset()
) -> tuple[SlotSpec, ...]:
    """The twenty slots the diet asks for, as bucket-and-topic pairs.

    The counts come from the specification's two tables. The *assignment* —
    which bucket serves which topic — is searched rather than dealt, against
    what the specification needs: every topic able to reach a promotion, every
    contested topic able to be contradicted, and slots spread rather than
    stacked.

    `pins` is for what the specification does not settle. Several assignments
    score identically, and the search picks among them arbitrarily — but "a
    patent is where an energy claim is formally lodged" is domain knowledge, not
    arbitrariness. A pin requires a bucket to serve a topic; the search honours
    it or says it cannot, which is better than a scoring function quietly
    rewritten until it produces the answer somebody already wanted.
    """
    allocation, _ = topic_allocation(size)
    assignment = assign(allocation, pins)

    specs: list[SlotSpec] = []
    index = 0
    for bucket in sorted(REQUIRED_SLOTS, key=lambda b: (-REQUIRED_SLOTS[b], b)):
        for topic in sorted(assignment):
            for _ in range(assignment[topic].get(bucket, 0)):
                specs.append(
                    SlotSpec(
                        index=index,
                        bucket=bucket,
                        topic=topic,
                        rationale=(
                            f"{TOPIC_TARGETS[topic]:.0%} of the menu is {topic}; "
                            f"{REQUIRED_SLOTS[bucket]} of {size} slots are {bucket}"
                        ),
                    )
                )
                index += 1
    return tuple(specs)


def unmet(specs: tuple[SlotSpec, ...], have: list[tuple[str, str]]) -> tuple[SlotSpec, ...]:
    """Which prescribed slots are still unfilled, given what has been found.

    `have` is a list of (bucket, topic) pairs already covered. Matching is by
    pair rather than by index, because two candidates for the same bucket and
    topic are interchangeable and a search should not be told otherwise.
    """
    outstanding: list[SlotSpec] = []
    pool = list(have)
    for spec in specs:
        pair = (spec.bucket, spec.topic)
        if pair in pool:
            pool.remove(pair)
        else:
            outstanding.append(spec)
    return tuple(outstanding)


def render(specs: tuple[SlotSpec, ...] = ()) -> str:
    """The prescription as a person reads it, with the arithmetic shown."""
    specs = specs or prescribe()
    allocation, working = topic_allocation()
    lines = [
        f"The diet prescribes {len(specs)} slots.",
        "",
        "By topic (SPEC section 3 menu targets):",
    ]
    for topic in sorted(allocation, key=lambda t: (-allocation[t], t)):
        lines.append(f"  {allocation[topic]}  {topic}  ({TOPIC_TARGETS[topic]:.0%})")
    lines.append("")
    lines.append("By role bucket (SPEC section 5.2):")
    for bucket, count in sorted(REQUIRED_SLOTS.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"  {count}  {bucket}  ({BUCKET_TARGETS[bucket]:.0%})")
    lines.append("")
    lines.append("Slots to find:")
    for spec in specs:
        lines.append(f"  {spec.index + 1:>2}. {spec.bucket:<30} {spec.topic}")
    lines.append("")
    lines.append("Working:")
    for line in working:
        lines.append(f"  {line}")
    return "\n".join(lines)


def coverage(specs: tuple[SlotSpec, ...] = ()) -> dict[str, Any]:
    specs = specs or prescribe()
    allocation = {}
    for spec in specs:
        allocation[spec.topic] = allocation.get(spec.topic, 0) + 1
    by_topic: dict[str, int] = {}
    by_bucket: dict[str, int] = {}
    pairs: dict[str, list[str]] = {}
    for spec in specs:
        by_topic[spec.topic] = by_topic.get(spec.topic, 0) + 1
        by_bucket[spec.bucket] = by_bucket.get(spec.bucket, 0) + 1
        pairs.setdefault(spec.topic, []).append(spec.bucket)
    assignment = {topic: {bucket: 1 for bucket in set(buckets)} for topic, buckets in pairs.items()}
    return {
        "slots": len(specs),
        "promotable": [
            topic for topic in sorted(allocation) if set(assignment[topic]) & EVIDENCE_WEIGHTED
        ],
        "unpromotable": [
            topic for topic in sorted(allocation) if not set(assignment[topic]) & EVIDENCE_WEIGHTED
        ],
        "contested_without_a_skeptic": [
            topic
            for topic, count in sorted(allocation.items())
            if count >= CONTESTED_THRESHOLD and SKEPTICAL not in assignment[topic]
        ],
        "contested_without_a_claimant": [
            topic
            for topic, count in sorted(allocation.items())
            if count >= CONTESTED_THRESHOLD and CLAIMANT not in assignment[topic]
        ],
        "by_topic": dict(sorted(by_topic.items())),
        "by_bucket": dict(sorted(by_bucket.items())),
        "buckets_per_topic": {topic: sorted(set(buckets)) for topic, buckets in sorted(pairs.items())},
        "topics_covered": sorted(by_topic),
        "all_topics_covered": set(by_topic) == set(REQUIRED_TOPICS),
    }
