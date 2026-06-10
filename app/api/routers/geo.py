import json
import httpx
from fastapi import APIRouter, Query
from starlette.responses import StreamingResponse

from app.services.ddintel import call_ddintel

router = APIRouter()

_AI_CRAWLERS = [
    {"name": "GPTBot", "owner": "OpenAI", "impact": "ChatGPT citations"},
    {"name": "ChatGPT-User", "owner": "OpenAI", "impact": "ChatGPT live browse"},
    {"name": "ClaudeBot", "owner": "Anthropic", "impact": "Claude citations"},
    {"name": "PerplexityBot", "owner": "Perplexity", "impact": "Perplexity AI search"},
    {"name": "Google-Extended", "owner": "Google", "impact": "Gemini/AI Overviews"},
    {"name": "Applebot-Extended", "owner": "Apple", "impact": "Apple Intelligence"},
    {"name": "Amazonbot", "owner": "Amazon", "impact": "Alexa/Amazon AI"},
    {"name": "anthropic-ai", "owner": "Anthropic", "impact": "Claude training"},
    {"name": "CCBot", "owner": "Common Crawl", "impact": "Foundation model training"},
    {"name": "FacebookBot", "owner": "Meta", "impact": "Meta AI"},
    {"name": "cohere-ai", "owner": "Cohere", "impact": "Enterprise LLM"},
    {"name": "Bytespider", "owner": "ByteDance", "impact": "TikTok AI"},
    {"name": "Diffbot", "owner": "Diffbot", "impact": "Knowledge graph"},
    {"name": "YouBot", "owner": "You.com", "impact": "You.com AI search"},
]

async def check_robots_ai_blockers(domain: str) -> dict:
    blocked = []
    allowed = []
    has_robots = False
    robots_content = ""

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for scheme in ["https", "http"]:
            try:
                resp = await client.get(f"{scheme}://{domain}/robots.txt")
                if resp.status_code == 200 and "user-agent" in resp.text.lower():
                    robots_content = resp.text
                    has_robots = True
                    break
            except Exception:
                continue

    if not has_robots:
        return {
            "status": "ok", "module": "geo_robots", "has_robots_txt": False,
            "blocked": [], "allowed": [c["name"] for c in _AI_CRAWLERS],
            "total_blocked": 0, "total_crawlers": len(_AI_CRAWLERS),
            "risk_level": "LAAG", "dd_verdict": "Geen robots.txt â€” AI-crawlers hebben volledige toegang.",
        }

    lines = robots_content.split("\n")
    current_agents = []

    for line in lines:
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if line.lower().startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            current_agents = [agent]
        elif line.lower().startswith("disallow:") and current_agents:
            path = line.split(":", 1)[1].strip()
            if path == "/" or path == "/*":
                for crawler in _AI_CRAWLERS:
                    agent_lower = current_agents[0].lower()
                    crawler_lower = crawler["name"].lower()
                    if agent_lower == crawler_lower or agent_lower == "*":
                        if crawler["name"] not in [b["name"] for b in blocked]:
                            blocked.append(crawler)

    blocked_names = {b["name"] for b in blocked}
    for crawler in _AI_CRAWLERS:
        if crawler["name"] not in blocked_names:
            allowed.append(crawler["name"])

    wildcard_block = False
    current_agent_name = ""
    for line in lines:
        line = line.strip()
        if line.lower().startswith("user-agent:"):
            current_agent_name = line.split(":", 1)[1].strip()
        elif line.lower().startswith("disallow:") and current_agent_name == "*":
            path = line.split(":", 1)[1].strip()
            if path == "/" or path == "/*":
                wildcard_block = True

    if wildcard_block:
        explicitly_allowed = set()
        current_agent_name = ""
        for line in lines:
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                current_agent_name = line.split(":", 1)[1].strip()
            elif line.lower().startswith("allow:") and current_agent_name != "*":
                for crawler in _AI_CRAWLERS:
                    if current_agent_name.lower() == crawler["name"].lower():
                        explicitly_allowed.add(crawler["name"])

        for crawler in _AI_CRAWLERS:
            if crawler["name"] not in blocked_names and crawler["name"] not in explicitly_allowed:
                blocked.append(crawler)
                blocked_names.add(crawler["name"])

        allowed = [c["name"] for c in _AI_CRAWLERS if c["name"] not in blocked_names]

    total_blocked = len(blocked)
    if total_blocked >= 10:
        risk_level = "KRITIEK"
        dd_verdict = f"ðŸš¨ GEO Risico: KRITIEK. Doelwit blokkeert {total_blocked} van {len(_AI_CRAWLERS)} AI-crawlers. De digitale infrastructuur is niet voorbereid op Gen-AI zoekverkeer."
    elif total_blocked >= 5:
        risk_level = "HOOG"
        dd_verdict = f"âš ï¸ GEO Risico: HOOG. {total_blocked} AI-crawlers geblokkeerd."
    elif total_blocked >= 1:
        risk_level = "MIDDEL"
        dd_verdict = f"ðŸŸ¡ GEO Risico: MIDDEL. {total_blocked} AI-crawler(s) geblokkeerd."
    else:
        risk_level = "LAAG"
        dd_verdict = "âœ… Geen AI-crawlers geblokkeerd. Domein is toegankelijk voor Gen-AI platformen."

    return {
        "status": "ok", "module": "geo_robots", "has_robots_txt": True,
        "blocked": [{"name": b["name"], "owner": b["owner"], "impact": b["impact"]} for b in blocked],
        "allowed": allowed, "total_blocked": total_blocked, "total_crawlers": len(_AI_CRAWLERS),
        "risk_level": risk_level, "dd_verdict": dd_verdict,
    }


