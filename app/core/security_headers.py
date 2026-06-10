"""Security headers middleware â€” production-grade trust hygiene.

Adds OWASP-recommended security headers to every response:
- Content-Security-Policy (CSP)
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy
- Cross-Origin-Opener-Policy
- Cross-Origin-Resource-Policy

Designed for FastAPI/Starlette. Apply via app.add_middleware(SecurityHeadersMiddleware).
Headers are tunable per-server (scan_server.py vs vdr_server.py) via init kwargs.

References:
- OWASP Secure Headers Project: owasp.org/www-project-secure-headers
- securityheaders.com grading scale
- MDN web docs / web.dev recommendations 2026
"""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Default CSP â€” strict but allows inline styles for tagged designs.
# Caller can override per app via `csp=` kwarg.
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com "
    "  https://www.googletagmanager.com https://www.google-analytics.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https:; "
    "connect-src 'self' https://api.mollie.com https://*.duesight.nl "
    "  https://api.minimax.io https://ops.epo.org https://www.google-analytics.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self' https://api.mollie.com; "
    "object-src 'none'; "
    "upgrade-insecure-requests"
)

# Strict CSP for VDR upload â€” no third-party connections.
STRICT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self' data:; "
    "img-src 'self' data: blob:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'; "
    "upgrade-insecure-requests"
)

DEFAULT_PERMISSIONS_POLICY = (
    "accelerometer=(), ambient-light-sensor=(), autoplay=(self), "
    "battery=(), camera=(), display-capture=(), document-domain=(), "
    "encrypted-media=(), fullscreen=(self), geolocation=(), "
    "gyroscope=(), magnetometer=(), microphone=(), midi=(), "
    "payment=(self \"https://api.mollie.com\"), picture-in-picture=(), "
    "publickey-credentials-get=(self), screen-wake-lock=(), "
    "sync-xhr=(), usb=(), web-share=(), xr-spatial-tracking=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware adding OWASP security headers.

    Use via:
        app.add_middleware(SecurityHeadersMiddleware, csp=STRICT_CSP)

    Skips headers for paths matching `skip_paths` (e.g. health endpoints).
    """

    def __init__(
        self,
        app,
        csp: str = DEFAULT_CSP,
        permissions_policy: str = DEFAULT_PERMISSIONS_POLICY,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_preload: bool = True,
        skip_paths: tuple = ("/health",),
    ) -> None:
        super().__init__(app)
        self.csp = csp
        self.permissions_policy = permissions_policy
        hsts_parts = [f"max-age={hsts_max_age}", "includeSubDomains"]
        if hsts_preload:
            hsts_parts.append("preload")
        self.hsts = "; ".join(hsts_parts)
        self.skip_paths = skip_paths

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Skip noisy paths (health checks need to stay light)
        path = request.url.path
        if any(path.startswith(p) for p in self.skip_paths):
            return response

        # Core security headers
        response.headers.setdefault("Content-Security-Policy", self.csp)
        response.headers.setdefault("Strict-Transport-Security", self.hsts)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", self.permissions_policy)
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")

        # Remove leaky headers if framework added them
        # (MutableHeaders has no .pop() â€” use del with membership check)
        for leaky in ("Server", "X-Powered-By"):
            if leaky in response.headers:
                try:
                    del response.headers[leaky]
                except KeyError:
                    pass

        return response
