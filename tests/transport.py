"""A stand-in for the far side of the wire.

Not a mock of the fetcher's policy — the policy under test is the real one. This
supplies status lines, headers and bytes, so redirects, ceilings, MIME
normalization, decompression limits and address checks all run exactly as they
would against a network, offline and deterministically.

Hosts resolve to a public unicast address, so the SSRF boundary stays in force
during the offline tests rather than being switched off for them. The RFC 5737
documentation ranges are not usable here: `ipaddress` classifies them as
private, which is correct of it and would make every fixture fetch a refusal.
"""

from __future__ import annotations

import gzip
import io
from dataclasses import dataclass, field

from newz.acquisition.transport import RawResponse


@dataclass
class Reply:
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    #: Raise a timeout instead of replying.
    slow: bool = False
    #: Refuse the connection instead of replying.
    unreachable: bool = False


class SlowBody:
    """A body that yields one chunk and then never finishes."""

    def __init__(self, chunk: bytes) -> None:
        self._chunk = chunk
        self._sent = False

    def read(self, _size: int) -> bytes:
        if self._sent:
            raise TimeoutError("the far side stopped sending")
        self._sent = True
        return self._chunk


@dataclass
class FixtureTransport:
    replies: dict[str, Reply] = field(default_factory=dict)
    addresses: dict[str, tuple[str, ...]] = field(default_factory=dict)
    default_address: str = "93.184.216.34"
    requested: list[str] = field(default_factory=list)

    def serve(self, url: str, reply: Reply) -> None:
        self.replies[url] = reply

    def serve_html(self, url: str, body: str, **headers: str) -> None:
        self.serve(
            url,
            Reply(
                headers={"Content-Type": "text/html; charset=utf-8", **headers},
                body=body.encode("utf-8"),
            ),
        )

    def serve_bytes(self, url: str, body: bytes, content_type: str, **headers: str) -> None:
        self.serve(url, Reply(headers={"Content-Type": content_type, **headers}, body=body))

    def serve_gzip(self, url: str, body: bytes, content_type: str = "text/plain") -> None:
        self.serve(
            url,
            Reply(
                headers={"Content-Type": content_type, "Content-Encoding": "gzip"},
                body=gzip.compress(body),
            ),
        )

    def serve_redirect(self, url: str, to: str, status: int = 302) -> None:
        self.serve(url, Reply(status=status, headers={"Location": to}))

    def resolve(self, host: str) -> tuple[str, ...]:
        return self.addresses.get(host, (self.default_address,))

    def open(
        self, *, scheme: str, host: str, port: int, path: str, address: str, timeout: float
    ) -> RawResponse:
        url = f"{scheme}://{host}{'' if port in (80, 443) else f':{port}'}{path}"
        self.requested.append(url)
        reply = self.replies.get(url)
        if reply is None:
            return RawResponse(404, (("Content-Type", "text/plain"),), io.BytesIO(b"not found"))
        if reply.unreachable:
            raise OSError("connection refused")
        if reply.slow:
            return RawResponse(
                reply.status, tuple(reply.headers.items()), SlowBody(reply.body[:16])
            )
        headers = dict(reply.headers)
        headers.setdefault("Content-Length", str(len(reply.body)))
        return RawResponse(reply.status, tuple(headers.items()), io.BytesIO(reply.body))
