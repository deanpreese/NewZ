"""Serving the surface, and the one value that decides who can reach it
(P4 epic E3.4).

**Rule 3: outward capabilities are built public-ready and left unpublished.**
Reach is a config change and never a redesign — which means this file must
already do everything a public surface needs, and must default to nobody.

**The whole decision rides on one value**, so it is built to fail closed:

  - anything that is not the literal string `open` is treated as `local`, so a
    typo cannot expose the surface;
  - `local` binds `127.0.0.1`, which no other machine can route to;
  - the server refuses to start bound outward unless the value says `open`,
    rather than trusting a caller to pass the right host.

**No index, ever.** Stable identifiers are what make a piece citable; being
crawled is a separate decision nobody has made. `robots.txt` disallows
everything and every page carries `noindex, nofollow` — belt and braces,
because the two fail differently: a robots file is a request and a meta tag is
a request, and neither is a permission system. What actually keeps the surface
private is the bind address.

**P4 Decision 1 is unmade** — when, who the first reader is, and what wording
they see first. Until it is made this is `local`, and nothing in this codebase
writes the setting.
"""

from __future__ import annotations

import functools
import http.server
import logging
import socketserver
from pathlib import Path

logger = logging.getLogger(__name__)

LOCAL_HOST = "127.0.0.1"
OPEN_HOST = "0.0.0.0"  # noqa: S104 — the point of the setting, guarded below


def host_for(reach: str) -> str:
    """The bind address for a reach setting. Anything unrecognised is local."""
    return OPEN_HOST if (reach or "").strip().lower() == "open" else LOCAL_HOST


def is_open(reach: str) -> bool:
    return host_for(reach) == OPEN_HOST


class _Handler(http.server.SimpleHTTPRequestHandler):
    """Static files, no directory listing, no index anywhere.

    **The surface is markdown** *(operator, 2026-08-22)*, so `.md` is typed
    explicitly rather than left to `mimetypes`, which resolves it to
    `application/octet-stream` on some systems — and an octet-stream is a
    download prompt, not a page. `text/markdown` is the true type and is what
    a markdown reader keys off; a plain browser may still offer to save the
    file rather than render it, which is the honest consequence of publishing
    documents instead of a website.
    """

    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".md": "text/markdown; charset=utf-8"}

    def list_directory(self, path):  # noqa: D102 — no listing, ever
        self.send_error(404, "no index")
        return None

    def end_headers(self):
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def log_message(self, fmt, *args):  # keep the being's log readable
        logger.info("surface: " + fmt, *args)


def serve(directory: Path, *, reach: str, port: int,
          server_factory=socketserver.TCPServer):
    """Build the server. Binding outward requires the setting, not an argument.

    **There is no `host` parameter, and that is the guard.** An earlier version
    took the setting, derived the host, and then raised if the host was outward
    without the setting — a check that could never fire, because the host came
    from the setting. A guard that cannot fire reads as protection and is not
    one, so it is gone: the only way to reach `0.0.0.0` from here is to have
    written `open` in the config, and no argument to this function can produce
    it.
    """
    host = host_for(reach)
    handler = functools.partial(_Handler, directory=str(directory))
    server_factory.allow_reuse_address = True
    httpd = server_factory((host, port), handler)
    logger.info("surface served at http://%s:%d/ (reach=%s)", host, port,
                "open — reachable by anyone who can route here" if host == OPEN_HOST
                else "local — this machine only")
    return httpd
