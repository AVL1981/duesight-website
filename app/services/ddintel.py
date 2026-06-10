import json
import logging
import os
from typing import Any

import httpx

from app.core.cache import _CACHEABLE_TOOLS, cache_get, cache_set

DDINTEL_BASE = os.getenv("DUESIGHT_DDINTEL_BASE_URL", "http://localhost:8000").rstrip("/")
SCAN_TIMEOUT = 15.0  # seconds per DDIntel call

async def _call_ddintel_raw(tool_name: str, params: dict[str, Any]) -> dict:
    """Raw DDIntel call without caching."""
    async with httpx.AsyncClient(timeout=SCAN_TIMEOUT) as client:
        try:
            # Try MCP JSON-RPC style call
            resp = await client.post(
                f"{DDINTEL_BASE}/call",
                json={
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": params,
                    },
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                # MCP returns content in result.content[0].text
                if "result" in data and "content" in data["result"]:
                    content = data["result"]["content"]
                    if content and isinstance(content, list):
                        text = content[0].get("text", "{}")
                        return json.loads(text)
                return data

            # Fallback: try direct tool endpoint
            resp = await client.post(
                f"{DDINTEL_BASE}/tools/{tool_name}",
                json=params,
            )
            if resp.status_code == 200:
                return resp.json()

            return {"error": f"DDIntel returned {resp.status_code}", "tool": tool_name}

        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
            return {"error": "DDIntel server unreachable", "tool": tool_name}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON from DDIntel", "tool": tool_name}
        except Exception as e:
            return {"error": str(e), "tool": tool_name}


async def call_ddintel(tool_name: str, params: dict[str, Any]) -> dict:
    """Call a DDIntel MCP tool via HTTP, with SQLite caching for KvK tools.

    For cacheable tools (KvK, financials, mutations), checks local cache
    first and returns cached data if available (TTL: 30 days).
    Non-cacheable tools bypass the cache entirely.

    Args:
        tool_name: DDIntel tool name (e.g., 'kvk_screen')
        params: Tool parameters as a dict

    Returns:
        dict with tool results, or error dict on failure
    """
    # Check cache for cacheable tools
    if tool_name in _CACHEABLE_TOOLS:
        cached = cache_get(tool_name, params)
        if cached is not None:
            cached["_cached"] = True
            cached["_cache_note"] = "Result from local cache (KvK rate limit protection)"
            return cached

    # Call the actual API
    result = await _call_ddintel_raw(tool_name, params)

    # Cache successful responses (don't cache errors or 429s)
    if tool_name in _CACHEABLE_TOOLS and "error" not in result:
        api_errors = result.get("api_errors", [])
        has_429 = any("429" in str(e) for e in api_errors)
        if not has_429:
            cache_set(tool_name, params, result)

    return result
