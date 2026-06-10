"""
Location Intelligence router â€” POST /api/location/scan
Wraps tools.location_intel.LocationIntel from duesight-agent.

Returns multi-source geo verification:
  - PDOK (NL) / Swisstopo (CH) / OSM (EU) geocoding
  - 3DBAG (NL) building 3D intel
  - OSM Overpass nearby POIs
  - Mapillary street imagery (optional)
  - Shell company risk score
"""
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("api.location")
router = APIRouter()

# Resolve agent dir for cross-project import
_AGENT_DIR = Path(r"C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-agent")
if _AGENT_DIR.exists() and str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

try:
    from tools.location_intel import LocationIntel
    _AVAILABLE = True
except ImportError as e:
    logger.error("location_intel import failed: %s", e)
    _AVAILABLE = False


class LocationScanRequest(BaseModel):
    address: str = Field(..., description="Full address: street + house number + postal code + city")
    country: str = Field(default="auto", description="auto | NL | DE | CH | AT | EU")


@router.post("/location/scan", tags=["Location Intelligence"])
async def location_scan(req: LocationScanRequest):
    """
    Multi-source geo verification cascade.

    Free APIs only â€” no costs:
      - PDOK Locatieserver (NL official BAG)
      - 3DBAG (TU Delft 3D buildings)
      - Swisstopo (CH government)
      - OSM Nominatim (EU geocoding)
      - OSM Overpass (POI + building data)
      - Mapillary (street imagery, if MAPILLARY_ACCESS_TOKEN set)
    """
    if not _AVAILABLE:
        raise HTTPException(503, "Location intelligence module not available â€” check agent path")

    if not req.address.strip():
        raise HTTPException(400, "address is required")

    try:
        async with LocationIntel() as intel:
            report = await intel.scan(req.address, req.country)
        return asdict(report)
    except Exception as e:
        logger.exception("location scan failed for %s: %s", req.address, e)
        raise HTTPException(500, f"scan_failed: {e.__class__.__name__}")


@router.get("/location/health", tags=["Location Intelligence"])
async def location_health():
    """Quick health check â€” confirms module is loadable."""
    return {
        "available": _AVAILABLE,
        "sources": [
            "PDOK Locatieserver (NL)",
            "3DBAG (NL, TU Delft)",
            "Swisstopo (CH)",
            "OSM Nominatim (EU)",
            "OSM Overpass (EU, 3 mirrors)",
            "Mapillary (optional, EU)",
        ],
    }
