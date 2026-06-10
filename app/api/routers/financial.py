import json
from pathlib import Path
from fastapi import APIRouter, Query

from app.services.ddintel import call_ddintel

router = APIRouter()

# Local DuckDB paths
_ICIJ_DB = Path(__file__).parent.parent.parent.parent.parent / "Promptwatch_clone" / "gego" / "data" / "icij.duckdb"
if not _ICIJ_DB.exists():
    _ICIJ_DB = Path("C:/Users/arian/Promptwatch_clone/gego/data/icij.duckdb")

_CH_DB = Path(__file__).parent.parent.parent.parent.parent / "Promptwatch_clone" / "gego" / "data" / "ch_uk.duckdb"
if not _CH_DB.exists():
    _CH_DB = Path("C:/Users/arian/Promptwatch_clone/gego/data/ch_uk.duckdb")

_GLEIF_API = "https://api.gleif.org/api/v1"
_GLEIF_OFFSHORE = {
    "VG", "KY", "BM", "PA", "BS", "GG", "JE", "IM", "GI", "LI",
    "MC", "SC", "MU", "CW", "BZ", "WS", "MH", "CY", "MT", "SG", "HK",
}

@router.get("/proxy-analysis")
async def financial_proxy_scan_endpoint(company_name: str = Query(...)):
    result = await call_ddintel("financial_proxy_analysis", {"company_name": company_name})
    if "error" in result:
        return {"status": "error", "error": result["error"]}

    return {
        "status": "ok",
        "module": "financial",
        "revenue_estimate": result.get("estimated_revenue", ""),
        "fte_estimate": result.get("fte_count", result.get("estimated_fte", 0)),
        "sector": result.get("sector", result.get("sbi_description", "")),
        "confidence": result.get("confidence_score", result.get("confidence", 0)),
        "data_tier": result.get("data_tier", "proxy"),
        "risk_flags": result.get("risk_flags", []),
    }

@router.get("/icij-offshore")
async def icij_offshore_scan_endpoint(company_name: str = Query(...)):
    if not _ICIJ_DB.exists():
        return {
            "status": "unavailable",
            "module": "icij_offshore",
            "reason": "ICIJ database not found",
        }
    try:
        import duckdb
        from difflib import SequenceMatcher

        con = duckdb.connect(str(_ICIJ_DB), read_only=True)
        norm = company_name.strip().lower()
        for suffix in [" b.v.", " bv", " n.v.", " nv", " gmbh", " ag", " ltd", " limited", " inc", " holding", " holdings"]:
            if norm.endswith(suffix):
                norm = norm[:-len(suffix)].strip()
        search_term = f"%{norm}%"

        rows = con.execute("""
            SELECT node_id, name, jurisdiction_description,
                   country_codes, service_provider, sourceID
            FROM icij_entities
            WHERE LOWER(name) LIKE ?
            LIMIT 20
        """, [search_term]).fetchall()

        matches = []
        for row in rows:
            node_id, ename, jur, cc, sp, dataset = row
            if not ename:
                continue
            en = ename.strip().lower()
            for s in [" ltd", " limited", " inc", " corp"]:
                if en.endswith(s):
                    en = en[:-len(s)].strip()
            conf = SequenceMatcher(None, norm, en).ratio()
            if norm in en or en in norm:
                conf = max(conf, 0.95)
            if conf < 0.7:
                continue

            matches.append({
                "name": ename,
                "confidence": round(conf, 2),
                "jurisdiction": jur or "",
                "dataset": dataset or "",
                "service_provider": sp or "",
            })

        officer_rows = con.execute("""
            SELECT name, country_codes, sourceID
            FROM icij_officers
            WHERE LOWER(name) LIKE ?
            LIMIT 10
        """, [search_term]).fetchall()

        officer_matches = []
        for row in officer_rows:
            oname, cc, dataset = row
            if not oname:
                continue
            on = oname.strip().lower()
            conf = SequenceMatcher(None, norm, on).ratio()
            if norm in on or on in norm:
                conf = max(conf, 0.95)
            if conf < 0.7:
                continue
            officer_matches.append({
                "name": oname,
                "confidence": round(conf, 2),
                "country": cc or "",
                "dataset": dataset or "",
            })

        con.close()

        all_matches = matches + officer_matches
        if not all_matches:
            return {
                "status": "ok",
                "module": "icij_offshore",
                "total_matches": 0,
                "risk_score": 0,
                "risk_level": "CLEAN",
                "verdict": "âœ… Geen offshore verbindingen gevonden in ICIJ database",
                "matches": [],
            }

        max_conf = max(m["confidence"] for m in all_matches)
        risk_score = min(100, int(max_conf * 60) + min(20, len(all_matches) * 5) + 10)

        if risk_score >= 80:
            risk_level = "CRITICAL"
        elif risk_score >= 60:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        top = matches[0] if matches else officer_matches[0]
        verdict = f"ðŸš© {company_name} komt voor in de {top['dataset']} via offshore entiteit {top['name']}"
        if matches and matches[0].get("jurisdiction"):
            verdict += f" in {matches[0]['jurisdiction']}"

        return {
            "status": "ok",
            "module": "icij_offshore",
            "total_matches": len(all_matches),
            "entity_matches": len(matches),
            "officer_matches": len(officer_matches),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "verdict": verdict,
            "matches": (matches + officer_matches)[:5],
            "risk_flags": [verdict] if risk_level in ("CRITICAL", "HIGH") else [],
        }
    except Exception as e:
        return {"status": "error", "module": "icij_offshore", "error": str(e)}

