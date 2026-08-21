# Phase 3A — the monitor, and Phase 8 struck

*2026-08-21. The operator's design: **at the top of every hour the
instrumentation is read and saved; every day an email goes to the address in
`.env` with the current state; that eliminates the remainder of Phase 8.***

*Final draft, and the fourth. The first was six epics and over-built. The second
was this design in prose. The third red-teamed it against the code and moved four
things. This one moves the monitor out of the being's process and into its own
database, which is simpler than what it replaces and closes the gaps the earlier
rounds could not. Figures are from this clone at `52670b4` and from checks and
timings run this session; where a claim has no instrument, it says so (Rule 0).
§5 is the red team. §6 is the decision asked for.*

---

## 0. What this is

**One command, started by hand, running beside the being rather than inside it.**
And a deletion.

| | | |
|---|---|---|
| **E3A.0** | the instrument registry | *built — was E8.1* |
| **E3A.1** | `data/monitor.db`, and the tables that move into it | |
| **E3A.2** | `tools/monitor.py` — a reading at the top of every hour | |
| **E3A.3** | the daily state email to `GMAIL_TO` | |
| **E3A.4** | Phase 8 struck | |

Nothing decides anything. No model call anywhere in the phase. No autonomy, no
precedence table, no build path, no restart.

**Two properties carry the whole design.** It runs **outside the being's
process**, because a monitor inside the thing it monitors reports nothing at the
moment that matters. And it writes **its own database**, because observations
*about* the being are not part of the being's record, and because `newz.db`
should keep exactly one writer.

The credentials already sit unused in `.env` — `GMAIL_USER`, `GMAIL_PASS`,
`GMAIL_TO` — and the constitution already permits the send: `read-only-web-001`,
*"Email to the operator is not publishing; email to anyone else is."*

**Roughly a day.**

---

## 1. E3A.0 — the instrument registry *(built 2026-08-19, as E8.1)*

*Delivers:* the three probes that hardcoded an absolute path resolve the repo the
way every other tool does; `evolution/instruments.yaml` enumerates every tool
exactly once with what it measures, what it reads, whether a model touched any
link in its chain, its denominator and its method line.

*Done when:* no tool holds an absolute path outside the repo, every tool is
classified exactly once, and both are tested. **Done.**

*Depends on:* nothing.

*Was:* E8.1. The registry row carries `was: E8.1`, so every commit message naming
it still resolves.

---

## 2. E3A.1 — `data/monitor.db`

*Delivers:* a second database — its own file, its own migration chain under
`newz/store/sql_monitor/`, its own `schema_versions` — holding what the monitor
writes and reads:

- **`metric_readings`** and **`metric_definition_changes`**, moved whole from
  `newz.db` **with their ids preserved**;
- **`monitor_log`** (new): one row per run and per send, with its outcome, so a
  missed hour is visible and a day is never sent twice.

This is the `interior.db` discipline, applied for the same reason it was applied
there: *"separation is structural — different file, different connection — not a
table prefix."*

**Six modules read those tables and none of them joins to a being table** —
`baseline.py`, `definitions.py`, `pre_loop.py`, `surface/generate.py`,
`tools/claims.py`, verified this session. So they reach it by `ATTACH … AS mon`
on the existing connection with a `mon.` prefix in the query text, rather than by
threading a second connection through all six.

*Done when:* `newz.db` holds neither table; every reader reaches them through the
attached database; the ids in the moved rows are the ids they had; `monitor.db`
is covered by the backup with its own `verify_table`; and `rebuild_check`
restores both files and still produces a byte-comparable surface.

*Depends on:* nothing.

*Hooks:* **§5 F4 and F5.** The surface's read page records provenance as
`m.record("read", "metric_readings", [ids])` — E3.3's disclosure by construction
— and E3.5 closes on a byte-comparable rebuild. A split that the rebuild does not
know about produces a page that looks correct and says nothing.

**Move it now rather than later.** `pre_loop_baseline.yaml` pins reading ids and
is currently empty, so the move costs nothing today. Once the baseline is taken,
those ids live in a file inside the hard core and moving the rows underneath them
becomes a `Semantics:` change with a store snapshot behind it.

---

## 3. E3A.2 — the monitor, hourly, outside the being

*Delivers:* `tools/monitor.py`, one command, **started the way the being is** —
`python tools/monitor.py`, its own process, sleeping to the next hour boundary.
No launchd, no cron, no service manager: the repo's idiom is a command the
operator starts, and an OS scheduler would add machine state the repo cannot see
while supervising the monitor more closely than the being it watches.
`--once` takes a single reading and exits, which is what the tests drive.

