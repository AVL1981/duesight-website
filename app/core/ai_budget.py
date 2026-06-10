from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from datetime import date


class AIBudgetExceeded(RuntimeError):
    """Raised before an AI call when the configured budget would be exceeded."""


@dataclass
class ProviderUsage:
    calls: int = 0
    tokens: int = 0
    cost_eur: float = 0.0


@dataclass
class BudgetState:
    day: str = field(default_factory=lambda: date.today().isoformat())
    total_calls: int = 0
    total_tokens: int = 0
    total_cost_eur: float = 0.0
    providers: dict[str, ProviderUsage] = field(default_factory=dict)


@dataclass(frozen=True)
class BudgetReservation:
    provider: str
    model: str
    estimated_cost_eur: float
    estimated_tokens: int
    units: int
    active: bool = True


_LOCK = threading.Lock()
_STATE = BudgetState()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return max(0, int(value))
    except ValueError:
        return default


def _provider_key(provider: str) -> str:
    return (provider or "unknown").strip().lower().replace(" ", "_")


def _rollover_if_needed() -> None:
    global _STATE
    today = date.today().isoformat()
    if _STATE.day != today:
        _STATE = BudgetState(day=today)


def is_ai_budget_enabled() -> bool:
    return _env_flag("DUESIGHT_AI_BUDGET_ENABLED", default=True)


def reserve_ai_call(
    provider: str,
    *,
    model: str = "",
    estimated_cost_eur: float = 0.0,
    estimated_tokens: int = 0,
    units: int = 1,
) -> BudgetReservation:
    """Reserve budget before an external AI call."""
    provider_key = _provider_key(provider)
    units = max(1, units)
    estimated_cost_eur = max(0.0, estimated_cost_eur)
    estimated_tokens = max(0, estimated_tokens)

    if not is_ai_budget_enabled():
        return BudgetReservation(
            provider=provider_key,
            model=model,
            estimated_cost_eur=estimated_cost_eur,
            estimated_tokens=estimated_tokens,
            units=units,
            active=False,
        )

    daily_call_limit = _env_int("DUESIGHT_AI_DAILY_CALL_LIMIT", 200)
    provider_call_limit = _env_int("DUESIGHT_AI_PROVIDER_DAILY_CALL_LIMIT", 80)
    daily_cost_limit = _env_float("DUESIGHT_AI_DAILY_EUR_LIMIT", 10.0)
    provider_cost_limit = _env_float("DUESIGHT_AI_PROVIDER_DAILY_EUR_LIMIT", 5.0)

    with _LOCK:
        _rollover_if_needed()
        usage = _STATE.providers.setdefault(provider_key, ProviderUsage())

        if daily_call_limit and _STATE.total_calls + units > daily_call_limit:
            raise AIBudgetExceeded("Daily AI call limit exceeded.")
        if provider_call_limit and usage.calls + units > provider_call_limit:
            raise AIBudgetExceeded(f"Daily AI call limit exceeded for provider {provider_key}.")
        if daily_cost_limit and _STATE.total_cost_eur + estimated_cost_eur > daily_cost_limit:
            raise AIBudgetExceeded("Daily AI cost limit exceeded.")
        if provider_cost_limit and usage.cost_eur + estimated_cost_eur > provider_cost_limit:
            raise AIBudgetExceeded(f"Daily AI cost limit exceeded for provider {provider_key}.")

        _STATE.total_calls += units
        _STATE.total_tokens += estimated_tokens
        _STATE.total_cost_eur += estimated_cost_eur
        usage.calls += units
        usage.tokens += estimated_tokens
        usage.cost_eur += estimated_cost_eur

    return BudgetReservation(
        provider=provider_key,
        model=model,
        estimated_cost_eur=estimated_cost_eur,
        estimated_tokens=estimated_tokens,
        units=units,
    )


def finalize_ai_call(
    reservation: BudgetReservation | None,
    *,
    actual_cost_eur: float | None = None,
    actual_tokens: int | None = None,
) -> None:
    if not reservation or not reservation.active:
        return

    actual_cost = reservation.estimated_cost_eur if actual_cost_eur is None else max(0.0, actual_cost_eur)
    actual_token_count = reservation.estimated_tokens if actual_tokens is None else max(0, actual_tokens)
    cost_delta = actual_cost - reservation.estimated_cost_eur
    token_delta = actual_token_count - reservation.estimated_tokens

    with _LOCK:
        _rollover_if_needed()
        usage = _STATE.providers.setdefault(reservation.provider, ProviderUsage())
        _STATE.total_cost_eur = max(0.0, _STATE.total_cost_eur + cost_delta)
        _STATE.total_tokens = max(0, _STATE.total_tokens + token_delta)
        usage.cost_eur = max(0.0, usage.cost_eur + cost_delta)
        usage.tokens = max(0, usage.tokens + token_delta)


def estimate_cost_eur(
    provider: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> float:
    prices = {
        "anthropic": (2.75, 13.80),
        "openai": (2.30, 9.20),
        "google": (0.32, 1.10),
        "gemini": (0.32, 1.10),
        "mistral": (1.85, 5.50),
        "groq": (0.55, 0.80),
        "sambanova": (0.30, 0.90),
    }
    in_price, out_price = prices.get(_provider_key(provider), (0.50, 1.50))
    return (max(0, input_tokens) * in_price + max(0, output_tokens) * out_price) / 1_000_000


def get_ai_budget_snapshot() -> dict:
    with _LOCK:
        _rollover_if_needed()
        return {
            "day": _STATE.day,
            "enabled": is_ai_budget_enabled(),
            "total_calls": _STATE.total_calls,
            "total_tokens": _STATE.total_tokens,
            "total_cost_eur": round(_STATE.total_cost_eur, 6),
            "providers": {
                name: {
                    "calls": usage.calls,
                    "tokens": usage.tokens,
                    "cost_eur": round(usage.cost_eur, 6),
                }
                for name, usage in sorted(_STATE.providers.items())
            },
        }


def reset_ai_budget_state() -> None:
    global _STATE
    with _LOCK:
        _STATE = BudgetState()
