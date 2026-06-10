from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _split_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _matches(path: str, exact: set[str], prefixes: set[str]) -> bool:
    if path in exact:
        return True
    return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _extract_key(request: Request) -> str:
    api_key = request.headers.get("x-api-key", "").strip()
    if api_key:
        return api_key
    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


@dataclass(frozen=True)
class ApiSecurityConfig:
    enabled: bool
    api_keys: set[str]
    admin_keys: set[str]
    public_rate_limit: int
    protected_rate_limit: int
    rate_window_seconds: int
    protected_prefixes: set[str]
    public_paths: set[str]
    public_prefixes: set[str]
    public_limited_paths: set[str]
    public_limited_prefixes: set[str]
    admin_paths: set[str]
    admin_prefixes: set[str]
    service_name: str


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, bucket: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        hits = self._hits[bucket]
        cutoff = now - window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


def _apply_security_headers(response):
    """Attach baseline browser hardening headers without changing API payloads."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if _env_bool("DUESIGHT_ENABLE_HSTS", False):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
    return response


def build_api_security_config(
    *,
    public_paths: Iterable[str] = (),
    public_prefixes: Iterable[str] = (),
    public_limited_paths: Iterable[str] = (),
    public_limited_prefixes: Iterable[str] = (),
    admin_paths: Iterable[str] = (),
    admin_prefixes: Iterable[str] = (),
    protected_prefixes: Iterable[str] = ("/api",),
    service_name: str = "duesight-api",
) -> ApiSecurityConfig:
    api_keys = _split_csv(os.getenv("DUESIGHT_API_KEYS"))
    admin_keys = _split_csv(os.getenv("DUESIGHT_ADMIN_API_KEYS"))
    all_api_keys = api_keys | admin_keys
    return ApiSecurityConfig(
        enabled=_env_bool("DUESIGHT_AUTH_ENABLED", True),
        api_keys=all_api_keys,
        admin_keys=admin_keys,
        public_rate_limit=_env_int("DUESIGHT_PUBLIC_RATE_LIMIT_PER_MINUTE", 30),
        protected_rate_limit=_env_int("DUESIGHT_PROTECTED_RATE_LIMIT_PER_MINUTE", 120),
        rate_window_seconds=_env_int("DUESIGHT_RATE_WINDOW_SECONDS", 60),
        protected_prefixes=set(protected_prefixes),
        public_paths=set(public_paths),
        public_prefixes=set(public_prefixes),
        public_limited_paths=set(public_limited_paths),
        public_limited_prefixes=set(public_limited_prefixes),
        admin_paths=set(admin_paths),
        admin_prefixes=set(admin_prefixes),
        service_name=service_name,
    )


def configure_api_security(app: FastAPI, **kwargs: object) -> ApiSecurityConfig:
    config = build_api_security_config(**kwargs)
    limiter = InMemoryRateLimiter()

    @app.middleware("http")
    async def duesight_api_security(request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path

        if request.method == "OPTIONS" or not config.enabled:
            return _apply_security_headers(await call_next(request))

        is_protected_area = any(
            path == prefix or path.startswith(prefix.rstrip("/") + "/")
            for prefix in config.protected_prefixes
        )
        if not is_protected_area:
            return _apply_security_headers(await call_next(request))

        is_admin = _matches(path, config.admin_paths, config.admin_prefixes)
        is_public = _matches(path, config.public_paths, config.public_prefixes)
        is_public_limited = _matches(path, config.public_limited_paths, config.public_limited_prefixes)

        if is_admin:
            api_key = _extract_key(request)
            if not config.admin_keys:
                return _apply_security_headers(JSONResponse({"detail": "Admin API access is not configured"}, status_code=503))
            if api_key not in config.admin_keys:
                return _apply_security_headers(JSONResponse({"detail": "Admin API key required"}, status_code=403))
            bucket = f"admin:{api_key}:{path}"
            if not limiter.allow(bucket, config.protected_rate_limit, config.rate_window_seconds):
                return _apply_security_headers(JSONResponse({"detail": "Rate limit exceeded"}, status_code=429))
            request.state.auth_role = "admin"
            response = await call_next(request)
            response.headers["X-DueSight-Auth"] = "admin"
            return _apply_security_headers(response)

        if is_public or is_public_limited:
            if is_public_limited:
                bucket = f"public:{_client_id(request)}:{path}"
                if not limiter.allow(bucket, config.public_rate_limit, config.rate_window_seconds):
                    return _apply_security_headers(JSONResponse({"detail": "Rate limit exceeded"}, status_code=429))
            request.state.auth_role = "public"
            response = await call_next(request)
            response.headers["X-DueSight-Auth"] = "public"
            return _apply_security_headers(response)

        api_key = _extract_key(request)
        if not config.api_keys:
            return _apply_security_headers(JSONResponse({"detail": "API access is not configured"}, status_code=503))
        if api_key not in config.api_keys:
            return _apply_security_headers(JSONResponse({"detail": "API key required"}, status_code=401))

        bucket = f"api:{api_key}:{path}"
        if not limiter.allow(bucket, config.protected_rate_limit, config.rate_window_seconds):
            return _apply_security_headers(JSONResponse({"detail": "Rate limit exceeded"}, status_code=429))

        request.state.auth_role = "api"
        response = await call_next(request)
        response.headers["X-DueSight-Auth"] = "api"
        return _apply_security_headers(response)

    return config
