from __future__ import annotations

import os
import time
import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.ai_budget import AIBudgetExceeded, finalize_ai_call, reserve_ai_call


class PremiumSourceError(RuntimeError):
    """Raised when a premium source call fails before usable data is returned."""


@dataclass
class PremiumSourceResult:
    provider: str
    status: str
    configured: bool
    elapsed_ms: int
    data: dict[str, Any] | None = None
    error: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)


HANDELSREGISTER_BASE_URL = "https://handelsregister.ai/api/v1"
HANDELSREGISTER_DEFAULT_DETAIL_FEATURES = (
    "financial_kpi",
    "related_persons",
    "publications",
    "insolvency_publications",
    "shareholders",
    "ubos",
    "shareholdings",
)
HANDELSREGISTER_ALLOWED_FEATURES = HANDELSREGISTER_DEFAULT_DETAIL_FEATURES + (
    "balance_sheet_accounts",
    "profit_and_loss_account",
    "annual_financial_statements",
    "annual_financial_statements__html",
    "news",
    "website_content",
)
HANDELSREGISTER_DOCUMENT_TYPES = {
    "shareholders_list",
    "articles_of_association",
    "AD",
    "CD",
    "SI",
}
GENERIC_COMPANY_AUTH_HEADER_DEFAULT = "Authorization"


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return default
    if value.strip().lower() in {"", "none", "off", "false"}:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _bounded_int(value: int, *, minimum: int = 1, maximum: int = 10) -> int:
    return max(minimum, min(int(value), maximum))


def _handelsregister_auth_headers() -> dict[str, str]:
    bearer = os.getenv("HANDELSREGISTER_AI_BEARER_TOKEN")
    if bearer:
        return {"Authorization": f"Bearer {bearer}"}
    api_key = os.getenv("HANDELSREGISTER_AI_API_KEY")
    if api_key:
        return {"x-api-key": api_key}
    return {}


def _handelsregister_base_url() -> str:
    return os.getenv("HANDELSREGISTER_AI_BASE_URL", HANDELSREGISTER_BASE_URL).rstrip("/")


def _auth_header_from_env(
    key_name: str,
    *,
    header_name_env: str,
    default_header_name: str = GENERIC_COMPANY_AUTH_HEADER_DEFAULT,
) -> dict[str, str]:
    api_key = os.getenv(key_name)
    if not api_key:
        return {}
    header_name = os.getenv(header_name_env, default_header_name).strip() or default_header_name
    if header_name.lower() == "authorization":
        token_prefix = os.getenv(f"{key_name}_AUTH_PREFIX", "Bearer").strip()
        return {"Authorization": f"{token_prefix} {api_key}".strip()}
    return {header_name: api_key}


def configured_premium_sources() -> dict[str, bool]:
    return {
        "exa": bool(os.getenv("EXA_API_KEY")),
        "handelsregister_ai": bool(_handelsregister_auth_headers()),
        "firmenbuch_ai": bool(os.getenv("FIRMENBUCH_AI_API_KEY") and os.getenv("FIRMENBUCH_AI_SEARCH_URL")),
        "belgium_company_api": bool(os.getenv("BELGIUM_COMPANY_API_KEY") and os.getenv("BELGIUM_COMPANY_SEARCH_URL")),
        "luxembourg_rcs_api": bool(os.getenv("LUXEMBOURG_RCS_API_KEY") and os.getenv("LUXEMBOURG_RCS_SEARCH_URL")),
        "france_sirene_api": bool(os.getenv("FRANCE_SIRENE_API_KEY") and os.getenv("FRANCE_SIRENE_SEARCH_URL")),
    }


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        return default


def _safe_error(exc: Exception) -> str:
    # Avoid leaking provider payloads, keys, or auth headers into reports/logs.
    return f"{type(exc).__name__}: {str(exc)[:160]}"


def _country_key(value: str) -> str:
    normalized = (value or "").strip().lower()
    return (
        normalized.replace("Ã¶", "oe")
        .replace("Ã¤", "ae")
        .replace("Ã¼", "ue")
        .replace("ÃŸ", "ss")
    )


