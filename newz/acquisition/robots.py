"""robots.txt: asking before reading, and honouring the answer.

Eighteen one-off reads with a contactable agent is within any reasonable
reading of ordinary use. A pilot reading the same twenty sources every day is
not — it is a standing arrangement with somebody who never agreed to one, and
`robots.txt` is where a site states the terms of that arrangement.

The parser is written here rather than taken from the standard library because
`urllib.robotparser` reaches the network to do its job, and this package keeps
exactly one door open for that. Parsing lines is not the part that needs a
socket.

Two decisions worth stating.

**Unavailable and unreachable are different answers**, and RFC 9309 §2.3.1
already says which is which rather than leaving it to taste. A 4xx means the
site published no rules, so ordinary use applies and the read proceeds. A 5xx or
a connection failure means the site did not answer at all, and reading on
regardless would be deciding on their behalf — so it disallows for that read and
is asked again later, rather than being cached as a yes.

**The longest matching rule wins, and `Allow` beats `Disallow` on a tie.** That
is what the de-facto standard says and what site owners expect; a stricter
reading would refuse paths sites deliberately opened.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import unquote, urlsplit

#: How long a fetched robots.txt stands before it is asked for again.
CACHE_HOURS = 24

_DIRECTIVE = re.compile(r"^\s*([A-Za-z-]+)\s*:\s*(.*?)\s*$")


@dataclass(frozen=True, slots=True)
class Rule:
    allow: bool
    path: str

    @property
    def specificity(self) -> int:
        return len(self.path)

    def matches(self, path: str) -> bool:
        """Prefix match, with `*` and an end-anchoring `$` as the standard has them."""
        pattern = self.path
        if not pattern:
            return False
        anchored = pattern.endswith("$")
        if anchored:
            pattern = pattern[:-1]
        parts = pattern.split("*")
        position = 0
        for index, part in enumerate(parts):
            if not part:
                continue
            found = path.find(part, position)
            if index == 0:
                if not path.startswith(part):
                    return False
                position = len(part)
                continue
            if found == -1:
                return False
            position = found + len(part)
        if anchored:
            return position == len(path)
        return True


@dataclass(frozen=True, slots=True)
class Robots:
    """The rules that apply to one agent on one host."""

    host: str
    rules: tuple[Rule, ...] = ()
    crawl_delay: float | None = None
    fetched: bool = True
    detail: str = ""

    def allows(self, path: str) -> bool:
        """Whether this path may be read. The longest matching rule decides."""
        if not self.fetched:
            return False
        candidates = [rule for rule in self.rules if rule.matches(path or "/")]
        if not candidates:
            return True
        best = max(candidates, key=lambda rule: (rule.specificity, rule.allow))
        return best.allow

    def as_record(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "rules": [{"allow": rule.allow, "path": rule.path} for rule in self.rules],
            "crawl_delay": self.crawl_delay,
            "fetched": self.fetched,
            "detail": self.detail,
        }


def parse(body: str, agent: str, host: str = "") -> Robots:
    """Read the groups that apply to this agent, falling back to `*`.

    A named group for our agent wins outright over `*`, because a site that
    wrote a rule about us meant it.
    """
    agent_token = agent.split("/")[0].strip().lower()
    groups: dict[str, list[Rule]] = {}
    delays: dict[str, float] = {}
    current: list[str] = []
    starting_group = False

    for raw in body.splitlines():
        line = raw.split("#", 1)[0]
        match = _DIRECTIVE.match(line)
        if not match:
            continue
        field_name, value = match.group(1).lower(), match.group(2)
        if field_name == "user-agent":
            if not starting_group:
                current = []
                starting_group = True
            current.append(value.strip().lower())
            groups.setdefault(value.strip().lower(), [])
            continue
        starting_group = False
        if not current:
            continue
        if field_name in ("allow", "disallow"):
            path = unquote(value)
            for name in current:
                groups.setdefault(name, []).append(Rule(field_name == "allow", path))
        elif field_name == "crawl-delay":
            try:
                for name in current:
                    delays[name] = float(value)
            except ValueError:
                continue

    for name in (agent_token, agent.strip().lower(), "*"):
        if name in groups:
            return Robots(
                host=host,
                rules=tuple(groups[name]),
                crawl_delay=delays.get(name),
                detail=f"group {name!r}",
            )
    return Robots(host=host, rules=(), detail="no applicable group")


@dataclass
class RobotsCache:
    """What each host said, and when it will be asked again."""

    entries: dict[str, tuple[Robots, datetime]] = field(default_factory=dict)
    hours: int = CACHE_HOURS

    def get(self, host: str, now: datetime) -> Robots | None:
        entry = self.entries.get(host)
        if entry is None:
            return None
        robots, expires = entry
        if now >= expires:
            del self.entries[host]
            return None
        return robots

    def put(self, host: str, robots: Robots, now: datetime) -> None:
        self.entries[host] = (robots, now + timedelta(hours=self.hours))


def path_of(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path