Per run it takes a reading of every registered metric through E2.7's baseline
layer and E2.8's definition guard — the same `record_all` the being called
nightly. **`MetricScheduler` is removed from `run_newz.py`.**

**Because the monitor now writes the readings, the readings stop being evidence
the being is alive.** A dead being still produces a full hourly series. So
liveness comes only from rows the being itself writes — last episode, last
`perspective`, last verified backup — and that is the same defect as F1 in
another place: a signal that keeps arriving after its subject has stopped is not
a signal.

**And the baseline works in days while the series works in hours.**
`pre_loop.propose()` refuses below `MIN_READINGS = 7` and its own comment says
why — *"below that it is one week seen once"* — so it counts readings and means
nights; and it records **every reading id it used**, which goes from 28 per metric
to 672, about 19,000 ids in a hand-readable file inside the hard core that
INV-087 makes load-bearing. One change fixes both: the baseline takes the last
reading of each day.

*Done when:* a reading exists for every elapsed hour **whether or not the being
was up**, asserted by a test that stops the being and still gets one; the
liveness figures derive only from being-written rows; and `pre_loop.propose()`
reads one reading per day, refuses below seven **days**, and records ~28 ids —
each asserted by a test that would have failed under the old rule at the new
cadence.

*Depends on:* E3A.1.

**What changes downstream, stated rather than discovered:**

- **The series gets 24× denser** — 28 metrics/hour ≈ 672 rows/day, ~245k/year,
  ~20–25MB/year. `metric_readings` is append-only with `(metric, ts DESC)`
  already indexed, and nothing expires or rolls up: *"every reading, holes
  included — the point of keeping them."*
- **The delta layer gets more precise, not different.** `_baseline()` takes the
  last reading before the 168h window opened; hourly puts that within an hour of
  the window edge instead of within a day.
- **No metric's definition changes.** Every one is a 168h window and the cadence
  is not part of any definition, so `definition_version` must not move.
- **An outage stops being a hole and becomes a reading.** This is the point: a
  dead being now produces `hours_since_last_sleep` climbing hour by hour, rather
  than a gap nobody is there to notice.

---

## 4. E3A.3 — the daily state email

*Delivers:* the same command, at or after `NEWZ_MONITOR_SEND_HOUR` (default
`sleep_hour + 2`), sends one message to `GMAIL_TO` via `GMAIL_USER` /
`GMAIL_PASS`. Three config fields, `smtplib.SMTP_SSL`, no new dependency.

**It is not triggered by sleep. It reports on sleep** (§5 F1).

*The body is what already exists, and nothing else:*

- **is the being alive** — when it last slept, last recorded an episode, last
  took a verified backup; from being-written rows only;
- **hours since the last reading**, from `monitor_log`;
- every registered metric: **value, baseline, delta, grade** (E2.5, E2.7);
- every `UNREADABLE`, with its reason (INV-044);
- **premise drift** (E2.10) and **epic drift** (E2.11);
- ledger and freeze status, and the ready queue;
- any `monitor_log` row in the last day that failed.

*Done when:* the email sends with no model call; every number carries its grade
and method (Rules 0 and 7); **no sentence in it is anything but a number, its
method, or a heading**, asserted by a test; **a day on which the being never ran
still produces an email and says so**, asserted by a test; and a send failure is
recorded in `monitor_log` and retried on the next hourly run rather than lost.

*Depends on:* E3A.2.

*Hooks:* R-R1 — *"a weekly page of fluent reasoning is the worst available drift
detector."* Phase 8's answer was to order the loop's prose last and mark it
unverified. Here there is no prose to order, which is the stronger form of the
same answer.

---

## 5. E3A.4 — Phase 8 struck

**Every id resolves. Nothing is dropped silently.**

| P4 | Now |
|---|---|
| **E8.0** the gate | **struck.** `tools/gate.py` and `environment.yml` exist and are used; the remaining clause — *"a push that breaks either check is refused"* — became unachievable when the hooks and CI were removed (`e238528`), and striking the epic settles it |
| **E8.1** the registry *(built)* | **E3A.0**, unchanged and built |
| **E8.2** the runner, continuity assertion | **struck.** Nothing restarts the being but a person |
| **E8.3** the Watcher, report, prepared session | **struck.** Its daily read was already delivered by `MetricScheduler` and `PublishScheduler`; the report is E3A.3; precedence, the decision queue and prepared sessions go with the phase |
| **E8.4** the builder | **struck** |
| the enablement ladder, stages 0–4 | **deleted** — no autonomy to widen |
| the six kill conditions | **lines in the email**, halting nothing |
| S8-E | **S3A-E** below |
| P3-11 … P3-16 | **closed as moot** — six risks of a loop that will not exist |