def _build_exa_payload(query: str, *, num_results: int = 5, include_text: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": query,
        "numResults": max(1, min(int(num_results), 10)),
        "type": "auto",
    }
    if include_text:
        payload["contents"] = {
            "text": True,
            "highlights": True,
        }
    return payload


def _build_handelsregister_params(
    query: str,
    *,
    limit: int = 5,
    skip: int = 0,
    filters: dict[str, Any] | None = None,
) -> dict[str, str]:
    params = {
        "q": query,
        "limit": str(_bounded_int(limit, maximum=30)),
    }
    if skip > 0:
        params["skip"] = str(skip)
    if filters:
        params["filters"] = json.dumps(filters, separators=(",", ":"))
    return params


def _build_handelsregister_fetch_params(
    query: str,
    *,
    features: tuple[str, ...] | list[str] | None = None,
    ai_search: bool = False,
    realtime_mode: bool = False,
) -> dict[str, Any]:
    clean_features = [
        feature
        for feature in (features or ())
        if feature in HANDELSREGISTER_ALLOWED_FEATURES
    ]
    params: dict[str, Any] = {"q": query}
    if clean_features:
        params["feature"] = clean_features
    if ai_search:
        params["ai_search"] = "on-default"
    if realtime_mode:
        params["realtime_mode"] = "handelsregister-default"
    return params


def _build_handelsregister_person_params(
    person_q: str,
    organization_q: str,
    *,
    features: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    clean_features = [
        feature
        for feature in (features or ())
        if feature == "shareholdings"
    ]
    params: dict[str, Any] = {
        "person_q": person_q,
        "organization_q": organization_q,
    }
    if clean_features:
        params["features"] = clean_features
    return params


def _build_firmenbuch_params(query: str, *, limit: int = 5) -> dict[str, str]:
    return {
        "q": query,
        "limit": str(_bounded_int(limit, maximum=10)),
    }


def _build_belgium_company_params(query: str, *, limit: int = 5) -> dict[str, str]:
    return {
        "q": query,
        "limit": str(_bounded_int(limit, maximum=10)),
    }


def _build_luxembourg_rcs_params(query: str, *, limit: int = 5) -> dict[str, str]:
    return {
        "q": query,
        "limit": str(_bounded_int(limit, maximum=10)),
    }


def _build_france_sirene_params(query: str, *, limit: int = 5) -> dict[str, str]:
    # INSEE SIRENE multicriteria search: `q` is the documented query param and
    # `nombre` caps the result count (max 1000 upstream; we keep it conservative).
    # Host/path comes from FRANCE_SIRENE_SEARCH_URL so a proxy/aggregator can be swapped in.
    return {
        "q": query,
        "nombre": str(_bounded_int(limit, maximum=10)),
    }


def _normalize_exa_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = []
    for item in data.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        snippet = item.get("text") or ""
        highlights = item.get("highlights")
        if not snippet and isinstance(highlights, list) and highlights:
            snippet = str(highlights[0])
        evidence.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or item.get("id") or "",
                "published_date": item.get("publishedDate") or "",
                "source": "Exa",
                "snippet": snippet[:600],
            }
        )
    return evidence


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return [value]
    return []


def _nested_items(value: Any, *keys: str) -> list[Any]:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return _as_list(current)


def _registration_label(registration: dict[str, Any]) -> str:
    register_type = registration.get("register_type") or registration.get("type") or ""
    register_number = registration.get("register_number") or registration.get("number") or ""
    if register_type and register_number:
        return f"{register_type} {register_number}"
    return str(register_number or registration.get("id") or "")


def _normalize_handelsregister_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = data.get("data") or data.get("results") or data.get("organizations") or []
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    evidence = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        registration = item.get("registration") or {}
        address = item.get("address") or {}
        evidence.append(
            {
                "evidence_type": "company_search_result",
                "entity_id": item.get("entity_id") or item.get("id") or "",
                "name": item.get("name") or item.get("company_name") or item.get("organization_name") or "",
                "register_number": (
                    item.get("register_number")
                    or item.get("registration_number")
                    or _registration_label(registration)
                    or item.get("id")
                    or ""
                ),
                "court": item.get("register_court") or item.get("court") or registration.get("court") or "",
                "city": item.get("city") or address.get("city") or "",
                "status": item.get("status") or "",
                "source": "Handelsregister.ai",
            }
        )
    return evidence