@router.get("/companieshouse")
async def companieshouse_scan_endpoint(company_name: str = Query(...)):
    if not _CH_DB.exists():
        return {
            "status": "unavailable",
            "module": "uk_companies",
            "reason": "Companies House database not found",
        }
    try:
        import duckdb
        con = duckdb.connect(str(_CH_DB), read_only=True)
        norm = company_name.strip().lower()
        for suffix in [" b.v.", " bv", " n.v.", " nv", " gmbh", " ag"]:
            if norm.endswith(suffix):
                norm = norm[:-len(suffix)].strip()
        search_term = f"%{norm}%"

        results = con.execute("""
            SELECT "CompanyName", "CompanyNumber", "CompanyStatus",
                   "CompanyCategory", "CountryOfOrigin",
                   "RegAddress.AddressLine1", "RegAddress.PostCode",
                   "SICCode.SICText_1", "Accounts.AccountCategory",
                   "Accounts.LastMadeUpDate"
            FROM ch_companies
            WHERE LOWER("CompanyName") LIKE ?
            LIMIT 10
        """, [search_term]).fetchall()
        con.close()

        matches = []
        for r in results:
            name, num, status, cat, country, addr, postcode, sic, acc_cat, acc_date = r
            matches.append({
                "name": name, "number": num, "status": status or "", "type": cat or "",
                "country": country or "", "address": f"{addr or ''}, {postcode or ''}".strip(", "),
                "sic": sic or "", "accounts": acc_cat or "", "accounts_date": acc_date or "",
            })

        if not matches:
            return {
                "status": "ok", "module": "uk_companies",
                "total_matches": 0, "verdict": "Geen UK entiteiten gevonden", "matches": [],
            }

        active = [m for m in matches if m["status"] == "Active"]
        holding = [m for m in active if "holding" in m["name"].lower()]

        if holding:
            verdict = f"UK holding gevonden: {holding[0]['name']} ({holding[0]['number']})"
        elif active:
            verdict = f"{len(active)} actieve UK entiteiten gevonden"
        else:
            verdict = f"{len(matches)} UK entiteiten gevonden (geen actief)"

        return {
            "status": "ok", "module": "uk_companies",
            "total_matches": len(matches), "active_matches": len(active),
            "verdict": verdict, "matches": matches[:5],
        }
    except Exception as e:
        return {"status": "error", "module": "uk_companies", "error": str(e)}

