from pathlib import Path

import pytest

from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"

CONSTITUTION_YAML = """
clauses:
  - id: honesty-001
    text: I do not knowingly assert things I believe to be false.
    severity: hard
  - id: no-flattery-001
    text: I do not flatter or soften disagreement into agreement.
    severity: firm
  - id: style-001
    text: I prefer plain language.
    severity: soft
"""


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "newz.db")
    apply_pending(conn, MAIN_SQL)
    conn.execute(
        "INSERT INTO constitution (version, ts, clauses_yaml, change_summary,"
        " approval_status) VALUES (1, 1.0, ?, 'test', 'active')",
        (CONSTITUTION_YAML,),
    )
    conn.execute(
        "INSERT INTO character_core (version, ts, content, source)"
        " VALUES ('v1', 1.0, 'Plain, curious, honest.', 'test')"
    )
    conn.execute(
        "INSERT INTO perspective (version, ts, content, diff_json, token_count)"
        " VALUES (1, 1.0, '# Perspective\\nI am Lumen. I hold that testing matters.', '{}', 10)"
    )
    conn.commit()
    yield conn
    conn.close()


class LexicalEmbedder:
    """Deterministic offline stand-in: cosine over content-word vectors.

    Near-identical wording scores high, distinct topics score low — enough
    for tests that only need "is this the same point again". The paraphrase
    case, which lexical similarity provably cannot catch, is covered by the
    purpose-built stub in test_concerns.py and by the live measurement
    recorded in newz/concerns/advance.py.
    """

    _STOP = frozenset("a an and are as at be by for from in is it of on or that "
                      "the to was with i my not".split())

    def _vec(self, text: str):
        import hashlib

        words = {w for w in "".join(
            ch.lower() if ch.isalnum() else " " for ch in text or ""
        ).split() if w not in self._STOP and len(w) > 2}
        v = [0.0] * 64
        for w in words:
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1.0
        return v or [0.0] * 64

    def embed(self, texts):
        return [self._vec(t) for t in texts]


class FakeLLM:
    """Scripted stand-in for LLMClient: pops responses per role.

    Entries are (role, text) or (role, text, truncated) so tests can
    exercise the max_tokens-truncation path.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, role, system, user, **kw):
        self.calls.append({"role": role, "system": system, "user": user, **kw})
        entry = self.responses.pop(0)
        expect_role, text = entry[0], entry[1]
        truncated = entry[2] if len(entry) > 2 else False
        assert role == expect_role, f"expected {expect_role} call, got {role}"

        class R:
            pass

        r = R()
        r.text = text
        r.prompt_tokens = 0
        r.completion_tokens = 0
        r.truncated = truncated
        return r