def _normalize_handelsregister_detail_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return evidence

    registration = data.get("registration") or {}
    address = data.get("address") or {}
    company_name = data.get("name") or data.get("company_name") or ""
    register_number = _registration_label(registration)
    evidence.append(
        {
            "evidence_type": "company_profile",
            "entity_id": data.get("entity_id") or "",
            "name": company_name,
            "register_number": register_number,
            "court": registration.get("court") or "",
            "legal_form": data.get("legal_form") or "",
            "status": data.get("status") or "",
            "city": address.get("city") or "",
            "source": "Handelsregister.ai",
        }
    )

    related_persons = data.get("related_persons") or {}
    for bucket in ("current", "former"):
        for person in _nested_items(related_persons, bucket):
            if not isinstance(person, dict):
                continue
            role = person.get("role") or {}
            role_label = role.get("de", {}).get("long") if isinstance(role.get("de"), dict) else role.get("de")
            evidence.append(
                {
                    "evidence_type": f"related_person_{bucket}",
                    "name": person.get("name") or "",
                    "role": role_label or person.get("label") or "",
                    "start_date": person.get("start_date") or "",
                    "end_date": person.get("end_date") or "",
                    "source": "Handelsregister.ai",
                }
            )

    for item in _as_list(data.get("financial_kpi"))[:3]:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "evidence_type": "financial_kpi",
                "name": company_name,
                "year": item.get("year") or "",
                "revenue": item.get("revenue"),
                "net_income": item.get("net_income"),
                "employees": item.get("employees"),
                "source": "Handelsregister.ai",
            }
        )

    for item in _as_list(data.get("publications"))[:5]:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "evidence_type": "publication",
                "title": item.get("title") or item.get("event") or item.get("type") or "Register publication",
                "published_date": item.get("publication_date") or item.get("date") or "",
                "source": "Handelsregister.ai",
            }
        )

    for item in _as_list(data.get("insolvency_publications"))[:5]:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "evidence_type": "insolvency_publication",
                "title": item.get("title") or item.get("event") or "Insolvency publication",
                "published_date": item.get("publication_date") or item.get("date") or "",
                "case_number": item.get("case_number") or item.get("file_number") or "",
                "source": "Handelsregister.ai",
            }
        )

    for item in _as_list(data.get("shareholders"))[:10]:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "evidence_type": "shareholder",
                "name": item.get("name") or item.get("shareholder_name") or "",
                "percentage": item.get("percentage") or item.get("ownership_percentage"),
                "source": "Handelsregister.ai",
            }
        )

    for item in _as_list(data.get("ubos"))[:10]:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "evidence_type": "ubo",
                "name": item.get("name") or item.get("ubo_name") or "",
                "percentage": item.get("percentage") or item.get("ownership_percentage"),
                "source": "Handelsregister.ai",
            }
        )

    shareholdings = data.get("shareholdings") or {}
    holdings = _nested_items(shareholdings, "holdings", "current") or _as_list(shareholdings)
    for item in holdings[:10]:
        if not isinstance(item, dict):
            continue
        organization = item.get("organization") or {}
        ownership = item.get("ownership") or {}
        evidence.append(
            {
                "evidence_type": "shareholding",
                "name": organization.get("name") or item.get("name") or "",
                "percentage": ownership.get("percentage") or item.get("percentage"),
                "as_of": item.get("as_of") or "",
                "source": "Handelsregister.ai",
            }
        )

    return evidence


def _normalize_handelsregister_person_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return evidence
    evidence.append(
        {
            "evidence_type": "person_profile",
            "entity_id": data.get("entity_id") or "",
            "name": data.get("name") or "",
            "source": "Handelsregister.ai",
        }
    )
    for role in _as_list(data.get("handelsregister_roles")):
        if not isinstance(role, dict):
            continue
        organization = role.get("organization") or {}
        evidence.append(
            {
                "evidence_type": "person_register_role",
                "name": data.get("name") or "",
                "organization": organization.get("name") if isinstance(organization, dict) else role.get("organization"),
                "role": role.get("label") or role.get("relation") or "",
                "start_date": role.get("start_date") or "",
                "end_date": role.get("end_date") or "",
                "source": "Handelsregister.ai",
            }
        )
    return evidence


