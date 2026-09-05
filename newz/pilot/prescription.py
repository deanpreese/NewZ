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


def _deal(counts: dict[str, int]) -> list[str]:
    """Round-robin a multiset into a flat list, largest first, ties by name.

    Dealing rather than blocking is what spreads a topic across buckets. Taken
    in blocks, four UAP slots would land consecutively and meet whichever bucket
    happened to be filling at the time.
    """
    remaining = dict(counts)
    order = sorted(remaining, key=lambda key: (-remaining[key], key))
    dealt: list[str] = []
    while any(remaining.values()):
        for key in order:
            if remaining[key]:
                dealt.append(key)
                remaining[key] -= 1
    return dealt


def prescribe(size: int = SLATE_SIZE) -> tuple[SlotSpec, ...]:
    """The twenty slots the diet asks for, as bucket-and-topic pairs.

    Both axes are dealt round-robin and then zipped, so a topic with four slots
    lands in several different buckets rather than four of the same one. That
    spread is the point: four UAP claimant sources and no UAP primary record
    would satisfy every count in the specification and defeat its purpose.
    """
    allocation, _ = topic_allocation(size)
    topics = _deal(allocation)
    buckets = _deal(dict(REQUIRED_SLOTS))

    return tuple(
        SlotSpec(
            index=index,
            bucket=bucket,
            topic=topic,
            rationale=(
                f"{TOPIC_TARGETS[topic]:.0%} of the menu is {topic}; "
                f"{REQUIRED_SLOTS[bucket]} of {size} slots are {bucket}"
            ),
        )
        for index, (bucket, topic) in enumerate(zip(buckets, topics, strict=True))
    )


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
    by_topic: dict[str, int] = {}
    by_bucket: dict[str, int] = {}
    pairs: dict[str, list[str]] = {}
    for spec in specs:
        by_topic[spec.topic] = by_topic.get(spec.topic, 0) + 1
        by_bucket[spec.bucket] = by_bucket.get(spec.bucket, 0) + 1
        pairs.setdefault(spec.topic, []).append(spec.bucket)
    return {
        "slots": len(specs),
        "by_topic": dict(sorted(by_topic.items())),
        "by_bucket": dict(sorted(by_bucket.items())),
        "buckets_per_topic": {topic: sorted(set(buckets)) for topic, buckets in sorted(pairs.items())},
        "topics_covered": sorted(by_topic),
        "all_topics_covered": set(by_topic) == set(REQUIRED_TOPICS),
    }
