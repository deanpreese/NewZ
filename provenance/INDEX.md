# NewZ session archive — index

The raw Claude Code transcripts for the whole of NewZ (v2) live in
`provenance/newz-sessions/`, carried over on 2026-08-17 when this repo was
cloned from its predecessor at `a6c3552`. They are **not tracked** (see
`.gitignore`): 28MB of jsonl is an archive, not a handoff, and anything ever
echoed inside a session is in there verbatim — the same reason `.env` is
ignored.

This file is the tracked part. It exists so a position held in NewZ can be
traced back to the conversation that produced it, the way
`tools/what_shaped.py` traces a view back to its sources.

| Session | Span | Lines | Size | Opened with |
|---|---|---|---|---|
| `3e3a3d76` | 2026-08-09 → 08-13 | 3086 | 8.1 MB | the founding session — TRUE_NORTH/SPEC/PLAN handed over, conda `agent13` set as the env |
| `b1582d39` | 2026-08-12 → 08-18 | 6770 | 20.3 MB | "where does the current plan stand" — the long spine; most of 08-14 → 08-17 |
| `af8092c2` | 2026-08-14 | 20 | 0.04 MB | q36-a3b test-suite failures, first pass |
| `9e03ff44` | 2026-08-14 | 351 | 0.89 MB | the same three a3b failure classes, worked through to proposals |
| `28f2bdd4` | 2026-08-13 | 66 | 0.13 MB | short, opened by a local command |
| `15a5c122` | 2026-08-17 | 69 | 0.16 MB | the close — how to carry v2 into the clone |

114 commits across 2026-08-08 → 08-17, heaviest on 08-14 (20) and 08-08 (17).

## What is NOT in here

- **The being.** `data/newz.db` + `data/interior.db` are the store, not the
  transcripts. They cross as bytes or not at all.
- **The being's own model calls.** `logs/llm_calls.jsonl` (13MB) stayed in
  the predecessor repo. Different provenance entirely — that is Lumen
  thinking, this is the build being argued about.
- **The reasoning that already landed.** The constitution (v3–v6),
  `proposals/`, `INVARIANTS.md`, `RISKS.md` and the commit messages are the
  *decided* record and came across in the clone. Read those first; these
  transcripts are only for when you need to know why a decision went the way
  it did and the commit message doesn't say.