def _normalize_firmenbuch_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = (
        data.get("data")
        or data.get("results")
        or data.get("companies")
        or data.get("organizations")
        or data.get("items")
        or []
    )
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    evidence = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "name": item.get("name") or item.get("company_name") or item.get("firma") or "",
                "register_number": (
                    item.get("fnr")
                    or item.get("firmenbuchnummer")
                    or item.get("register_number")
                    or item.get("registration_number")
                    or item.get("id")
                    or ""
                ),
                "legal_form": item.get("legal_form") or item.get("rechtsform") or "",
                "city": item.get("city") or item.get("ort") or item.get("location") or "",
                "status": item.get("status") or "",
                "source": "Firmenbuch.ai",
            }
        )
    return evidence


def _normalize_belgium_company_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = (
        data.get("data")
        or data.get("results")
        or data.get("companies")
        or data.get("enterprises")
        or data.get("items")
        or []
    )
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    evidence = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        address = item.get("address") or item.get("registered_office") or {}
        evidence.append(
            {
                "evidence_type": "company_search_result",
                "name": item.get("name") or item.get("denomination") or item.get("enterprise_name") or "",
                "register_number": (
                    item.get("enterprise_number")
                    or item.get("kbo_number")
                    or item.get("bce_number")
                    or item.get("vat_number")
                    or item.get("id")
                    or ""
                ),
                "legal_form": item.get("legal_form") or item.get("juridical_form") or "",
                "status": item.get("status") or "",
                "city": item.get("city") or address.get("city") or "",
                "source": "Belgium KBO/BCE API",
            }
        )
    return evidence


def _normalize_luxembourg_rcs_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = (
        data.get("data")
        or data.get("results")
        or data.get("companies")
        or data.get("entities")
        or data.get("items")
        or []
    )
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    evidence = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        address = item.get("address") or item.get("registered_office") or {}
        evidence.append(
            {
                "evidence_type": "company_search_result",
                "name": item.get("name") or item.get("company_name") or item.get("denomination") or "",
                "register_number": (
                    item.get("rcs_number")
                    or item.get("registration_number")
                    or item.get("matricule")
                    or item.get("id")
                    or ""
                ),
                "legal_form": item.get("legal_form") or item.get("form") or "",
                "status": item.get("status") or "",
                "city": item.get("city") or address.get("city") or "",
                "source": "Luxembourg RCS/LBR API",
            }
        )
    return evidence


