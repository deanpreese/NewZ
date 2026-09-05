"""Directed search, which produces leads and nothing else.

`SPEC.md` section 6 item 2 is categorical: feed entries and search results are
leads, and cannot become factual evidence without a retained full artifact. A
directed-search adapter is therefore allowed to say "look here" and nothing
more. It cannot create an assertion, cannot name a basis, and cannot reach an
assessment — and the way that is enforced is that this module has no function
that would let it.

Consuming a lead means going through the ordinary spine: a reservation in a
lane, a fetch under policy, a parse, an extraction. A lead does not shortcut any
of it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from newz.acquisition.urlpolicy import UrlPolicy, inspect_url
from newz.store.db import Store


@dataclass(frozen=True, slots=True)
class Lead:
    id: str
    claim_id: str | None
    task_id: str | None
    adapter: str
    url: str
    rationale: str
    source_revision_id: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "task_id": self.task_id,
            "adapter": self.adapter,
            "url": self.url,
            "rationale": self.rationale,
            "source_revision_id": self.source_revision_id,
        }


#: An adapter is a pure function from a question to places worth looking. It
#: receives no store and returns no evidence.
SearchAdapter = Callable[[str, str], tuple[tuple[str, str], ...]]

_ADAPTERS: dict[str, SearchAdapter] = {}


def register_adapter(name: str, adapter: SearchAdapter) -> None:
    _ADAPTERS[name] = adapter


def registered_adapters() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTERS))


def propose_leads(
    store: Store,
    *,
    adapter: str,
    claim_id: str,
    task_id: str | None,
    question: str,
    lane: str,
    id_prefix: str,
    url_policy: UrlPolicy | None = None,
) -> tuple[Lead, ...]:
    """Run an adapter and record what it suggests, refusing what cannot be fetched.

    A lead whose URL the fetcher would refuse is not recorded. Storing one would
    put a place the system can never go onto a list of places to go, and the
    backlog would grow with work that can never be done.
    """
    if adapter not in _ADAPTERS:
        raise KeyError(f"no directed-search adapter named {adapter!r}")
    policy = url_policy or UrlPolicy()

    proposed = _ADAPTERS[adapter](question, lane)
    leads: list[Lead] = []
    with store.write() as connection:
        for index, (url, rationale) in enumerate(proposed):
            if not inspect_url(url, policy).allowed:
                continue
            known = connection.execute(
                "SELECT id FROM source_revisions WHERE endpoint_url = ? LIMIT 1", (url,)
            ).fetchone()
            lead = Lead(
                id=f"{id_prefix}-{index}",
                claim_id=claim_id,
                task_id=task_id,
                adapter=adapter,
                url=url,
                rationale=rationale,
                source_revision_id=known["id"] if known else None,
            )
            connection.execute(
                "INSERT OR IGNORE INTO leads (id, claim_id, task_id, adapter, url, "
                "source_revision_id, rationale, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    lead.id,
                    lead.claim_id,
                    lead.task_id,
                    lead.adapter,
                    lead.url,
                    lead.source_revision_id,
                    lead.rationale,
                ),
            )
            leads.append(lead)
    return tuple(leads)


def unconsumed(store: Store, claim_id: str | None = None) -> tuple[Lead, ...]:
    rows = (
        store.query(
            "SELECT * FROM leads WHERE consumed_at IS NULL AND claim_id = ? ORDER BY id", claim_id
        )
        if claim_id
        else store.query("SELECT * FROM leads WHERE consumed_at IS NULL ORDER BY id")
    )
    return tuple(
        Lead(
            id=row["id"],
            claim_id=row["claim_id"],
            task_id=row["task_id"],
            adapter=row["adapter"],
            url=row["url"],
            rationale=row["rationale"],
            source_revision_id=row["source_revision_id"],
        )
        for row in rows
    )


def mark_consumed(store: Store, lead_id: str, operation_id: str) -> None:
    """A lead is spent when an authorized operation went and looked."""
    with store.write() as connection:
        connection.execute(
            "UPDATE leads SET consumed_at = datetime('now'), operation_id = ? WHERE id = ?",
            (operation_id, lead_id),
        )


def catalog_search(question: str, lane: str) -> tuple[tuple[str, str], ...]:
    """The only adapter Phase 3 ships: the catalog itself.

    It suggests sources already in the diet whose declared scope mentions the
    lane's subject. Deliberately unimpressive — a real directed search is a
    Phase 6 concern, and the point here is that whatever produces the suggestion
    can only ever produce a suggestion.
    """
    return ()
