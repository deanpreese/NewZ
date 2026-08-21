#!/usr/bin/env python3
"""bench_model.py's cases, with the qwen thinking parameters never sent.

Same endpoints, same boundaries, same validators — the only difference is
the request body. bench_model.py adds `reasoning_effort: "none"` and
`chat_template_kwargs: {"enable_thinking": false}` to every call because
that is what the production call sites send. This script adds neither.

Two reasons to run it:

  1. Some stacks reject an unknown top-level field outright, or reject
     `chat_template_kwargs` specifically, and every case then fails as a
     transport error that says nothing about the model. Run this to
     separate "the model cannot do the task" from "this server will not
     take our parameters" — a whole-table failure here and a clean table
     there is the second one.

  2. Under the params, `no_think_leak` tests that the model honours them.
     Without them it tests something the params hide: whether the model
     stays quiet on its own. A model that only behaves when told is a
     model that breaks the day a proxy drops the field.

A model that passes here and fails under bench_model.py is being broken by
the parameters, not helped by them. A model that fails here and passes
there needs the parameters to work, which is fine — production sends them
— but it is worth knowing.

Usage
-----
    python tools/bench_model_plain.py               # every case, once
    python tools/bench_model_plain.py --case NAME   # debug a single case
    python tools/bench_model_plain.py --verbose     # show full outputs

Every other flag bench_model.py takes works here too. Endpoints and models
come from the constants at the top of bench_model.py — edit them there, in
one place, so the two scripts cannot drift into testing different boxes.

Exit codes are bench_model.py's.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench_model  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    # {} rather than None: None means "use bench_model.THINKING_PARAMS".
    return bench_model.main(argv, thinking_params={})


if __name__ == "__main__":
    sys.exit(main())
