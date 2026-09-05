"""Versions that consequential records carry.

`SPEC.md` section 13 requires that an assessment reproduce exactly given the
same artifacts, policy version, and code version, so both versions are stated
here rather than discovered at runtime. Neither is read from git: a derivation
that changes with the working tree is not reproducible.
"""

CODE_VERSION = "0.1.0"

# Bumped whenever the capability matrix, promotion thresholds, independence
# justifications, required evidence lanes, or the task-state classification
# change. `SPEC.md` section 9 item 8 makes that bump a reassessment trigger.
POLICY_VERSION = "1.0.0"
