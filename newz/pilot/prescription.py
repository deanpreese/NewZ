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


def _largest_remainder(targets: dict[str, float], size: int) -> tuple[dict[str, int], list[str]]:
    """Allocate `size` whole slots across weighted shares, and show the working."""
    exact = {name: share * size for name, share in targets.items()}
    floors = {name: int(value) for name, value in exact.items()}
    remaining = size - sum(floors.values())

    # Ties broken by name so the allocation is the same every run.
    ranked = sorted(exact.items(), key=lambda item: (-(item[1] - int(item[1])), item[0]))
    working = [
        f"{name}: {targets[name]:.0%} of {size} is {value:.2f}"
        for name, value in sorted(exact.items())
    ]
    for name, _ in ranked[:remaining]:
        floors[name] += 1
        working.append(f"{name}: +1 from the largest remainder")
    return floors, working


def topic_allocation(size: int = SLATE_SIZE) -> tuple[dict[str, int], list[str]]:
    """Allocate slots across topics by largest remainder, and show the working."""
    floors, working = _largest_remainder(TOPIC_TARGETS, size)

    # Every topic must appear: SPEC 5.2 requires all eight covered, and a
    # share small enough to floor to zero would silently drop one.
    for topic in TOPIC_TARGETS:
        if floors[topic] == 0:
            raise ValueError(
                f"{topic} allocated no slot; all eight initial topics must be covered"
            )
    return floors, working


