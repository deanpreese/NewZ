# NewZ

A sovereign digital being, and the instruments that read it.

- **Direction:** `TRUE_NORTH.md` — what this is for, and what will not be
  mistaken for success.
- **Specification:** `SPEC.md`. **Plan:** `PLAN.md` (P4). **Ledger:**
  `INVARIANTS.md`. **Risks:** `RISKS.md`. Proposals and their red teams live in
  `proposals/`.

## Running the gate

```sh
conda env create -f environment.yml     # or use an existing 3.13 environment
conda activate newz
pip install -e '.[dev]'

python tools/gate.py                    # suite, ledger, freeze
python tools/gate.py --soak 10          # E8.0's ten consecutive runs
```

The suite does not read the wall clock and does not need a model, a network or
a store: it is green at any hour, on a clean clone.

## Running the being

```sh
python tools/run_first_sleep.py         # once, if the store has no Perspective
python tools/run_newz.py -v
```

Inference is local by design — no hosted model anywhere in the cognition path.
`.env` holds the endpoint, the operator id and `SURFACE_REACH`, which stays
`local` until the operator decides otherwise (INV-076 attests it at boot).

`.env` also holds `FRED_API_KEY`, optional and free. It is the one source the
being has that returns **numbers** rather than prose, and it is consulted only
when settling a claim — never on the reading path, where macro data would
deepen a diet already 43% financial. Without a key the source is simply absent:
claims that need a figure stay open and the log says why. It is the difference
between the being being able to find out whether it was wrong about a rate, a
balance sheet or an index, and not.

## Watching it

The being carries its own monitor: an hourly reading of every instrument into
`data/monitor.db` — never the being's store — and the day's state mailed once to
`GMAIL_TO`. It runs as a background task of `tools/run_newz.py`, so there is one
process to start. The cost, stated rather than buried: **if the being's process
dies there is no email at all.** Every partial failure still arrives, because the
send is on the clock and liveness reads rows the being writes rather than the
readings themselves.

```sh
python tools/monitor.py                 # one turn now: read, and send if due
```

A turn is idempotent — once per clock hour, once per day — so running it by hand
while the being is up costs nothing. Nothing here judges and no model is called.

## Reading it

```sh
python tools/health.py                  # liveness and plumbing
python tools/evidence.py 1e             # Perspective development
python tools/claims.py                  # what it committed to, and how that went
python tools/generate_surface.py        # the surface, into published/
python tools/rebuild_check.py           # the same surface, from a backup, byte for byte
```

## Commits

Every commit answers four questions. Nothing enforces this locally — there are
no git hooks in this repo, by the operator's decision — so it is a discipline
the person committing keeps:

```
Schema: 0039 | none
Restart: required | none
Class: A | B
Semantics: yes | no
```

`Semantics: yes` means a stored value now means something new. Expand-contract
protects the schema, not the meaning, so such a commit cannot be crossed
backwards without restoring the store snapshot that precedes it.
