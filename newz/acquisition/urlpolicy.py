"""What may be fetched, decided before anything is opened.

Pure: this module resolves nothing and connects to nothing, so the rules can be
tested exhaustively against strings and addresses without a network. The fetcher
calls it three times — once on the target, once on every address that target
resolves to, and once per redirect hop — and refuses on the first no.

The address rules are the SSRF boundary. A URL that resolves to a loopback,
private, link-local, or reserved address is refused whatever it claims to be,
because the interesting attack is not a hostile URL but an ordinary-looking one
whose DNS answer points inside the house.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from newz.domain.enums import FetchRefusal

DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True, slots=True)
class UrlPolicy:
    allowed_schemes: frozenset[str] = frozenset({"https", "http"})
    allowed_ports: frozenset[int] = frozenset({80, 443})
    max_redirects: int = 3
    #: Off everywhere but the offline fixture harness, which serves from a
    #: transport that never opens a socket at all.
    allow_non_public_addresses: bool = False
    #: When set, the host must appear here: the catalog is the allowlist.
    allowed_hosts: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class UrlVerdict:
    allowed: bool
    refusal: FetchRefusal | None
    scheme: str = ""
    host: str = ""
    port: int = 0
    path: str = "/"
    detail: str = ""


def inspect_url(url: str, policy: UrlPolicy) -> UrlVerdict:
    """Decide a URL on its face, before any name is resolved."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return UrlVerdict(False, FetchRefusal.URL_MALFORMED, detail=url)

    scheme = parts.scheme.lower()
    # Scheme first: `file:///etc/passwd` has no network location either, and
    # naming the scheme is the more useful refusal to read.
    if scheme and scheme not in policy.allowed_schemes:
        return UrlVerdict(False, FetchRefusal.SCHEME_NOT_ALLOWED, detail=scheme)
    if not scheme or not parts.netloc:
        return UrlVerdict(False, FetchRefusal.URL_MALFORMED, detail=url)
    if parts.username or parts.password:
        # Credentials in a URL are either a secret in the ledger or a
        # misreading of the host by something downstream. Both are refusals.
        return UrlVerdict(False, FetchRefusal.CREDENTIALS_IN_URL, detail=url)

    host = (parts.hostname or "").lower()
    if not host:
        return UrlVerdict(False, FetchRefusal.URL_MALFORMED, detail=url)

    try:
        port = parts.port or DEFAULT_PORTS[scheme]
    except ValueError:
        return UrlVerdict(False, FetchRefusal.PORT_NOT_ALLOWED, detail=url)
    if port not in policy.allowed_ports:
        return UrlVerdict(False, FetchRefusal.PORT_NOT_ALLOWED, detail=str(port))

    if policy.allowed_hosts and host not in policy.allowed_hosts:
        return UrlVerdict(False, FetchRefusal.HOST_NOT_IN_CATALOG, detail=host)

    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"

    return UrlVerdict(True, None, scheme=scheme, host=host, port=port, path=path)


def inspect_address(address: str, policy: UrlPolicy) -> FetchRefusal | None:
    """Refuse anything that is not a public unicast address."""
    if policy.allow_non_public_addresses:
        return None
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return FetchRefusal.HOST_NOT_RESOLVABLE
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return FetchRefusal.NON_PUBLIC_ADDRESS
    # An IPv4-mapped IPv6 address that wraps a private v4 address passes every
    # check above on the v6 form, so it is unwrapped and re-asked.
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        return inspect_address(str(mapped), policy)
    return None


def inspect_redirect(
    from_url: str, to_url: str, hop: int, policy: UrlPolicy
) -> UrlVerdict:
    """Every hop is a new fetch decision, and one rule the first fetch did not need."""
    if hop > policy.max_redirects:
        return UrlVerdict(False, FetchRefusal.REDIRECT_LIMIT, detail=str(hop))

    origin = urlsplit(from_url)
    verdict = inspect_url(to_url, policy)
    if not verdict.allowed:
        if verdict.refusal in (FetchRefusal.SCHEME_NOT_ALLOWED, FetchRefusal.URL_MALFORMED):
            return UrlVerdict(False, FetchRefusal.REDIRECT_OFF_POLICY, detail=to_url)
        return verdict

    if origin.scheme.lower() == "https" and verdict.scheme == "http":
        return UrlVerdict(False, FetchRefusal.REDIRECT_SCHEME_DOWNGRADE, detail=to_url)

    return verdict
