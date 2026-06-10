import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our new modular routers
from app.api.routers import scan
from app.api.routers import financial
from app.api.routers import geo
from app.api.routers import subsidy
from app.api.routers import shadow
from app.api.routers import location
from app.api.routers import stock
from app.api.routers import property as property_router
from app.api.routers import privacy
from app.api.routers import contract
from app.core.cache import get_cache_stats
from app.core.security import configure_api_security
from app.core.security_headers import SecurityHeadersMiddleware

app = FastAPI(
    title="DueSight Teaser Scan â€” Refactored API",
    version="2.0.0",
    description="Scalable backend for DueSight Free Scans & Intelligence",
)

# CORS configuration â€” restrict to known origins
_CORS_ORIGINS = [
    "https://duesight.nl",
    "https://www.duesight.nl",
]
if os.environ.get("DUESIGHT_ENV") == "development":
    _CORS_ORIGINS += [
        "http://localhost:8000",
        "http://localhost:5050",
        "http://localhost:5051",
        "http://localhost:5052",
        "http://localhost:8088",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5050",
        "http://127.0.0.1:5051",
        "http://127.0.0.1:5052",
        "http://127.0.0.1:8088",
    ]
_CORS_ORIGINS += [
    origin.strip()
    for origin in os.environ.get("DUESIGHT_CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

configure_api_security(
    app,
    public_paths={
        "/health",
        "/api/location/health",
        "/api/property/health",
        "/api/stock/health",
        "/api/privacy/audit",
        "/api/privacy/stats",
        "/api/privacy/verify/{session_id}",
        "/api/privacy/test-purge",
        "/api/contract/health",
        "/api/contract/triage",
    },
    admin_paths={"/api/cache-stats"},
    admin_prefixes={"/api/shadow"},
    public_limited_paths={"/api/teaser-scan", "/api/tech-scan-active"},
    service_name="duesight-api-v2",
)

# OWASP security headers (CSP/HSTS/Frame/Permissions/COOP/CORP). Register
# after the auth middleware so auth-generated error responses are covered too.
app.add_middleware(SecurityHeadersMiddleware)

# Include Routers
app.include_router(scan.router, prefix="/api", tags=["Core Scans"])
app.include_router(financial.router, prefix="/api", tags=["Financial & Entity Scans"])
app.include_router(geo.router, prefix="/api", tags=["GEO Digital Debt Scans"])
app.include_router(subsidy.router, prefix="/api/subsidy", tags=["Subsidies & Grants"])
app.include_router(shadow.router, prefix="/api/shadow", tags=["Zero-Trace Operations"])
app.include_router(location.router, prefix="/api", tags=["Location Intelligence"])
app.include_router(stock.router, prefix="/api", tags=["Stock Imagery"])
app.include_router(property_router.router, prefix="/api", tags=["Property Intelligence"])
app.include_router(privacy.router, prefix="/api", tags=["Privacy & Compliance"])
app.include_router(contract.router, prefix="/api", tags=["Contract Triage"])

# Global system endpoints
@app.get("/api/cache-stats", tags=["System"])
async def cache_stats():
    """Return cache statistics for monitoring."""
    return get_cache_stats()

@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "DueSight API v2"}


@app.get("/property-viewer.html", tags=["Property Intelligence"])
async def serve_property_viewer():
    """Serve the cinematic 3D property viewer HTML (Three.js engine)."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    viewer = Path(__file__).resolve().parent.parent / "property-viewer.html"
    if not viewer.exists():
        from fastapi import HTTPException
        raise HTTPException(404, "viewer not found")
    return FileResponse(viewer, media_type="text/html")


@app.get("/property-viewer-cesium.html", tags=["Property Intelligence"])
async def serve_property_viewer_cesium():
    """Serve the high-end Cesium viewer with PDOK 3D Tiles + ESRI imagery + bloom."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    viewer = Path(__file__).resolve().parent.parent / "property-viewer-cesium.html"
    if not viewer.exists():
        from fastapi import HTTPException
        raise HTTPException(404, "viewer not found")
    return FileResponse(viewer, media_type="text/html")


@app.get("/renders/{filename}", tags=["Property Intelligence"])
async def serve_render(filename: str):
    """Serve rendered MP4 files."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    if "/" in filename or "\\" in filename or ".." in filename:
        from fastapi import HTTPException
        raise HTTPException(400, "invalid filename")
    p = Path(__file__).resolve().parent.parent / "renders" / filename
    if not p.exists():
        from fastapi import HTTPException
        raise HTTPException(404, "render not found")
    return FileResponse(p, media_type="video/mp4")

if __name__ == "__main__":
    import uvicorn
    # This enables running the script directly with `python main.py`
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5050,
        reload=True,
        server_header=False,
        date_header=False,
    )
