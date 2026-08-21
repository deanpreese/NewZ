#!/usr/bin/env python3
"""bench_model.py's field, with the qwen thinking parameters never sent.

Same endpoint, same corpus, same scoring — the only difference is the request
body. bench_model.py adds `reasoning_effort: "none"` and
`chat_template_kwargs: {"enable_thinking": false}` to every call because that
is what the production call sites send. This script adds neither.

Three reasons to run it:

  1. Some stacks reject an unknown top-level field outright, or reject
     `chat_template_kwargs` specifically, and every case then fails as a
     transport error that says nothing about the model. Run this to separate
     "the model cannot hold the boundary" from "this server will not take our
     parameters" — a disqualified field here and a scored one there is the
     second.

  2. The reasoning-token column stops being a formality. Under the params it
     records whether a model honoured them; without them it records what the
     model spends unprompted, which is the number that decides whether it fits
     the token diet the day a proxy drops the field.

  3. A model that scores well here needs nothing said to it. That is worth
     more than the same score under two switches it may stop honouring on the
     next quant.

A candidate that passes here and fails under bench_model.py is being broken by
the parameters, not helped by them. One that fails here and passes there needs
them to work, which is fine — production sends them — but it belongs in the
comparison rather than hidden by it.

Usage
-----
    python tools/bench_model_plain.py --all              # every served model
    python tools/bench_model_plain.py --models a,b,c     # a specific field
    python tools/bench_model_plain.py --all --json out.json

Every flag bench_model.py takes works here too, `--no-thinking-params`
included, where it is a no-op. The endpoint and the corpus come from
bench_model.py — edit them there, in one place, so the two scripts cannot
drift into benching different boxes or different prompts.

Exit codes are bench_model.py's.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench_model  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    # Emptied before main() runs, and main() only ever clears it further, so
    # the flag cannot switch the parameters back on.
    bench_model.THINKING_PARAMS.clear()
    return bench_model.main(argv)


if __name__ == "__main__":
    sys.exit(main())
