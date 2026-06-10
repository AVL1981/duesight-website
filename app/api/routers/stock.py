"""
Stock Imagery router â€” POST /api/stock/search
Wraps tools.stock_imagery.StockImagery from duesight-agent.

Cascade: Unsplash â†’ Pexels â†’ Pixabay â†’ Wikimedia Commons (default).
All sources free, all CC-or-equivalent licenses, all commercial use OK.
"""
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("api.stock")
router = APIRouter()

# Cross-project import from duesight-agent
_AGENT_DIR = Path(r"C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-agent")
if _AGENT_DIR.exists() and str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

try:
    from tools.stock_imagery import StockImagery
    _AVAILABLE = True
except ImportError as e:
    logger.error("stock_imagery import failed: %s", e)
    _AVAILABLE = False


class StockSearchRequest(BaseModel):
    query: str = Field(..., description="Search keywords, e.g. 'modern office building'")
    limit: int = Field(default=10, ge=1, le=30, description="Max results per source")
    orientation: str = Field(default="any", description="any | landscape | portrait | square")


@router.post("/stock/search", tags=["Stock Imagery"])
async def stock_search(req: StockSearchRequest):
    """
    Search free stock imagery across Unsplash + Pexels + Pixabay + Wikimedia.

    Sources without API keys configured are silently skipped (Wikimedia always
    works â€” no key required). Set in .env to enable extras:
      UNSPLASH_ACCESS_KEY, PEXELS_API_KEY, PIXABAY_API_KEY
    """
    if not _AVAILABLE:
        raise HTTPException(503, "Stock imagery module not available")
    if not req.query.strip():
        raise HTTPException(400, "query is required")

    try:
        async with StockImagery() as s:
            result = await s.search(req.query, limit=req.limit, orientation=req.orientation)
        return asdict(result)
    except Exception as e:
        logger.exception("stock search failed for %r: %s", req.query, e)
        raise HTTPException(500, f"search_failed: {e.__class__.__name__}")


@router.get("/stock/health", tags=["Stock Imagery"])
async def stock_health():
    """Show which stock sources are configured."""
    import os
    return {
        "available": _AVAILABLE,
        "sources": {
            "unsplash": bool(os.getenv("UNSPLASH_ACCESS_KEY")),
            "pexels": bool(os.getenv("PEXELS_API_KEY")),
            "pixabay": bool(os.getenv("PIXABAY_API_KEY")),
            "wikimedia": True,  # always available
        },
    }
