"""Official OKX source-authority rule shared by the historical client and the live recorder.

A configured endpoint may only be used if it resolves *syntactically* to an
official OKX-controlled hostname in an official secure endpoint form. This is a
deterministic provenance boundary (nothing labelled ``okx`` may come from another
host), not a network/DNS ownership check.

Rule:

* hostname (case-insensitive, as parsed by ``urllib.parse.urlsplit``) is exactly
  ``okx.com`` or ends in ``.okx.com``, and every label is a plain LDH label;
* no userinfo, no query, no fragment;
* REST: scheme ``https``, no path other than empty/``/``, port omitted or 443;
* WebSocket: scheme ``wss``, port 8443 (the documented OKX secure WebSocket
  form, e.g. ``wss://ws.okx.com:8443``, ``wss://wseea.okx.com:8443``,
  ``wss://wsus.okx.com:8443``), exact path from the caller's allow-list.

Invalid endpoints are rejected with ``ValueError``; they are never rewritten.
"""

from __future__ import annotations

import re
import urllib.parse

OKX_ROOT_DOMAIN = "okx.com"
REST_ALLOWED_PORTS = frozenset({None, 443})
WS_ALLOWED_PORTS = frozenset({8443})
_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def is_official_okx_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.lower()
    if host != OKX_ROOT_DOMAIN and not host.endswith("." + OKX_ROOT_DOMAIN):
        return False
    return all(_LABEL.match(label) for label in host.split("."))


def _split_official(url: str, scheme: str, allowed_ports: frozenset[int | None]) -> urllib.parse.SplitResult:
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 0x20 for c in url) or "\\" in url:
        raise ValueError(f"not an official OKX {scheme} URL: {url!r}")
    u = urllib.parse.urlsplit(url)
    if u.scheme.lower() != scheme:
        raise ValueError(f"OKX endpoint must use {scheme}://, got {url!r}")
    if "@" in u.netloc or u.username is not None or u.password is not None:
        raise ValueError(f"OKX endpoint must not contain credentials/userinfo: {url!r}")
    if u.query or "?" in url:
        raise ValueError(f"OKX endpoint must not contain a query string: {url!r}")
    if u.fragment or "#" in url:
        raise ValueError(f"OKX endpoint must not contain a fragment: {url!r}")
    if not is_official_okx_host(u.hostname):
        raise ValueError(f"not an official OKX host (must be okx.com or *.okx.com): {url!r}")
    try:
        port = u.port
    except ValueError:
        raise ValueError(f"invalid port in OKX endpoint: {url!r}") from None
    if port not in allowed_ports:
        raise ValueError(f"port {port} is not allowed for OKX {scheme} endpoints: {url!r}")
    return u


def validate_okx_rest_base_url(url: str) -> urllib.parse.SplitResult:
    """Validate an official OKX REST base URL (``https://<host>.okx.com`` with no path)."""
    u = _split_official(url, "https", REST_ALLOWED_PORTS)
    if u.path not in ("", "/"):
        raise ValueError(f"OKX REST base URL must not contain a path, got {url!r}")
    return u


def validate_okx_ws_url(url: str, allowed_paths: frozenset[str] | tuple[str, ...]) -> urllib.parse.SplitResult:
    """Validate an official OKX WebSocket URL whose path is exactly one of ``allowed_paths``."""
    u = _split_official(url, "wss", WS_ALLOWED_PORTS)
    if u.path not in allowed_paths:
        raise ValueError(f"OKX WebSocket path {u.path!r} is not allowed (expected one of {sorted(allowed_paths)}): "
                         f"{url!r}")
    return u
