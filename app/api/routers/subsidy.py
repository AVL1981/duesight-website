import json
import logging
from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()

SUBSIDY_RULES_PATH = Path(__file__).parent.parent.parent.parent / "subsidy_rules_2026.json"

def _load_subsidy_rules() -> dict:
    try:
        if not SUBSIDY_RULES_PATH.exists():
            return {}
        with open(SUBSIDY_RULES_PATH, "r", encoding="utf-8") as f:
            rules = json.load(f)
        return {k: v for k, v in rules.items() if not k.startswith("_")}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning(f"Could not load subsidy rules: {e}")
        return {}

SUBSIDY_RULES = _load_subsidy_rules()

def filter_subsidies(
    sbi_code: str = "",
    fte_count: int = 0,
    legal_form: str = "",
    has_payroll: bool = True,
    annual_revenue: float = 0,
    tech_keywords: list[str] | None = None,
) -> list[dict]:
    matches = []
    tech_kw = [kw.lower() for kw in (tech_keywords or [])]

    for name, rule in SUBSIDY_RULES.items():
        hard = rule.get("hard_criteria", {})
        passed = True
        reasons_fail: list[str] = []

        max_fte = hard.get("max_fte")
        if max_fte is not None and fte_count > max_fte:
            passed = False
            reasons_fail.append(f"FTE ({fte_count}) > maximum ({max_fte})")

        if hard.get("requires_payroll") and not has_payroll:
            passed = False
            reasons_fail.append("Geen loonbelasting afdracht")

        if hard.get("requires_mkb_status"):
            if fte_count > 250:
                passed = False
                reasons_fail.append(f"Geen MKB-status (FTE {fte_count} > 250)")
            if annual_revenue > 50000000:
                passed = False
                reasons_fail.append("Omzet > â‚¬50M (geen MKB)")

        if not passed:
            continue

        tech_signals = rule.get("tech_stack_signals", [])
        tech_match_count = sum(
            1 for sig in tech_signals if any(sig.lower() in kw for kw in tech_kw)
        )
        tech_boost = min(tech_match_count * 10, 30)

        matches.append({
            "regeling": name,
            "voluit": rule.get("voluit", name),
            "type": rule.get("type", "onbekend"),
            "budget_label": rule.get("budget_label", ""),
            "benefits": rule.get("benefits", {}),
            "confidence": "HOOG" if tech_boost > 20 else "MIDDEL",
            "tech_stack_match": tech_boost > 0,
            "questionnaire_needed": rule.get("questionnaire_questions", []),
            "lead_partner_type": rule.get("lead_partner_type", ""),
            "application_periods": rule.get("application_periods_2026", []),
        })

    return matches


@router.post("/questionnaire")
async def subsidy_questionnaire(
    company_name: str = Query("", description="Company name"),
    sbi_code: str = Query("", description="SBI code from KvK"),
    fte_count: int = Query(0, description="Number of employees"),
    legal_form: str = Query("BV", description="Legal form"),
    answers: str = Query("{}", description="JSON string of questionnaire answers"),
) -> JSONResponse:
    try:
        user_answers = json.loads(answers) if isinstance(answers, str) else answers
    except json.JSONDecodeError:
        user_answers = {}

    matched = filter_subsidies(sbi_code=sbi_code, fte_count=fte_count, legal_form=legal_form)

    enriched = []
    for subsidy in matched:
        questions = subsidy.pop("questionnaire_needed", [])
        answered_count = 0
        positive_count = 0

        for q in questions:
            qid = q.get("id", "")
            if qid in user_answers:
                answered_count += 1
                if user_answers[qid]:
                    positive_count += 1

        if answered_count > 0 and positive_count == answered_count:
            subsidy["confidence"] = "HOOG"
            subsidy["user_confirmed"] = True
        elif answered_count > 0 and positive_count > 0:
            subsidy["confidence"] = "MIDDEL"
            subsidy["user_confirmed"] = "partial"
        elif answered_count > 0 and positive_count == 0:
            subsidy["confidence"] = "LAAG"
            subsidy["user_confirmed"] = False

        subsidy["questions_answered"] = answered_count
        subsidy["questions_positive"] = positive_count
        enriched.append(subsidy)

    confidence_order = {"HOOG": 0, "MIDDEL": 1, "LAAG": 2}
    enriched.sort(key=lambda x: confidence_order.get(x.get("confidence", ""), 99))

    return JSONResponse(content={
        "status": "ok",
        "company": company_name,
        "total_matched": len(enriched),
        "subsidies": enriched,
        "prompt_context": _build_subsidy_prompt_context(enriched, company_name),
    })


def _build_subsidy_prompt_context(subsidies: list[dict], company_name: str) -> str:
    if not subsidies:
        return (
            f"Subsidie Pre-Kwalificatie voor {company_name}: "
            "Op basis van de harde criteria komt dit bedrijf momenteel niet in aanmerking."
        )

    lines = [
        f"## Subsidie Pre-Kwalificatie â€” {company_name}",
        f"Er zijn {len(subsidies)} regelingen geÃ¯dentificeerd:\n",
    ]
    for s in subsidies:
        emoji = "ðŸŸ¢" if s["confidence"] == "HOOG" else "ðŸŸ¡" if s["confidence"] == "MIDDEL" else "ðŸ”´"
        lines.append(f"{emoji} **{s['voluit']}** ({s['type']})")
        lines.append(f"   Budget: {s['budget_label']} | Kans: {s['confidence']}")

    return "\n".join(lines)