async def check_llms_txt(domain: str) -> dict:
    paths_to_check = [
        f"https://{domain}/llms.txt",
        f"https://{domain}/.well-known/llms.txt",
        f"https://{domain}/llms-full.txt",
    ]

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for url in paths_to_check:
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.text.strip()) > 10:
                    content = resp.text.strip()
                    if "<html" in content.lower() or "<head" in content.lower():
                        continue
                    return {
                        "status": "ok", "module": "geo_llmstxt", "exists": True, "url": url,
                        "content_preview": content[:500], "content_length": len(content),
                        "risk_level": "LAAG", "dd_verdict": "âœ… llms.txt aanwezig.",
                    }
            except Exception:
                continue

    return {
        "status": "ok", "module": "geo_llmstxt", "exists": False, "url": None,
        "content_preview": None, "content_length": 0, "risk_level": "MIDDEL",
        "dd_verdict": "ðŸŸ¡ Geen llms.txt gedetecteerd. De nieuwe standaard voor AI-leesbaarheid (2025) is niet geÃ¯mplementeerd.",
    }


async def check_ai_citations(company_name: str, domain: str, sector: str = "") -> dict:
    result = await call_ddintel("check_llm_citations", {
        "company_name": company_name, "sector": sector,
    })

    if "error" in result:
        return {"status": "error", "module": "geo_citations", "error": result["error"]}

    visibility_score = result.get("visibility_score", 0)
    mentioned_in = result.get("mentioned_in", [])
    total_queries = result.get("total_queries", 0)
    mention_count = result.get("mention_count", 0)

    if visibility_score >= 70:
        risk_level = "LAAG"
        dd_verdict = f"âœ… Sterke AI-zichtbaarheid ({visibility_score}/100)."
    elif visibility_score >= 40:
        risk_level = "MIDDEL"
        dd_verdict = f"ðŸŸ¡ Matige AI-zichtbaarheid ({visibility_score}/100)."
    else:
        risk_level = "HOOG"
        dd_verdict = f"âš ï¸ Lage AI-zichtbaarheid ({visibility_score}/100)."

    return {
        "status": "ok", "module": "geo_citations", "visibility_score": visibility_score,
        "mention_count": mention_count, "total_queries": total_queries, "mentioned_in": mentioned_in,
        "risk_level": risk_level, "dd_verdict": dd_verdict, "raw_data": {k: v for k, v in result.items() if k not in ("error",)},
    }


