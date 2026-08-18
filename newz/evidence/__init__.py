"""The evidence instruments (P2 Rule 3) — development read, not liveness.

`tools/health.py` reports whether the being is up, answered and backed up.
These modules report whether it is *developing*, which is a different
question with different failure modes: a health check that lies goes quiet,
an evidence instrument that lies gets believed.

Two rules hold everywhere in here.

**No model is consulted.** Every number is computed from the store or from a
stored artifact. A digest graded by the thing that wrote it is the failure
INV-023 exists to prevent, and it applies to the instruments that read the
digest as much as to the digest itself.

**Every number carries its method** (P2 Rule 0), including the numbers that
cannot be produced. An instrument that prints 0% because its input is missing
has not measured compliance; it has measured its own blindness, and reported
it in the units of the thing it was asked about.
"""
