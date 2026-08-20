#!/usr/bin/env python3
"""Run the ambient loop (P2 Phase 0.4) — the being, live, operator-only.

Boot: migrations → WAL checkpoint → constitution + gate + channel → poll.
Ctrl-C to stop. Rehearsal boundary: only the operator's chat is answered.

Visibility:
  default        INFO — inbound messages, composition size/tokens per
                 attempt, every gate verdict with clause + span, send
                 results, exchange summaries.
  -v/--verbose   DEBUG — adds full draft texts before the gate sees them.
  logs/llm_calls.jsonl   every LLM call whole (role, prompts, response,
                 tokens, duration), size-rotated — the S2 §16 record that
                 makes the gate diagnosable after the fact.
"""

from __future__ import annotations

import asyncio
import datetime
import traceback
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.ambient.loop import AmbientLoop
from newz.channels.telegram import TelegramChannel
from newz.config import load
from newz.gate.constitution import load_active_constitution
from newz.gate.outbound import OutboundGate
from newz.llm.client import LLMClient
from newz.store.db import boot_checkpoint, open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


def main() -> int:
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    cfg = load()
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured", file=sys.stderr)
        return 1
    conn = open_db(cfg.main_db_path)
    applied = apply_pending(conn, MAIN_SQL)
    if applied:
        logging.info("migrations applied: %s", applied)
    boot_checkpoint(conn)

    have_perspective = conn.execute("SELECT COUNT(*) FROM perspective").fetchone()[0]
    if not have_perspective:
        print("no Perspective in store — run tools/run_first_sleep.py first", file=sys.stderr)
        return 1

    constitution = load_active_constitution(conn)
    from newz.llm.recorder import CallRecorder

    recorder = CallRecorder(cfg.repo_root / "logs" / "llm_calls.jsonl")
    client = LLMClient(cfg, timeout=300, recorder=recorder)
    gate = OutboundGate(client, constitution, conn)
    channel = TelegramChannel(cfg.telegram_bot_token, cfg.telegram_chat_id)

    retriever = None
    try:
        from newz.memory.embeddings import Embedder
        from newz.memory.retrieval import Retriever

        retriever = Retriever(conn, Embedder(cfg))
        embedded = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE embedding IS NOT NULL"
        ).fetchone()[0]
        logging.info("retrieval live over %d embedded episodes", embedded)
    except Exception as e:
        logging.warning("retrieval unavailable (%s) — conversation runs without recall", e)

    loop = AmbientLoop(conn, client, gate, channel, cfg.operator_id or "operator",
                       retriever=retriever)

    from newz.deliberation.lite import Deliberator, DeliberationScheduler
    from newz.sleep.nightly import SleepScheduler
    from newz.store.backup import BackupScheduler
    from newz.world.substrate import SubstrateScheduler
    from newz.ambient.noticing import SurfaceScheduler

    backups = BackupScheduler(cfg.main_db_path, cfg.interior_db_path, cfg.backups_dir)
    sleeper = SleepScheduler(cfg.main_db_path, client, cfg.operator_id or "operator",
                             hour=cfg.sleep_hour,
                             embedder=retriever._embedder if retriever else None)
    # Research ON: P2 2.3 requires the cascade to RUN inside deliberation,
    # not merely to exist. The S2 §9.1 budget gate gates it from here.
    thinker = DeliberationScheduler(Deliberator(
        cfg.main_db_path, client,
        embedder=retriever._embedder if retriever else None,
        research=True, log_path=cfg.repo_root / "logs" / "llm_calls.jsonl",
        feeds_path=cfg.repo_root / "data" / "feeds.yaml"))
    # S2 §6.1: the being is told how it is running, once a day, folded.
    # Without this its newest information about itself was 2026-06-13.
    substrate = SubstrateScheduler(
        cfg.main_db_path,
        log_path=cfg.repo_root / "logs" / "llm_calls.jsonl",
        backups_dir=cfg.backups_dir, started_at=time.time())
    # S2 §6.1: the being may raise something nobody asked about, under
    # wake windows, maturity and rate gates. Its own connection, and the
    # ORDINARY outbound gate — an unprompted message is not privileged.
    surface = SurfaceScheduler(
        cfg.main_db_path, client, channel, cfg.operator_id or "operator",
        gate_factory=lambda c: OutboundGate(client, constitution, c))

    logging.info(
        "ambient loop up: constitution v%d (%d clauses), perspective present, "
        "operator=%s — rehearsal (operator-only)",
        constitution.version, len(constitution.clauses), cfg.operator_id,
    )

    async def _run() -> None:
        # Backups run for as long as the being does; a boot backup lands
        # before the first message is answered. Sleep runs nightly alongside,
        # on its own connection, yielding to conversation.
        background = [asyncio.create_task(backups.run()),
                      asyncio.create_task(sleeper.run()),
                      asyncio.create_task(thinker.run()),
                      asyncio.create_task(substrate.run()),
                      asyncio.create_task(surface.run())]
        try:
            await loop.run()
        finally:
            for t in background:
                t.cancel()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logging.info("stopped by operator")
    except BaseException:
        # A being that dies must say why. Without this the process exits and
        # the only evidence is a gap in the backups (2026-08-11: the loop
        # stopped between two health checks with no record of the cause).
        logging.critical("ambient loop died", exc_info=True)
        crash = cfg.repo_root / "logs" / "crash.log"
        crash.parent.mkdir(parents=True, exist_ok=True)
        with open(crash, "a") as fh:
            fh.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
            traceback.print_exc(file=fh)
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