import httpx

@router.get("/gleif")
async def gleif_scan_endpoint(company_name: str = Query(...)):
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{_GLEIF_API}/lei-records",
                params={"filter[fulltext]": company_name, "page[size]": 3},
                headers={"Accept": "application/vnd.api+json"},
            )
            if resp.status_code != 200:
                return {"status": "error", "module": "gleif_ownership", "error": f"GLEIF API: {resp.status_code}"}

            data = resp.json()
            items = data.get("data", [])
            if not items:
                return {"status": "ok", "module": "gleif_ownership", "total_matches": 0, "verdict": "Geen LEI registratie gevonden"}

            best = items[0]
            attrs = best.get("attributes", {})
            entity = attrs.get("entity", {})
            legal_addr = entity.get("legalAddress", {})
            lei = best.get("id", "")

            entity_info = {
                "lei": lei, "legal_name": entity.get("legalName", {}).get("name", ""),
                "country": legal_addr.get("country", ""), "city": legal_addr.get("city", ""),
                "status": entity.get("status", ""),
            }

            rels = best.get("relationships", {})
            direct_parent, ultimate_parent = None, None
            dp_url = rels.get("direct-parent", {}).get("links", {}).get("lei-record")
            if dp_url:
                dp_resp = await client.get(dp_url, headers={"Accept": "application/vnd.api+json"})
                if dp_resp.status_code == 200:
                    dp_data = dp_resp.json().get("data", {})
                    if dp_data:
                        dp_entity = dp_data.get("attributes", {}).get("entity", {})
                        dp_addr = dp_entity.get("legalAddress", {})
                        direct_parent = {
                            "lei": dp_data.get("id", ""), "name": dp_entity.get("legalName", {}).get("name", ""),
                            "country": dp_addr.get("country", ""),
                        }

            up_url = rels.get("ultimate-parent", {}).get("links", {}).get("lei-record")
            if up_url:
                up_resp = await client.get(up_url, headers={"Accept": "application/vnd.api+json"})
                if up_resp.status_code == 200:
                    up_data = up_resp.json().get("data", {})
                    if up_data:
                        up_entity = up_data.get("attributes", {}).get("entity", {})
                        up_addr = up_entity.get("legalAddress", {})
                        ultimate_parent = {
                            "lei": up_data.get("id", ""), "name": up_entity.get("legalName", {}).get("name", ""),
                            "country": up_addr.get("country", ""),
                        }

            parts = [f"LEI: {lei}"]
            offshore_flags = []
            if direct_parent:
                parts.append(f"Parent: {direct_parent['name']} ({direct_parent['country']})")
                if direct_parent["country"][:2] in _GLEIF_OFFSHORE:
                    offshore_flags.append(f"Parent in {direct_parent['country']}")
            if ultimate_parent and ultimate_parent.get("lei") != (direct_parent or {}).get("lei"):
                parts.append(f"Ultimate: {ultimate_parent['name']} ({ultimate_parent['country']})")
                if ultimate_parent["country"][:2] in _GLEIF_OFFSHORE:
                    offshore_flags.append(f"Ultimate parent in {ultimate_parent['country']}")

            return {
                "status": "ok", "module": "gleif_ownership", "total_matches": len(items),
                "entity": entity_info, "direct_parent": direct_parent, "ultimate_parent": ultimate_parent,
                "offshore_flags": offshore_flags, "offshore_risk": len(offshore_flags) > 0,
                "verdict": " | ".join(parts), "risk_flags": [f"ðŸš© Offshore eigenaar: {f}" for f in offshore_flags],
            }
    except Exception as e:
        return {"status": "error", "module": "gleif_ownership", "error": str(e)}