**What the strike touches, because this is not a documentation edit:**

| Site | What happens |
|---|---|
| `newz/evidence/epics.py` | `from_plan`'s regex `E\d+\.\d+` rejects `E3A.1` **silently**; `ready()`'s sort key `int(e.split(".")[0][1:])` raises `ValueError`. Widen both, or the new epics are invisible to the drift check |
| `epics.py::closable_by_test()` | *"what an autonomous builder may attempt"* — no builder. Remove (Rule 2) |
| `pre_loop.py::may_widen()` | refuses autonomy stages that no longer exist. Remove; `compare()` survives as the email's comparison line |
| `freeze.py::enforce(actor="loop")` | the constrained party is gone. Rename the actor to what it always was — the operator's agents, which is who edits this repo unattended |
| `tests/test_hard_core.py:100` | reads `epics.epics()["E8.0"]` → **KeyError**. Repoint |
| `tests/test_freeze.py:110` | asserts `"E8.0"` and `"E8.4"` in a docstring. Repoint |
| INV-064, INV-074, INV-081, INV-083, INV-087 | each names E8.0/E8.2/E8.3/E8.4 as a coming consumer. Rewrite to name the email and `freeze_check`. **INV-064 and INV-074 change meaning**, not wording |
| INV-065 (`logs/sel_calls.jsonl`) | **dormant** — no loop, no second log. The rule stays right and unexercised; the INV-082 precedent |
| `hard_core.yaml::open_gaps` | three of four entries describe things that will now never exist. Record as **withdrawn**, not pending |
| `evolution/pre_loop_baseline.yaml` | keeps its name and its place in the hard core; it is the email's comparison line. Whoever is judged by a baseline must not be able to retake it, and that now means the operator's agents |

*Done when:* `grep -rn "E8\." newz tools tests` returns only the mapping table's
own references; no document, invariant or registry asserts a consumer that does
not exist; ledger clean, suite green.

*Depends on:* nothing, but it lands with E3A.3.

---

**Evidence S3A-E.** The email is read, and the falsifier: **did anything in it
change a decision the operator took?**

**Decision rule.** *Rule 6, and stated as such.* If the operator judges after a
month that the email has not changed a decision, it is filing — stop sending it,
and record that the sensor layer's only real consumer is a session with an agent,
which is what the SEL proposal's §13.1 measured. **This is a judgment and not a
threshold**; an earlier draft wrote *"two consecutive weeks unread"*, which has no
instrument and could never have fired.

---

## 6. Red team

*Four rounds. The structural separation the SEL proposal specified — fresh
context, artifact only, instructed to refute — was not used in any of them, which
is the standing weakness of every red team in this repo this week.*

### Defects found in this proposal, and fixed

**F1 — the email's trigger was coupled to the failure it exists to report.**
Firing on a `perspective` row dated today is how `SleepScheduler` detects its own
completion — but that scheduler *"yields the night if the store is busy"* and
*"missing a night is harmless."* On the night sleep is skipped, no row appears and
no email is sent: the day you most need the report is the day it is silent, and
that is the ordinary case, not the catastrophic one. **A report must not be gated
on the thing it reports.** *Fixed* — a clock trigger, and the monitor outside the
being removes the coupling rather than working around it.

**F2 — the baseline reads a reading count and means a day count, twice over.**
`pre_loop.propose()` refuses below seven readings while its comment explains the
threshold in nights, and it records every reading id it used — 28 per metric
nightly, **672 hourly**, about 19,000 ids in a hand-readable file inside the hard
core that INV-087 makes load-bearing rather than droppable. A guard that keeps
passing while its reason stops being true is the INV-044 failure, introduced by
this proposal. *Fixed* — the baseline takes the last reading of each day.

**F3 — moving the writer out destroys the readings' value as a liveness signal.**
Under the old design a missing reading meant the being was down; with the monitor
outside, readings arrive forever, including for a being that died a week ago.
This is F1's defect relocated by F1's own fix. *Fixed* — liveness derives only
from being-written rows, and a test stops the being and asserts the email still
says so.

**F4 — the surface's read page would fail by looking fine.**
`surface/generate.py:380` records provenance as `m.record("read",
"metric_readings", [ids])`, and E3.5 closes on a byte-comparable rebuild from a
verified backup. Split the database and the rebuild sees no such table; the
generator's existing `except sqlite3.OperationalError` renders *"No readings yet
— this store has not taken the migration"*, which is **a page that looks correct
and is wrong** — the R-37 shape this project keeps finding. *Fixed* —
`rebuild_check` restores both, and the fallback distinguishes *the monitor
database is absent* from *there are no readings*: the first is a fact about the
restore, the second about the being.