@router.get("/geo-risk")
async def geo_risk_scan(domain: str = Query(...), company_name: str = Query(""), sector: str = Query("")):
    async def event_stream():
        results = {}
        yield f"data: {json.dumps({'phase': 'robots', 'status': 'running', 'label': 'robots.txt AI-crawler analyse...'})}\n\n"
        try:
            robots = await check_robots_ai_blockers(domain)
            results["robots"] = robots
            yield f"data: {json.dumps({'phase': 'robots', 'status': 'done', 'result': robots})}\n\n"
        except Exception as e:
            results["robots"] = {"status": "error", "error": str(e)}
            yield f"data: {json.dumps({'phase': 'robots', 'status': 'error', 'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'phase': 'llmstxt', 'status': 'running', 'label': 'llms.txt standaard detectie...'})}\n\n"
        try:
            llmstxt = await check_llms_txt(domain)
            results["llmstxt"] = llmstxt
            yield f"data: {json.dumps({'phase': 'llmstxt', 'status': 'done', 'result': llmstxt})}\n\n"
        except Exception as e:
            results["llmstxt"] = {"status": "error", "error": str(e)}
            yield f"data: {json.dumps({'phase': 'llmstxt', 'status': 'error', 'error': str(e)})}\n\n"

        if company_name:
            yield f"data: {json.dumps({'phase': 'citations', 'status': 'running', 'label': 'LLM citatie-analyse per platform...'})}\n\n"
            try:
                citations = await check_ai_citations(company_name, domain, sector)
                results["citations"] = citations
                yield f"data: {json.dumps({'phase': 'citations', 'status': 'done', 'result': citations})}\n\n"
            except Exception as e:
                results["citations"] = {"status": "error", "error": str(e)}
                yield f"data: {json.dumps({'phase': 'citations', 'status': 'error', 'error': str(e)})}\n\n"

        robots_risk = 0
        llmstxt_risk = 0
        citation_risk = 0
        if results.get("robots", {}).get("status") == "ok":
            robots_risk = int((results["robots"].get("total_blocked", 0) / max(len(_AI_CRAWLERS), 1)) * 100)
        if results.get("llmstxt", {}).get("status") == "ok":
            llmstxt_risk = 0 if results["llmstxt"].get("exists") else 30
        if results.get("citations", {}).get("status") == "ok":
            citation_risk = max(0, 100 - results["citations"].get("visibility_score", 0))

        has_citations = "citations" in results and results["citations"].get("status") == "ok"
        if has_citations:
            total_risk_score = int(robots_risk * 0.40 + citation_risk * 0.40 + llmstxt_risk * 0.20)
        else:
            total_risk_score = int(robots_risk * 0.60 + llmstxt_risk * 0.40)

        total_risk_score = min(100, max(0, total_risk_score))

        if total_risk_score >= 70:
            verdict, verdict_label = "KRITIEK", f"ðŸš¨ Digital Debt Score: {total_risk_score}/100"
        elif total_risk_score >= 40:
            verdict, verdict_label = "HOOG", f"âš ï¸ Digital Debt Score: {total_risk_score}/100"
        elif total_risk_score >= 15:
            verdict, verdict_label = "MIDDEL", f"ðŸŸ¡ Digital Debt Score: {total_risk_score}/100"
        else:
            verdict, verdict_label = "LAAG", f"âœ… Digital Debt Score: {total_risk_score}/100"

        yield f"data: {json.dumps({'phase': 'complete', 'status': 'done', 'digital_debt_score': total_risk_score, 'verdict': verdict, 'verdict_label': verdict_label, 'domain': domain, 'company_name': company_name or domain, 'components': {'robots_risk': robots_risk, 'llmstxt_risk': llmstxt_risk, 'citation_risk': citation_risk if has_citations else None}, 'results': results})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
