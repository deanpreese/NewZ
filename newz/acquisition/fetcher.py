"""The safe fetcher.

Every ceiling here is enforced while reading rather than after: a size limit
checked on `Content-Length` is a limit on what a server admits to, and a
decompression limit checked on the finished buffer is a limit that has already
been exceeded. The body is read in chunks and abandoned the moment a ceiling is
crossed.

Nothing in this module decides whether what it fetched is evidence. It produces
bytes, a hash, an identity, and a record of what happened — including when what
happened was a refusal.
"""

from __future__ import annotations

import hashlib
import zlib
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from newz.acquisition.transport import RawResponse, Transport
from newz.acquisition.urlpolicy import UrlPolicy, inspect_address, inspect_redirect, inspect_url
from newz.domain.enums import AttemptOutcome, FetchRefusal

CHUNK = 64 * 1024

#: Declared content types the system knows how to route, and what each
#: normalizes to. Anything else is refused rather than guessed at.
MIME_NORMALIZATION: dict[str, str] = {
    "text/html": "text/html",
    "application/xhtml+xml": "text/html",
    "text/plain": "text/plain",
    "text/csv": "text/csv",
    "application/pdf": "application/pdf",
    "application/json": "application/json",
    "application/ld+json": "application/json",
    "text/xml": "application/xml",
    "application/xml": "application/xml",
    "application/rss+xml": "application/xml",
    "application/atom+xml": "application/xml",
}

#: Leading bytes that contradict a declared type. A body that says it is a PDF
#: and does not begin like one is mislabeled, and mislabeling is the cheap way
#: past a router that trusts the header.
MAGIC: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "application/json": (b"{", b"[",),
}


@dataclass(frozen=True, slots=True)
class FetchPolicy:
    max_bytes: int = 8 * 1024 * 1024
    timeout_seconds: float = 20.0
    #: A compressed body may not expand past this, in bytes or in ratio.
    max_decompressed_bytes: int = 32 * 1024 * 1024
    max_decompression_ratio: int = 100
    url: UrlPolicy = field(default_factory=UrlPolicy)


@dataclass(frozen=True, slots=True)
class FetchResult:
    outcome: AttemptOutcome
    url: str
    final_url: str = ""
    status: int | None = None
    declared_mime: str = ""
    normalized_mime: str = ""
    body: bytes = b""
    content_hash: str = ""
    bytes_read: int = 0
    redirects: tuple[str, ...] = ()
    refusal: FetchRefusal | None = None
    detail: str = ""
    headers: tuple[tuple[str, str], ...] = ()

    @property
    def retained(self) -> bool:
        return self.outcome is AttemptOutcome.RETAINED


def normalize_mime(content_type: str) -> str:
    declared = content_type.split(";", 1)[0].strip().lower()
    return MIME_NORMALIZATION.get(declared, "")


def _refuse(url: str, refusal: FetchRefusal, detail: str = "", **extra) -> FetchResult:
    return FetchResult(
        outcome=AttemptOutcome.REFUSED, url=url, refusal=refusal, detail=detail, **extra
    )


def _read_body(response: RawResponse, policy: FetchPolicy) -> tuple[bytes, int, FetchRefusal | None]:
    """Read to a ceiling, decompressing as we go, and stop at the first breach."""
    encoding = response.header("Content-Encoding").strip().lower()
    declared_length = response.header("Content-Length").strip()
    if declared_length.isdigit() and int(declared_length) > policy.max_bytes:
        return b"", int(declared_length), FetchRefusal.RESPONSE_TOO_LARGE

    decompressor = None
    if encoding in ("gzip", "x-gzip"):
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif encoding == "deflate":
        decompressor = zlib.decompressobj()
    elif encoding not in ("", "identity"):
        return b"", 0, FetchRefusal.CONTENT_TYPE_NOT_ALLOWED

    raw_read = 0
    out = bytearray()
    while True:
        chunk = response.body.read(CHUNK)
        if not chunk:
            break
        raw_read += len(chunk)
        if raw_read > policy.max_bytes:
            return bytes(out), raw_read, FetchRefusal.RESPONSE_TOO_LARGE
        if decompressor is None:
            out += chunk
            continue
        out += decompressor.decompress(chunk, policy.max_decompressed_bytes + 1)
        if len(out) > policy.max_decompressed_bytes or (
            raw_read > 0 and len(out) > raw_read * policy.max_decompression_ratio
        ):
            return bytes(out), raw_read, FetchRefusal.DECOMPRESSION_LIMIT

    if decompressor is not None:
        out += decompressor.flush()
        if len(out) > policy.max_decompressed_bytes:
            return bytes(out), raw_read, FetchRefusal.DECOMPRESSION_LIMIT

    return bytes(out), raw_read, None