def _normalize_france_sirene_evidence(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = (
        data.get("etablissements")
        or data.get("unitesLegales")
        or data.get("data")
        or data.get("results")
        or data.get("companies")
        or data.get("items")
        or []
    )
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    evidence = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        unite = item.get("uniteLegale") if isinstance(item.get("uniteLegale"), dict) else {}
        address = item.get("adresseEtablissement") or item.get("address") or {}
        if not isinstance(address, dict):
            address = {}
        evidence.append(
            {
                "evidence_type": "company_search_result",
                "name": (
                    item.get("name")
                    or item.get("denomination")
                    or unite.get("denominationUniteLegale")
                    or item.get("denominationUniteLegale")
                    or ""
                ),
                "register_number": (
                    item.get("siren")
                    or item.get("siret")
                    or unite.get("siren")
                    or item.get("registration_number")
                    or item.get("id")
                    or ""
                ),
                "legal_form": (
                    item.get("legal_form")
                    or unite.get("categorieJuridiqueUniteLegale")
                    or item.get("categorieJuridiqueUniteLegale")
                    or ""
                ),
                "status": (
                    item.get("status")
                    or unite.get("etatAdministratifUniteLegale")
                    or item.get("etatAdministratifUniteLegale")
                    or ""
                ),
                "city": (
                    item.get("city")
                    or address.get("libelleCommuneEtablissement")
                    or address.get("city")
                    or ""
                ),
                "source": "France SIRENE (INSEE)",
            }
        )
    return evidence


async def exa_search(
    query: str,
    *,
    num_results: int = 5,
    include_text: bool = True,
    timeout_s: float = 20.0,
) -> PremiumSourceResult:
    api_key = os.getenv("EXA_API_KEY")
    started = time.perf_counter()
    if not api_key:
        return PremiumSourceResult("exa", "missing_key", False, 0, error="EXA_API_KEY missing")

    estimated_cost = _env_float("DUESIGHT_EXA_SEARCH_CALL_EUR", 0.007)
    reservation = None
    try:
        reservation = reserve_ai_call(
            "exa",
            model="search",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(
                "https://api.exa.ai/search",
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                json=_build_exa_payload(query, num_results=num_results, include_text=include_text),
            )
            response.raise_for_status()
            data = response.json()
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "exa",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data=data,
            evidence=_normalize_exa_evidence(data),
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult("exa", "budget_blocked", True, int((time.perf_counter() - started) * 1000), error=str(exc))
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult("exa", "error", True, int((time.perf_counter() - started) * 1000), error=_safe_error(exc))


async def handelsregister_ai_search(
    query: str,
    *,
    limit: int = 5,
    timeout_s: float = 20.0,
) -> PremiumSourceResult:
    auth_headers = _handelsregister_auth_headers()
    started = time.perf_counter()
    if not auth_headers:
        return PremiumSourceResult("handelsregister_ai", "missing_key", False, 0, error="HANDELSREGISTER_AI_API_KEY missing")

    estimated_cost = _env_float("DUESIGHT_HANDELSREGISTER_AI_SEARCH_CALL_EUR", 0.05)
    reservation = None
    try:
        reservation = reserve_ai_call(
            "handelsregister_ai",
            model="search-organizations",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(
                f"{_handelsregister_base_url()}/search-organizations",
                headers={**auth_headers, "Accept": "application/json"},
                params=_build_handelsregister_params(query, limit=limit),
            )
            response.raise_for_status()
            data = response.json()
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "handelsregister_ai",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data=data,
            evidence=_normalize_handelsregister_evidence(data),
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult(
            "handelsregister_ai",
            "budget_blocked",
            True,
            int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult(
            "handelsregister_ai",
            "error",
            True,
            int((time.perf_counter() - started) * 1000),
            error=_safe_error(exc),
        )


async def handelsregister_ai_fetch_organization(
    query: str,
    *,
    features: tuple[str, ...] | list[str] | None = None,
    ai_search: bool = False,
    realtime_mode: bool = False,
    timeout_s: float = 25.0,
) -> PremiumSourceResult:
    auth_headers = _handelsregister_auth_headers()
    started = time.perf_counter()
    if not auth_headers:
        return PremiumSourceResult("handelsregister_ai", "missing_key", False, 0, error="HANDELSREGISTER_AI_API_KEY missing")

    selected_features = tuple(features) if features is not None else _csv_env(
        "DUESIGHT_HANDELSREGISTER_AI_DETAIL_FEATURES",
        HANDELSREGISTER_DEFAULT_DETAIL_FEATURES,
    )
    estimated_cost = _env_float("DUESIGHT_HANDELSREGISTER_AI_DETAIL_CALL_EUR", 0.25)
    reservation = None
    try:
        reservation = reserve_ai_call(
            "handelsregister_ai",
            model="fetch-organization",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(
                f"{_handelsregister_base_url()}/fetch-organization",
                headers={**auth_headers, "Accept": "application/json"},
                params=_build_handelsregister_fetch_params(
                    query,
                    features=selected_features,
                    ai_search=ai_search,
                    realtime_mode=realtime_mode,
                ),
            )
            response.raise_for_status()
            data = response.json()
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "handelsregister_ai",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data=data,
            evidence=_normalize_handelsregister_detail_evidence(data),
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult(
            "handelsregister_ai",
            "budget_blocked",
            True,
            int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult(
            "handelsregister_ai",
            "error",
            True,
            int((time.perf_counter() - started) * 1000),
            error=_safe_error(exc),
        )


async def handelsregister_ai_fetch_person(
    person_q: str,
    organization_q: str,
    *,
    features: tuple[str, ...] | list[str] | None = None,
    timeout_s: float = 25.0,
) -> PremiumSourceResult:
    auth_headers = _handelsregister_auth_headers()
    started = time.perf_counter()
    if not auth_headers:
        return PremiumSourceResult("handelsregister_ai", "missing_key", False, 0, error="HANDELSREGISTER_AI_API_KEY missing")

    estimated_cost = _env_float("DUESIGHT_HANDELSREGISTER_AI_PERSON_CALL_EUR", 0.30)
    reservation = None
    try:
        reservation = reserve_ai_call(
            "handelsregister_ai",
            model="fetch-person",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(
                f"{_handelsregister_base_url()}/fetch-person",
                headers={**auth_headers, "Accept": "application/json"},
                params=_build_handelsregister_person_params(
                    person_q,
                    organization_q,
                    features=features,
                ),
            )
            response.raise_for_status()
            data = response.json()
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "handelsregister_ai",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data=data,
            evidence=_normalize_handelsregister_person_evidence(data),
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult(
            "handelsregister_ai",
            "budget_blocked",
            True,
            int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult(
            "handelsregister_ai",
            "error",
            True,
            int((time.perf_counter() - started) * 1000),
            error=_safe_error(exc),
        )


async def handelsregister_ai_fetch_document(
    company_id: str,
    document_type: str,
    *,
    timeout_s: float = 30.0,
) -> PremiumSourceResult:
    auth_headers = _handelsregister_auth_headers()
    started = time.perf_counter()
    if not auth_headers:
        return PremiumSourceResult("handelsregister_ai", "missing_key", False, 0, error="HANDELSREGISTER_AI_API_KEY missing")
    if document_type not in HANDELSREGISTER_DOCUMENT_TYPES:
        return PremiumSourceResult("handelsregister_ai", "invalid_document_type", True, 0, error="Unsupported document type")

    estimated_cost = _env_float("DUESIGHT_HANDELSREGISTER_AI_DOCUMENT_CALL_EUR", 0.10)
    reservation = None
    try:
        reservation = reserve_ai_call(
            "handelsregister_ai",
            model="fetch-document",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(
                f"{_handelsregister_base_url()}/fetch-document",
                headers={**auth_headers, "Accept": "application/pdf, application/xml, application/json"},
                params={"company_id": company_id, "document_type": document_type},
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            payload = response.content
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "handelsregister_ai",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data={
                "company_id": company_id,
                "document_type": document_type,
                "content_type": content_type,
                "size_bytes": len(payload),
            },
            evidence=[
                {
                    "evidence_type": "register_document",
                    "identifier": company_id,
                    "document_type": document_type,
                    "source": "Handelsregister.ai",
                }
            ],
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult(
            "handelsregister_ai",
            "budget_blocked",
            True,
            int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult(
            "handelsregister_ai",
            "error",
            True,
            int((time.perf_counter() - started) * 1000),
            error=_safe_error(exc),
        )


async def firmenbuch_ai_search(
    query: str,
    *,
    limit: int = 5,
    timeout_s: float = 20.0,
) -> PremiumSourceResult:
    api_key = os.getenv("FIRMENBUCH_AI_API_KEY")
    search_url = os.getenv("FIRMENBUCH_AI_SEARCH_URL")
    started = time.perf_counter()
    if not api_key:
        return PremiumSourceResult("firmenbuch_ai", "missing_key", False, 0, error="FIRMENBUCH_AI_API_KEY missing")
    if not search_url:
        return PremiumSourceResult(
            "firmenbuch_ai",
            "missing_endpoint",
            False,
            0,
            error="FIRMENBUCH_AI_SEARCH_URL missing",
        )

    estimated_cost = _env_float("DUESIGHT_FIRMENBUCH_AI_SEARCH_CALL_EUR", 0.05)
    auth_header = os.getenv("FIRMENBUCH_AI_AUTH_HEADER", "x-api-key").strip() or "x-api-key"
    reservation = None
    try:
        reservation = reserve_ai_call(
            "firmenbuch_ai",
            model="search",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(
                search_url,
                headers={auth_header: api_key, "Accept": "application/json"},
                params=_build_firmenbuch_params(query, limit=limit),
            )
            response.raise_for_status()
            data = response.json()
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "firmenbuch_ai",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data=data,
            evidence=_normalize_firmenbuch_evidence(data),
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult(
            "firmenbuch_ai",
            "budget_blocked",
            True,
            int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult(
            "firmenbuch_ai",
            "error",
            True,
            int((time.perf_counter() - started) * 1000),
            error=_safe_error(exc),
        )


async def belgium_company_search(
    query: str,
    *,
    limit: int = 5,
    timeout_s: float = 20.0,
) -> PremiumSourceResult:
    auth_headers = _auth_header_from_env(
        "BELGIUM_COMPANY_API_KEY",
        header_name_env="BELGIUM_COMPANY_AUTH_HEADER",
    )
    search_url = os.getenv("BELGIUM_COMPANY_SEARCH_URL")
    started = time.perf_counter()
    if not auth_headers:
        return PremiumSourceResult("belgium_company_api", "missing_key", False, 0, error="BELGIUM_COMPANY_API_KEY missing")
    if not search_url:
        return PremiumSourceResult(
            "belgium_company_api",
            "missing_endpoint",
            False,
            0,
            error="BELGIUM_COMPANY_SEARCH_URL missing",
        )

    estimated_cost = _env_float("DUESIGHT_BELGIUM_COMPANY_SEARCH_CALL_EUR", 0.03)
    reservation = None
    try:
        reservation = reserve_ai_call(
            "belgium_company_api",
            model="company-search",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(
                search_url,
                headers={**auth_headers, "Accept": "application/json"},
                params=_build_belgium_company_params(query, limit=limit),
            )
            response.raise_for_status()
            data = response.json()
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "belgium_company_api",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data=data,
            evidence=_normalize_belgium_company_evidence(data),
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult(
            "belgium_company_api",
            "budget_blocked",
            True,
            int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult(
            "belgium_company_api",
            "error",
            True,
            int((time.perf_counter() - started) * 1000),
            error=_safe_error(exc),
        )


async def luxembourg_rcs_search(
    query: str,
    *,
    limit: int = 5,
    timeout_s: float = 20.0,
) -> PremiumSourceResult:
    auth_headers = _auth_header_from_env(
        "LUXEMBOURG_RCS_API_KEY",
        header_name_env="LUXEMBOURG_RCS_AUTH_HEADER",
    )
    search_url = os.getenv("LUXEMBOURG_RCS_SEARCH_URL")
    started = time.perf_counter()
    if not auth_headers:
        return PremiumSourceResult("luxembourg_rcs_api", "missing_key", False, 0, error="LUXEMBOURG_RCS_API_KEY missing")
    if not search_url:
        return PremiumSourceResult(
            "luxembourg_rcs_api",
            "missing_endpoint",
            False,
            0,
            error="LUXEMBOURG_RCS_SEARCH_URL missing",
        )

    estimated_cost = _env_float("DUESIGHT_LUXEMBOURG_RCS_SEARCH_CALL_EUR", 0.05)
    reservation = None
    try:
        reservation = reserve_ai_call(
            "luxembourg_rcs_api",
            model="company-search",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(
                search_url,
                headers={**auth_headers, "Accept": "application/json"},
                params=_build_luxembourg_rcs_params(query, limit=limit),
            )
            response.raise_for_status()
            data = response.json()
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "luxembourg_rcs_api",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data=data,
            evidence=_normalize_luxembourg_rcs_evidence(data),
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult(
            "luxembourg_rcs_api",
            "budget_blocked",
            True,
            int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult(
            "luxembourg_rcs_api",
            "error",
            True,
            int((time.perf_counter() - started) * 1000),
            error=_safe_error(exc),
        )


async def france_sirene_search(
    query: str,
    *,
    limit: int = 5,
    timeout_s: float = 20.0,
) -> PremiumSourceResult:
    auth_headers = _auth_header_from_env(
        "FRANCE_SIRENE_API_KEY",
        header_name_env="FRANCE_SIRENE_AUTH_HEADER",
    )
    search_url = os.getenv("FRANCE_SIRENE_SEARCH_URL")
    started = time.perf_counter()
    if not auth_headers:
        return PremiumSourceResult("france_sirene_api", "missing_key", False, 0, error="FRANCE_SIRENE_API_KEY missing")
    if not search_url:
        return PremiumSourceResult(
            "france_sirene_api",
            "missing_endpoint",
            False,
            0,
            error="FRANCE_SIRENE_SEARCH_URL missing",
        )

    # INSEE SIRENE is an official open-data source (no per-call fee). Default cost is
    # 0.0 so the budget guard stays consistent without charging for a free source; it
    # can still be overridden if routed through a paid proxy/aggregator.
    estimated_cost = _env_float("DUESIGHT_FRANCE_SIRENE_SEARCH_CALL_EUR", 0.0)
    reservation = None
    try:
        reservation = reserve_ai_call(
            "france_sirene_api",
            model="company-search",
            estimated_cost_eur=estimated_cost,
            estimated_tokens=0,
        )
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(
                search_url,
                headers={**auth_headers, "Accept": "application/json"},
                params=_build_france_sirene_params(query, limit=limit),
            )
            response.raise_for_status()
            data = response.json()
        finalize_ai_call(reservation, actual_cost_eur=estimated_cost, actual_tokens=0)
        reservation = None
        return PremiumSourceResult(
            "france_sirene_api",
            "ok",
            True,
            int((time.perf_counter() - started) * 1000),
            data=data,
            evidence=_normalize_france_sirene_evidence(data),
        )
    except AIBudgetExceeded as exc:
        return PremiumSourceResult(
            "france_sirene_api",
            "budget_blocked",
            True,
            int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
    except Exception as exc:
        finalize_ai_call(reservation, actual_cost_eur=0.0, actual_tokens=0)
        return PremiumSourceResult(
            "france_sirene_api",
            "error",
            True,
            int((time.perf_counter() - started) * 1000),
            error=_safe_error(exc),
        )


async def premium_budget_evidence(
    company_name: str,
    *,
    country_hint: str = "",
    domain: str = "",
) -> dict[str, Any]:
    """Additive premium evidence layer: only use these after cheap/local sources."""
    queries = []
    base_query = company_name.strip()
    if domain:
        base_query = f"{base_query} {domain}".strip()
    if base_query:
        queries.append(base_query)

    provider_results: list[PremiumSourceResult] = []
    country_key = _country_key(country_hint)
    if country_key in {"de", "deu", "germany", "duitsland", "dach"} and company_name.strip():
        provider_results.append(await handelsregister_ai_search(company_name, limit=5))
        if _env_flag("DUESIGHT_HANDELSREGISTER_AI_DETAIL_ENABLED", True):
            provider_results.append(
                await handelsregister_ai_fetch_organization(
                    company_name,
                    ai_search=_env_flag("DUESIGHT_HANDELSREGISTER_AI_AI_SEARCH", False),
                    realtime_mode=_env_flag("DUESIGHT_HANDELSREGISTER_AI_REALTIME", False),
                )
            )
    if country_key in {"at", "aut", "austria", "oostenrijk", "Ã¶sterreich", "osterreich", "dach"} and company_name.strip():
        provider_results.append(await firmenbuch_ai_search(company_name, limit=5))

    if country_key == "oesterreich" and company_name.strip():
        provider_results.append(await firmenbuch_ai_search(company_name, limit=5))
    if country_key in {"be", "bel", "belgium", "belgie", "belgique", "belgien", "benelux"} and company_name.strip():
        provider_results.append(await belgium_company_search(company_name, limit=5))
    if country_key in {"lu", "lux", "luxembourg", "luxemburg", "luxembourgish", "benelux"} and company_name.strip():
        provider_results.append(await luxembourg_rcs_search(company_name, limit=5))
    if country_key in {"fr", "fra", "france", "frankrijk", "frankreich"} and company_name.strip():
        provider_results.append(await france_sirene_search(company_name, limit=5))

    if queries:
        provider_results.append(
            await exa_search(
                f"{queries[0]} official ownership risk filings adverse media",
                num_results=5,
                include_text=True,
            )
        )

    return {
        "sources": configured_premium_sources(),
        "results": [result.__dict__ for result in provider_results],
        "evidence": [item for result in provider_results for item in result.evidence],
    }
