"""The only module in the package that opens a socket.

`ARCHITECTURE.md` puts fetch behind its own trust boundary and runs it as its own
process with its own egress limits. Keeping the socket in one small module is
the in-process half of that: everything else in `newz` can be read without
asking whether it might reach the network, and the Gate 0 suite enforces it.

The transport is an interface so the whole fetch path — redirects, ceilings,
MIME normalization, decompression limits — can be exercised offline against
fixtures. The fixture transport is not a mock of the policy; it is a stand-in
for the far side of the wire, and the policy under test is the real one.
"""

from __future__ import annotations

import http.client
import socket
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RawResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: object  # anything with .read(n) -> bytes

    def header(self, name: str, default: str = "") -> str:
        lowered = name.lower()
        for key, value in self.headers:
            if key.lower() == lowered:
                return value
        return default


class Transport(Protocol):
    def open(
        self, *, scheme: str, host: str, port: int, path: str, address: str, timeout: float
    ) -> RawResponse: ...

    def resolve(self, host: str) -> tuple[str, ...]: ...


class SocketTransport:
    """Real HTTP, with the connection pinned to an address that was checked.

    Resolution and connection are separated on purpose. The fetcher resolves,
    checks every answer against the address rules, and then asks the transport to
    connect to *that address* while still presenting the real hostname for TLS
    and for `Host`. Connecting by name after checking by name would leave the
    window in which a second DNS answer arrives — the rebinding case, which is
    the one that matters for a system that fetches URLs it did not choose.
    """

    #: Overridden by `NEWZ_USER_AGENT`. Several sources refuse an agent with no
    #: way to reach its operator — Wikipedia answers 403 — and being reachable
    #: is the minimum a system owes a site it reads without asking.
    default_user_agent = "newz/0.1 (research agent for a single operator)"

    def __init__(self, user_agent: str = "") -> None:
        import os

        self.user_agent = (
            user_agent or os.environ.get("NEWZ_USER_AGENT", "") or self.default_user_agent
        )

    def resolve(self, host: str) -> tuple[str, ...]:
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except OSError:
            return ()
        return tuple(dict.fromkeys(info[4][0] for info in infos))

    def open(
        self, *, scheme: str, host: str, port: int, path: str, address: str, timeout: float
    ) -> RawResponse:
        if scheme == "https":
            import ssl

            connection = http.client.HTTPSConnection(
                host, port, timeout=timeout, context=ssl.create_default_context()
            )
        else:
            connection = http.client.HTTPConnection(host, port, timeout=timeout)

        # Pin the socket to the checked address while the connection keeps the
        # hostname for TLS verification and the Host header.
        connection._create_connection = lambda addr, tmo, src: socket.create_connection(  # type: ignore[method-assign]
            (address, addr[1]), tmo, src
        )
        try:
            connection.request(
                "GET",
                path,
                headers={
                    "Host": host,
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "gzip",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
        except http.client.HTTPException as error:
            # The transport owns the protocol, so it owns protocol failures. A
            # server answering with a malformed status line is the far side
            # being broken, and the fetcher above cannot catch an exception from
            # a module it is not allowed to import — so it is translated here
            # into the error contract the fetcher does handle.
            raise OSError(f"{type(error).__name__}: {error}") from error
        return RawResponse(
            status=response.status,
            headers=tuple(response.getheaders()),
            body=response,
        )