def fetch(url: str, transport: Transport, policy: FetchPolicy | None = None) -> FetchResult:
    """Fetch one URL under policy, following redirects it is allowed to follow."""
    policy = policy or FetchPolicy()
    current = url
    redirects: list[str] = []

    for hop in range(policy.url.max_redirects + 2):
        if hop == 0:
            verdict = inspect_url(current, policy.url)
        else:
            verdict = inspect_redirect(redirects[-2] if len(redirects) > 1 else url, current, hop, policy.url)
        if not verdict.allowed:
            return _refuse(url, verdict.refusal, verdict.detail, redirects=tuple(redirects))

        host = verdict.host
        literal = host.strip("[]")
        addresses = (literal,) if _is_literal_address(literal) else transport.resolve(host)
        if not addresses:
            return _refuse(
                url, FetchRefusal.HOST_NOT_RESOLVABLE, host, redirects=tuple(redirects)
            )
        for address in addresses:
            refusal = inspect_address(address, policy.url)
            if refusal is not None:
                # Every answer must be acceptable, not merely the first one: a
                # name that resolves to one public and one private address is
                # the rebinding case wearing a disguise.
                return _refuse(url, refusal, f"{host} -> {address}", redirects=tuple(redirects))

        try:
            response = transport.open(
                scheme=verdict.scheme,
                host=host,
                port=verdict.port,
                path=verdict.path,
                address=addresses[0],
                timeout=policy.timeout_seconds,
            )
        except TimeoutError as error:
            return _refuse(url, FetchRefusal.TIMEOUT, str(error), redirects=tuple(redirects))
        except OSError as error:
            return FetchResult(
                outcome=AttemptOutcome.ERROR,
                url=url,
                detail=f"{type(error).__name__}: {error}",
                redirects=tuple(redirects),
            )

        if response.status in (301, 302, 303, 307, 308):
            location = response.header("Location")
            if not location:
                return FetchResult(
                    outcome=AttemptOutcome.ERROR,
                    url=url,
                    status=response.status,
                    detail="redirect without a location",
                    redirects=tuple(redirects),
                )
            current = urljoin(current, location)
            redirects.append(current)
            continue

        if response.status == 429:
            return _refuse(
                url,
                FetchRefusal.RATE_LIMITED,
                response.header("Retry-After", "unspecified"),
                status=response.status,
                redirects=tuple(redirects),
            )
        if response.status >= 400:
            return FetchResult(
                outcome=AttemptOutcome.ERROR,
                url=url,
                final_url=current,
                status=response.status,
                detail=f"HTTP {response.status}",
                redirects=tuple(redirects),
            )

        declared = response.header("Content-Type")
        normalized = normalize_mime(declared)
        if not normalized:
            return _refuse(
                url,
                FetchRefusal.CONTENT_TYPE_NOT_ALLOWED,
                declared or "absent",
                status=response.status,
                redirects=tuple(redirects),
            )

        # A timeout can arrive mid-body as easily as on connect, and a read that
        # dies half way through is a refusal to record rather than an exception
        # to propagate: the far side was contacted, and that is a fact.
        try:
            body, raw_read, refusal = _read_body(response, policy)
        except TimeoutError as error:
            return _refuse(
                url,
                FetchRefusal.TIMEOUT,
                str(error),
                status=response.status,
                redirects=tuple(redirects),
            )
        except OSError as error:
            return FetchResult(
                outcome=AttemptOutcome.ERROR,
                url=url,
                status=response.status,
                detail=f"{type(error).__name__}: {error}",
                redirects=tuple(redirects),
            )
        if refusal is not None:
            return _refuse(
                url,
                refusal,
                f"{raw_read} bytes read",
                status=response.status,
                bytes_read=raw_read,
                redirects=tuple(redirects),
            )

        expected_magic = MAGIC.get(normalized)
        if expected_magic and not body.lstrip()[:8].startswith(expected_magic):
            return _refuse(
                url,
                FetchRefusal.CONTENT_TYPE_NOT_ALLOWED,
                f"declared {normalized}, body does not begin like one",
                status=response.status,
                bytes_read=raw_read,
                redirects=tuple(redirects),
            )

        return FetchResult(
            outcome=AttemptOutcome.RETAINED,
            url=url,
            final_url=current,
            status=response.status,
            declared_mime=declared,
            normalized_mime=normalized,
            body=body,
            content_hash=hashlib.sha256(body).hexdigest(),
            bytes_read=raw_read,
            redirects=tuple(redirects),
            headers=response.headers,
        )

    return _refuse(url, FetchRefusal.REDIRECT_LIMIT, str(len(redirects)), redirects=tuple(redirects))


def _is_literal_address(host: str) -> bool:
    return host.replace(".", "").isdigit() or ":" in host


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()