**F5 — backups cover exactly two files.** `run_backup(main, interior, dest)`
copies and verifies each with a `verify_table` apiece. A third is unprotected
unless added — and it holds the series `pre_loop_baseline.yaml` pins ids into.
*Fixed* — `monitor.db` joins the backup with its own verify table.

**F6 — the Decision rule could not fire.** *"Two consecutive weeks unread"* has no
instrument, and Rule 0 says a figure without one says so. *Fixed* — restated as
an operator judgment under Rule 6.

### Found, not caused by this proposal, and recorded

**F7 — the freeze already has no refusing caller.** INV-074 says a diff touching
a canonical instrument *"is refused for the loop, and recorded for the
operator"*, and `freeze_check.py` exits 2 as the loop and 0 as the operator.
`tools/gate.py:72` invokes it with **`--operator`** — the non-refusing mode. The
refusing half has no caller today, before anything is struck. **Removing the loop
does not make the freeze advisory; it reveals that it already is.** The ledger row
should say so rather than imply a refusal that has never happened. Whether that
mode gets a caller is a real question and is not answered here.

**F8 — the call-log scan is unbounded and now runs 24× more often.**
`consequence._declines` linearly scans `logs/llm_calls.jsonl` and JSON-parses
every line on every `record_all`; `since` is available and never used to seek.
Timed this session: **0.158s over 18MB**, and the file grows monotonically —
roughly 470MB/year at the current rate, ~4s a scan, 24 times a day. Not a reason
to avoid the cadence. Recorded as a known trend; the cheap fix when it matters is
to read the file backwards and stop at `since`.

### Raised and cleared

**F9 — could hourly readings move a metric's meaning?** No. Every metric is a
168h window and the cadence is not part of any definition, so
`definition_version` must not change and E2.8's series must not reset. Recorded
because if that reasoning is wrong the series breaks silently, and E2.8 exists to
catch precisely this.

**F10 — the outbound credential.** The objection was that `GMAIL_PASS` becomes
live in a process that also extracts hostile web content. It withdraws twice
over: the being already holds and uses `TELEGRAM_BOT_TOKEN` outward, and under
this design the credential is not in the being's process at all.

**F11 — a second process writing the being's store.** Retired by the separate
database: the monitor never opens `newz.db` for writing.

### Standing risks, accepted

**F12 — a process nobody started sends nothing.** The monitor is started by hand,
exactly as the being is, so its failure mode is the being's own: if it is not
running there is no email, and the email's absence is the only signal. **This is
the residual risk of the design and it is made small rather than removed.** With
the monitor outside the being, every partial failure now produces an email that
says what failed; only both processes being down produces silence.

**F13 — this is the fourth reader built for instruments nothing reads.** E8.1
gave the tools a registry, W7 gave the surface a rhythm, W3 gave the agreement
judge a caller — and `operator_agreement` still holds **0 rows**, `works_revised`
is **0**, `operator_disagreement_rate` reads `UNREADABLE`. S3A-E's falsifier is
aimed here and the Decision rule is what acts on it. **If this is right, the
phase is answered by not doing it, and a month is what it costs to find out.**

**F14 — striking Phase 8 leaves an unanswered direction.** *The operator must not
be the bottleneck; the system has to consume information and grow without a
person in the path.* This phase makes the operator more central, not less. What is
struck is a loop that would not have delivered that direction either — nothing in
Phases 4–7 gives the being a path to change its own conditions. **It should be
recorded in PLAN as an unanswered direction rather than left implied.**

---

## 7. What this does not do

- **It does not reorder Phases 4–7**, and delivers no capability of the being.
- **It does not judge anything.** No model call in the phase; nothing on the page
  is authored.
- **It does not claim the email will be read.** S3A-E asks; the Decision rule
  acts.
- **It does not delete the SEL proposal.** `2026-08-19-the-self-evolving-loop.md`
  stays, marked superseded, with its §11 steps 1–4 recorded as delivered — six
  rounds of red team produced the machinery this phase keeps.

---

## 8. For approval

1. **Phase 3A as written** — E3A.1 through E3A.4, about a day.
2. **Phase 8 struck**, with §5's mapping and §5's code and ledger work.
3. **F7 — does the freeze's refusing mode get a caller?** Separate from this
   proposal and worth an answer: today nothing has ever refused a diff against a
   canonical instrument.
4. **F14 — is the unanswered direction recorded in PLAN?** Recommended yes, as a
   line in §"What this plan does not do".
