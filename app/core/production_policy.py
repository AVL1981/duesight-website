from __future__ import annotations

import os


class ProductionPolicyError(RuntimeError):
    """Raised when a runtime route is not allowed in production."""


_PRODUCTION_ENV_NAMES = {"production", "prod", "live"}

_LOCAL_AI_MARKERS = (
    "ollama",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "local-ai",
    "local_ai",
)

_CLI_AUTH_MARKERS = (
    "codex",
    "claude_cli",
    "claude-code",
    "claude code",
    "antigravity",
    "gemini_cli",
    "opencode",
    "kilo",
    "hermes",
)

_FREE_FALLBACK_MARKERS = (
    "pollinations",
    ":free",
    "/free",
    "openrouter_minimax_free",
    "openrouter_glm_free",
    "openrouter_gptoss_free",
    "github/",
    "github_models",
    "nvidia/",
    "nvidia_nim",
    "nim_",
    "cerebras",
    "groq",
    "sambanova",
)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower().replace("\\", "/")


def _contains_any(value: str, markers: tuple[str, ...]) -> str | None:
    for marker in markers:
        if marker in value:
            return marker
    return None


def is_production_runtime() -> bool:
    return _normalize(os.getenv("DUESIGHT_ENV")) in _PRODUCTION_ENV_NAMES


def assert_ai_route_allowed(
    *,
    model_alias: str = "",
    target_model: str = "",
    provider: str = "",
    route: str = "",
) -> None:
    """Block non-production AI routes before any external call is attempted."""
    if not is_production_runtime():
        return

    material = " ".join(
        _normalize(part)
        for part in (model_alias, target_model, provider, route)
        if part
    )

    local_marker = _contains_any(material, _LOCAL_AI_MARKERS)
    if local_marker and not _env_flag("DUESIGHT_ALLOW_LOCAL_AI"):
        raise ProductionPolicyError(
            f"local AI route is disabled in production ({local_marker})."
        )

    cli_marker = _contains_any(material, _CLI_AUTH_MARKERS)
    if cli_marker and not _env_flag("DUESIGHT_ALLOW_CLI_AUTH"):
        raise ProductionPolicyError(
            f"CLI-auth AI route is disabled in production ({cli_marker})."
        )

    fallback_marker = _contains_any(material, _FREE_FALLBACK_MARKERS)
    if fallback_marker and not _env_flag("DUESIGHT_ALLOW_FREE_FALLBACKS"):
        raise ProductionPolicyError(
            f"free or developer-tier fallback route is disabled in production ({fallback_marker})."
        )