def bucket_allocation(size: int = SLATE_SIZE) -> tuple[dict[str, int], list[str]]:
    """Allocate slots across scheduling buckets, the same way.

    At twenty this reproduces section 5.2's stated counts exactly, which is what
    lets the slate grow past twenty at all: the specification fixes a
    distribution and states one instance of it, and a catalogue that expanded by
    adding whatever was available would drift off that distribution while every
    individual addition looked reasonable.
    """
    floors, working = _largest_remainder(BUCKET_TARGETS, size)
    for bucket in BUCKET_TARGETS:
        if floors[bucket] == 0:
            raise ValueError(
                f"{bucket} allocated no slot at size {size}; every bucket must be served"
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


#: Buckets a topic needs at most one of before anything else is distributed.
#: Order matters and is `_score`'s order: something that can carry a promotion,
#: then something that can contradict, then the claimant's own voice.
SCARCE = (EVIDENCE_WEIGHTED, frozenset({SKEPTICAL}), frozenset({CLAIMANT}))


def _reserve_scarce_buckets(
    allocation: dict[str, int],
    slots: dict[str, int],
    pins: frozenset[tuple[str, str]],
) -> tuple[dict[str, dict[str, int]], dict[str, int], dict[str, int]]:
    """Give every topic one of each scarce bucket before distributing the rest.

    The search ranks each topic's options in isolation and takes them in order,
    so at twenty slots — where the scarce buckets are almost exactly as large as
    the number of topics — it lands on the right answer and proves it. Past that
    the first topic considered takes several skeptical slots because nothing
    stops it, and the topics considered later get none. At sixty slots that left
    five of eight topics with no skeptical source: a slate three times the size
    of the pilot and worse at the thing the pilot was built to do.

    This is not a change to what a good assignment is. `_score` already says
    promotion capacity first, then refutability, then representation; this
    settles those three before the search runs, so the search decides only what
    `_score` was going to decide last anyway.

    A topic below `CONTESTED_THRESHOLD` is not reserved a skeptic or a claimant.
    That is the same rule the ranking applies: five claimant slots cannot cover
    eight topics, and the menu targets already say which topics matter most.
    """
    reserved: dict[str, dict[str, int]] = {}
    left = dict(slots)
    remaining = dict(allocation)
    pinned = {topic for _, topic in pins}

    for group in SCARCE:
        needs_it = [
            topic
            for topic in sorted(allocation, key=lambda t: (-allocation[t], t))
            if remaining[topic] > 0
            and topic not in pinned
            and (group is SCARCE[0] or allocation[topic] >= CONTESTED_THRESHOLD)
        ]
        for topic in needs_it:
            # The emptiest qualifying bucket, so the scarce ones are not spent
            # on the topics that happen to be considered first.
            options = sorted(
                (bucket for bucket in group if left.get(bucket, 0) > 0),
                key=lambda bucket: (-left[bucket], bucket),
            )
            if not options:
                break
            bucket = options[0]
            reserved.setdefault(topic, {})
            reserved[topic][bucket] = reserved[topic].get(bucket, 0) + 1
            left[bucket] -= 1
            remaining[topic] -= 1
    return reserved, left, remaining


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


def _ideal(allocation: dict[str, int], slots: dict[str, int]) -> tuple[int, ...]:
    """The best score any assignment could actually reach.

    A bound is only useful if something can reach it. The first version asked
    for every topic promotable, refutable and represented, which is true at
    twenty and false at thirty: fifteen percent of thirty is four or five
    skeptical slots against eight topics that all clear the contested
    threshold, so at most five of them can have a skeptic however the slots are
    dealt. An unreachable ceiling is not a ceiling — the search never stopped,
    spent its whole budget every time, and reported "not proven optimal" about
    answers that were optimal.

    So each term is bounded by the capacity that produces it.
    """
    topics = len(allocation)
    contested = sum(1 for count in allocation.values() if count >= CONTESTED_THRESHOLD)
    settled = topics - contested

    evidence = sum(slots.get(bucket, 0) for bucket in EVIDENCE_WEIGHTED)
    promotable = min(topics, evidence)
    refutable = settled + min(contested, slots.get(SKEPTICAL, 0))
    represented = settled + min(contested, slots.get(CLAIMANT, 0))

    # A topic cannot spread wider than the buckets that exist, and the buckets
    # cannot hold more distinct topics than they have slots.
    by_topic = sum(min(count, len(slots)) for count in allocation.values())
    by_bucket = sum(min(count, topics) for count in slots.values())
    spread = min(by_topic, by_bucket)
    return (promotable, refutable, represented, spread, spread - sum(allocation.values()))


#: How many placements the search will consider before settling for the best it
#: has found. The ceiling in `_ideal` is optimistic: it asks for every topic
#: spread across distinct buckets, which is reachable at twenty and not at
#: twenty-four, where several topics each want all five buckets and the smallest
#: bucket holds two. When the ceiling is unreachable the search has nothing to
#: stop it, and exhausting the space is not minutes but hours.
#:
#: So it is bounded. Options are generated best-first, so the good assignments
#: are found early and the budget cuts off the long tail of equivalent and worse
#: ones. `prescription_report` says whether the result was proven optimal or
#: merely the best found, because "we did not search the whole space" is a fact
#: about the answer and belongs with it.
NODE_BUDGET = 50_000


def assign(
    allocation: dict[str, int],
    pins: frozenset[tuple[str, str]] = frozenset(),
    slots: dict[str, int] | None = None,
    node_budget: int = NODE_BUDGET,
) -> dict[str, dict[str, int]]:
    """The better of two constructions, by the score that encodes the spec.

    The plain search is right at twenty and starves the topics it considers
    last at sixty; reserving the scarce buckets first is right at sixty and
    costs a unit of spread at twenty. Neither dominates, both are cheap, and
    `_score` already says which answer is better — so both are built and the
    better one is returned, rather than one being tuned until it wins.
    """
    full = dict(slots) if slots is not None else dict(REQUIRED_SLOTS)
    plain = _assign(allocation, pins, full, node_budget)

    reserved, left, remaining = _reserve_scarce_buckets(allocation, full, pins)
    if not reserved:
        return plain
    seeded = _merge(_assign(remaining, pins, left, node_budget), reserved)
    return max((plain, seeded), key=lambda option: _score(option, allocation))


def _merge(
    placed: dict[str, dict[str, int]], reserved: dict[str, dict[str, int]]
) -> dict[str, dict[str, int]]:
    merged = {topic: dict(buckets) for topic, buckets in placed.items()}
    for topic, held in reserved.items():
        for bucket, count in held.items():
            merged.setdefault(topic, {})
            merged[topic][bucket] = merged[topic].get(bucket, 0) + count
    return {topic: dict(sorted(merged[topic].items())) for topic in sorted(merged)}


def _assign(
    allocation: dict[str, int],
    pins: frozenset[tuple[str, str]],
    slots: dict[str, int],
    node_budget: int,
) -> dict[str, dict[str, int]]:
    """Place each topic's slots into buckets, best assignment by `_score`.

    A search rather than a deal. Round-robin dealing spreads topics evenly and
    considers fit not at all, and the first version of this function did exactly
    that: it gave anomalous history no primary or empirical source, so nothing
    in that topic could ever have been supported, and it gave declassified
    material — the topic most defined by primary documents — no primary slot.

    The search is ordered so the best candidates come first and stops as soon as
    it reaches a score nothing could beat, or as soon as it has spent its node
    budget. Reaching the ceiling takes no time at all where the ceiling is
    reachable.
    """
    if sum(slots.values()) != sum(allocation.values()):
        raise ValueError(
            f"{sum(slots.values())} bucket slots against {sum(allocation.values())} topic slots"
        )
    for bucket, topic in sorted(pins):
        if bucket not in slots:
            raise ValueError(f"{bucket} is not a slot bucket")
        if topic not in allocation:
            raise ValueError(f"{topic} has no slots allocated")

    topics = sorted(allocation, key=lambda topic: (-allocation[topic], topic))
    buckets = sorted(slots, key=lambda bucket: (-slots[bucket], bucket))

    evidence_index = [i for i, bucket in enumerate(buckets) if bucket in EVIDENCE_WEIGHTED]
    skeptical_index = buckets.index(SKEPTICAL)
    claimant_index = buckets.index(CLAIMANT)
    ceiling = _ideal(allocation, slots)

    best: tuple[tuple[int, ...], list[tuple[str, tuple[int, ...]]]] | None = None
    spent = 0

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
        nonlocal best, spent
        spent += 1
        if spent > node_budget:
            return True
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

    search(0, [slots[bucket] for bucket in buckets], [])
    if best is None:
        raise ValueError(
            "no assignment satisfies the slot counts with these pins: "
            + ", ".join(f"{bucket}/{topic}" for bucket, topic in sorted(pins))
        )

    return {
        topic: {buckets[i]: value for i, value in enumerate(counts) if value}
        for topic, counts in best[1]
    }


def prescription_report(
    size: int = SLATE_SIZE, pins: frozenset[tuple[str, str]] = frozenset()
) -> dict[str, Any]:
    """The prescription with its derivation, and whether it was proven optimal."""
    allocation, topic_working = topic_allocation(size)
    slots, bucket_working = bucket_allocation(size)
    assignment = assign(allocation, pins, slots)
    score = _score(assignment, allocation)
    ceiling = _ideal(allocation, slots)
    return {
        "size": size,
        "topics": allocation,
        "buckets": slots,
        "working": topic_working + bucket_working,
        "assignment": assignment,
        "score": list(score),
        "ceiling": list(ceiling),
        "proven_optimal": score >= ceiling,
        "shortfall": [
            name
            for name, got, want in zip(
                ("promotable", "refutable", "represented", "spread", "concentration"),
                score,
                ceiling,
                strict=True,
            )
            if got < want
        ],
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
    slots, _ = bucket_allocation(size)
    assignment = assign(allocation, pins, slots)

    specs: list[SlotSpec] = []
    index = 0
    for bucket in sorted(slots, key=lambda b: (-slots[b], b)):
        for topic in sorted(assignment):
            for _ in range(assignment[topic].get(bucket, 0)):
                specs.append(
                    SlotSpec(
                        index=index,
                        bucket=bucket,
                        topic=topic,
                        rationale=(
                            f"{TOPIC_TARGETS[topic]:.0%} of the menu is {topic}; "
                            f"{slots[bucket]} of {size} slots are {bucket}"
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
