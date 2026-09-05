"""Essay selection: the second and last thing an interest may cause.

`SPEC.md` section 9.1 lets interest select the subject of an essay and stop
there. So selection is here, in the attention plane, and composition is in the
presentation plane — and the two are separate modules rather than one, because a
composer that could look up the interest behind its subject is one refactor away
from writing for it.

Interest chose the subject. It does not get the verdict.
"""

from __future__ import annotations

from newz.attention.interest import load_interest, record_outcome
from newz.present.essays import Essay, compose_essay
from newz.store.db import Store


def select_subject(store: Store, interest_id: str) -> tuple[str, tuple[str, ...]]:
    """The claims an interest's investigations produced, as an essay's subject.

    Interest chooses what an essay is about by having caused the investigations
    it is about. There is no other selection path, which is what keeps subject
    selection from becoming a way to select a conclusion.
    """
    entry = load_interest(store, interest_id)
    investigations = [target for kind, target in entry.outcomes if kind == "investigation"]
    if not investigations:
        return entry.subject, ()
    claim_ids = tuple(
        row["claim_id"]
        for row in store.query(
            "SELECT DISTINCT claim_id FROM investigation_claims WHERE investigation_id IN "
            f"({','.join('?' * len(investigations))}) ORDER BY claim_id",
            *investigations,
        )
    )
    return entry.subject, claim_ids


def essay_from_interest(
    store: Store, *, interest_id: str, essay_id: str, intended_conclusion: str
) -> Essay:
    """Select the subject, compose against the record, and record what happened.

    The outcome is recorded whether or not the essay said what the interest
    hoped: an interest whose essay changed under it has still caused something,
    and hiding that would make the downstream trace flattering.
    """
    subject, claim_ids = select_subject(store, interest_id)
    essay = compose_essay(
        store,
        essay_id=essay_id,
        subject=subject,
        claim_ids=claim_ids,
        intended_conclusion=intended_conclusion,
        interest_id=interest_id,
    )
    if essay.rendered:
        record_outcome(store, interest_id, "essay", essay.id)
    return essay
