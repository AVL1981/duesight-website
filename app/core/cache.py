import hashlib
import json
import sqlite3
import time
from pathlib import Path

# Cache DB at the root of duesight-website
_CACHE_DB = Path(__file__).parent.parent.parent / "kvk_cache.db"
_CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 days

# Tools that benefit from caching (KvK-dependent, slow, rate-limited)
_CACHEABLE_TOOLS = {
    "kvk_screen",
    "kvk_financials",
    "scan_mutations",
    "scan_court_cases",
    "get_company_financials",
    "get_company_registry",
    "financial_proxy_analysis",
}

def init_cache_db() -> None:
    """Create cache table if it doesn't exist."""
    conn = sqlite3.connect(str(_CACHE_DB))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key   TEXT PRIMARY KEY,
            tool_name   TEXT NOT NULL,
            params_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at  REAL NOT NULL,
            expires_at  REAL NOT NULL,
            hit_count   INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()

def _cache_key(tool_name: str, params: dict) -> str:
    """Generate a deterministic cache key from tool name + params."""
    raw = json.dumps({"tool": tool_name, "params": params}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()

def cache_get(tool_name: str, params: dict) -> dict | None:
    """Return cached result if valid, else None."""
    key = _cache_key(tool_name, params)
    try:
        conn = sqlite3.connect(str(_CACHE_DB))
        row = conn.execute(
            "SELECT result_json, expires_at FROM api_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row and row[1] > time.time():
            conn.execute(
                "UPDATE api_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                (key,),
            )
            conn.commit()
            conn.close()
            return json.loads(row[0])
        conn.close()
    except Exception:
        pass
    return None

def cache_set(tool_name: str, params: dict, result: dict) -> None:
    """Store a successful API response in cache."""
    key = _cache_key(tool_name, params)
    now = time.time()
    try:
        conn = sqlite3.connect(str(_CACHE_DB))
        conn.execute(
            """
            INSERT OR REPLACE INTO api_cache
                (cache_key, tool_name, params_json, result_json, created_at, expires_at, hit_count)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                key,
                tool_name,
                json.dumps(params, sort_keys=True),
                json.dumps(result),
                now,
                now + _CACHE_TTL_SECONDS,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_cache_stats() -> dict:
    """Return cache statistics for monitoring."""
    try:
        conn = sqlite3.connect(str(_CACHE_DB))
        total = conn.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM api_cache WHERE expires_at > ?", (time.time(),)
        ).fetchone()[0]
        total_hits = conn.execute(
            "SELECT COALESCE(SUM(hit_count), 0) FROM api_cache"
        ).fetchone()[0]
        by_tool = conn.execute(
            """
            SELECT tool_name, COUNT(*), COALESCE(SUM(hit_count), 0)
            FROM api_cache WHERE expires_at > ?
            GROUP BY tool_name
            """,
            (time.time(),),
        ).fetchall()
        conn.close()
        return {
            "total_entries": total,
            "active_entries": active,
            "expired_entries": total - active,
            "total_cache_hits": total_hits,
            "ttl_days": _CACHE_TTL_SECONDS // 86400,
            "by_tool": {
                row[0]: {"entries": row[1], "hits": row[2]} for row in by_tool
            },
            "db_path": str(_CACHE_DB),
        }
    except Exception as e:
        return {"error": str(e)}

# Auto-init on import
init_cache_db()
