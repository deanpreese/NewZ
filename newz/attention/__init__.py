"""The attention plane.

`SPEC.md` sections 5 through 8 specify how a claim is evaluated once it exists.
This is what makes a claim worth evaluating at all — and the boundary that keeps
the two apart is the point of the whole package:

    **Interest reaches attention. Evidence reaches conclusion.**

There is no path from anything here to an assessment, and none may be added.
That is enforced by the absence of a code path rather than by a check, and
`tests/test_separation.py` proves the absence by enumerating every table this
package writes to.
"""

from newz.attention.decay import decay_interests, decay_notices, what_is_no_longer_held
from newz.attention.diet import diet_self_report
from newz.attention.interest import (
    form_interest,
    interest_register,
    provenance_mix,
    record_outcome,
    retire_interest,
)
from newz.attention.notices import NoticeRefused, notice_over_span, record_notice

__all__ = [
    "NoticeRefused",
    "decay_interests",
    "decay_notices",
    "diet_self_report",
    "form_interest",
    "interest_register",
    "notice_over_span",
    "provenance_mix",
    "record_notice",
    "record_outcome",
    "retire_interest",
    "what_is_no_longer_held",
]
