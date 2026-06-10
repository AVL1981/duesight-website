"""
Property dossier router â€” combines Modules A + B + C in one endpoint.

Routes:
  GET  /api/property/dossier   â€” full A+B+C combined response (used by viewer)
  POST /api/property/registry  â€” Module C only (official Dutch registry)
  POST /api/property/exterior  â€” Module A only (3D scene spec)
  POST /api/property/interior  â€” Module B only (interior intel)
  GET  /api/property/health    â€” module availability check
"""
import asyncio
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("api.property")
router = APIRouter()

_AGENT_DIR = Path(r"C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-agent")
if _AGENT_DIR.exists() and str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

try:
    from tools.property_registry import PropertyRegistry
    from tools.building_exterior_3d import ExteriorScene
    from tools.building_interior_intel import InteriorIntel
    _AVAILABLE = True
except ImportError as e:
    logger.error("property modules import failed: %s", e)
    _AVAILABLE = False

try:
    from tools.cinematic_renderer import render_property_mp4
    _RENDERER_AVAILABLE = True
except ImportError as e:
    logger.error("cinematic_renderer import failed: %s", e)
    _RENDERER_AVAILABLE = False

try:
    from tools.cinematic_enhancer import enhance_mp4, _check_binaries as _enh_bins
    _ENHANCER_AVAILABLE = all(_enh_bins().values())
except ImportError as e:
    logger.error("cinematic_enhancer import failed: %s", e)
    _ENHANCER_AVAILABLE = False

try:
    from tools.ai_video_gen import generate_video as ai_generate_video
    _AI_VIDEO_AVAILABLE = bool(__import__("os").environ.get("GOOGLE_API_KEY") or __import__("os").environ.get("GEMINI_API_KEY"))
except ImportError as e:
    logger.error("ai_video_gen import failed: %s", e)
    _AI_VIDEO_AVAILABLE = False

try:
    from tools.gaussian_splatting import GaussianSplattingPipeline
    _GSPLAT_AVAILABLE = True
except ImportError as e:
    logger.error("gaussian_splatting import failed: %s", e)
    _GSPLAT_AVAILABLE = False

try:
    from tools.cinematic_pipeline import t2v_cinematic, i2v_cinematic
    _LOCAL_VIDEO_AVAILABLE = True
except ImportError as e:
    logger.error("cinematic_pipeline import failed: %s", e)
    _LOCAL_VIDEO_AVAILABLE = False

try:
    from tools.realistic_demo_pipeline import realistic_demo
    _REALISTIC_DEMO_AVAILABLE = True
except ImportError as e:
    logger.error("realistic_demo_pipeline import failed: %s", e)
    _REALISTIC_DEMO_AVAILABLE = False

try:
    from tools.company_tour_aggregator import CompanyTourAggregator
    _TOUR_AVAILABLE = True
except ImportError as e:
    logger.error("company_tour_aggregator import failed: %s", e)
    _TOUR_AVAILABLE = False

try:
    from tools.earth_studio_helper import generate_esp, write_user_instructions
    from tools.external_seed_ingestor import ingest as ingest_external_seeds, SOURCE_LICENSES
    _EXTERNAL_SEEDS_AVAILABLE = True
except ImportError as e:
    logger.error("earth_studio/external_seeds import failed: %s", e)
    _EXTERNAL_SEEDS_AVAILABLE = False

try:
    from tools.video_brief_generator import VideoBriefGenerator
    _VIDEO_BRIEF_AVAILABLE = True
except ImportError as e:
    logger.error("video_brief_generator import failed: %s", e)
    _VIDEO_BRIEF_AVAILABLE = False


class AddressRequest(BaseModel):
    address: str = Field(..., description="Full address (street + city or postcode)")
    company: str = Field(default="", description="Optional company name (improves Module B precision)")


@router.get("/property/dossier", tags=["Property Intelligence"])
async def property_dossier(
    address: str = Query(...),
    company: str = Query(default=""),
):
    """
    Full property dossier â€” combines Modules A + B + C in parallel.

    Returns:
      {
        "dossier": {...},   # Module C: BAG/Kadaster/3DBAG official data
        "scene": {...},     # Module A: Three.js scene spec + camera path
        "intel": {...}      # Module B: Web/news/YouTube/signals
      }
    """
    if not _AVAILABLE:
        raise HTTPException(503, "Property modules not available")
    if not address.strip():
        raise HTTPException(400, "address is required")

    try:
        # Module C first â€” Module A needs its output (RD coords + height)
        async with PropertyRegistry() as p:
            dossier = await p.lookup(address)

        if not dossier.rd_x:
            return {
                "dossier": asdict(dossier),
                "scene": None,
                "intel": None,
                "error": "geocoding_failed",
            }

        # Module A + B in parallel (both depend on dossier coords)
        async def build_scene():
            return await ExteriorScene().build(
                address=dossier.address or address,
                latitude=dossier.latitude,
                longitude=dossier.longitude,
                rd_x=dossier.rd_x,
                rd_y=dossier.rd_y,
                building_height_m=dossier.building_3d.height_max_m or 30.0,
                ground_level_m=dossier.building_3d.ground_level_m or 0.0,
            )

        async def gather_intel():
            async with InteriorIntel() as i:
                return await i.gather(address, company_name=company)

        scene, intel = await asyncio.gather(build_scene(), gather_intel(), return_exceptions=True)

        scene_out = asdict(scene) if not isinstance(scene, Exception) else {"error": str(scene)}
        intel_out = asdict(intel) if not isinstance(intel, Exception) else {"error": str(intel)}

        return {
            "dossier": asdict(dossier),
            "scene": scene_out,
            "intel": intel_out,
        }
    except Exception as e:
        logger.exception("dossier failed for %r: %s", address, e)
        raise HTTPException(500, f"dossier_failed: {e.__class__.__name__}")


@router.post("/property/registry", tags=["Property Intelligence"])
async def property_registry(req: AddressRequest):
    """Module C only â€” official Dutch property registry (BAG/Kadaster/3DBAG)."""
    if not _AVAILABLE:
        raise HTTPException(503, "Module not available")
    try:
        async with PropertyRegistry() as p:
            dossier = await p.lookup(req.address)
        return asdict(dossier)
    except Exception as e:
        logger.exception("registry failed: %s", e)
        raise HTTPException(500, f"registry_failed: {e.__class__.__name__}")


@router.post("/property/interior", tags=["Property Intelligence"])
async def property_interior(req: AddressRequest):
    """Module B only â€” interior intel aggregator (web/YouTube/Wikipedia/Places)."""
    if not _AVAILABLE:
        raise HTTPException(503, "Module not available")
    try:
        async with InteriorIntel() as i:
            report = await i.gather(req.address, company_name=req.company)
        return asdict(report)
    except Exception as e:
        logger.exception("interior failed: %s", e)
        raise HTTPException(500, f"interior_failed: {e.__class__.__name__}")


class RenderRequest(BaseModel):
    address: str = Field(...)
    company: str = Field(default="")
    interior: bool = Field(default=False, description="Procedural interior view (illustrative only)")
    width: int = Field(default=1920, ge=640, le=3840)
    height: int = Field(default=1080, ge=480, le=2160)
    engine: str = Field(default="cesium", description="cesium (real geometry, PDOK 3D Tiles) or three (procedural box)")


@router.post("/property/render-mp4", tags=["Property Intelligence"])
async def property_render_mp4(req: RenderRequest):
    """
    Render a cinematic 30s MP4 of the property viewer (Playwright headless).

    Returns: { "mp4_url": "/renders/<filename>", "size_bytes": N }

    NOTE: blocking call (~50-90s for 1080p). Caller should expect ~1 min wait.
    """
    if not _RENDERER_AVAILABLE:
        raise HTTPException(503, "cinematic_renderer not available â€” install playwright + chromium")
    if not req.address.strip():
        raise HTTPException(400, "address is required")
    try:
        viewer_html = (
            "property-viewer-cesium.html" if req.engine == "cesium"
            else "property-viewer.html"
        )
        # Cesium needs more time for tile streaming + texture load
        timeout = 180.0 if req.engine == "cesium" else 90.0
        out = await render_property_mp4(
            address=req.address,
            company=req.company,
            viewer_url=f"http://127.0.0.1:5050/{viewer_html}",
            width=req.width,
            height=req.height,
            interior=req.interior,
            timeout_s=timeout,
        )
        return {
            "mp4_url": f"/renders/{out.name}",
            "size_bytes": out.stat().st_size,
            "interior_mode": req.interior,
        }
    except Exception as e:
        logger.exception("render failed: %s", e)
        raise HTTPException(500, f"render_failed: {e.__class__.__name__}: {str(e)[:200]}")


class EnhanceRequest(BaseModel):
    input_mp4: str = Field(..., description="Path to existing MP4 (e.g. /renders/X.mp4)")
    upscale_factor: int = Field(default=4, ge=2, le=4)
    target_fps: int = Field(default=60, ge=30, le=120)


@router.post("/property/enhance-mp4", tags=["Property Intelligence"])
async def property_enhance_mp4(req: EnhanceRequest):
    """
    AI-enhance an existing MP4 via Real-ESRGAN 4Ã— upscale + RIFE 60fps interp.

    Run time: ~3-6 min per 30s 720p clip on GPU. Output: ~5K 60fps MP4.
    Preserves geometric accuracy (no AI hallucination â€” pure upscaling).
    """
    if not _ENHANCER_AVAILABLE:
        raise HTTPException(503, "Enhancer not available â€” check Real-ESRGAN/RIFE binaries in ~/.duesight/bin/")
    from pathlib import Path
    # Strip leading /renders/ if present, resolve to absolute
    rel = req.input_mp4.lstrip("/")
    base = Path(__file__).resolve().parent.parent.parent
    input_path = base / rel if not Path(rel).is_absolute() else Path(rel)
    if not input_path.exists():
        raise HTTPException(404, f"input not found: {input_path}")
    try:
        out = await enhance_mp4(
            input_path=input_path,
            upscale_factor=req.upscale_factor,
            target_fps=req.target_fps,
        )
        return {
            "mp4_url": f"/renders/{out.name}",
            "size_bytes": out.stat().st_size,
        }
    except Exception as e:
        logger.exception("enhance failed: %s", e)
        raise HTTPException(500, f"enhance_failed: {e.__class__.__name__}: {str(e)[:200]}")


class AIVideoRequest(BaseModel):
    address: str = Field(...)
    company: str = Field(default="")
    duration_s: int = Field(default=8, ge=4, le=8)
    fast_model: bool = Field(default=True, description="Veo fast (5Ã— cheaper)")
    style: str = Field(default="drone", description="drone | ground | showcase")
    custom_prompt: str = Field(default="")


@router.post("/property/ai-video", tags=["Property Intelligence"])
async def property_ai_video(req: AIVideoRequest):
    """
    âš ï¸ Generate AI cinematic via Veo 3 (Gemini API). Costs real money.

    Veo HALLUCINATES â€” output not geometrically accurate. Marketing/pitch only,
    NEVER attach to DD report. Cost: ~$0.10-0.50/sec output (8s = $0.80-$4).
    """
    if not _AI_VIDEO_AVAILABLE:
        raise HTTPException(503, "AI video not available â€” set GOOGLE_API_KEY in env")

    # Pull metadata to enrich prompt
    height_m = 0.0
    year = None
    func = ""
    try:
        async with PropertyRegistry() as p:
            d = await p.lookup(req.address)
        height_m = d.building_3d.height_max_m or 0.0
        year = d.pand.bouwjaar
        func = d.primary_function
    except Exception:
        pass

    try:
        out = await ai_generate_video(
            address=req.address, company=req.company,
            building_height_m=height_m, building_year=year, building_function=func,
            style=req.style, duration_s=req.duration_s, fast_model=req.fast_model,
            custom_prompt=req.custom_prompt or None,
        )
        return {
            "mp4_url": f"/renders/{out.name}",
            "size_bytes": out.stat().st_size,
            "warning": "AI-generated â€” not geometrically accurate. Marketing use only.",
        }
    except Exception as e:
        logger.exception("ai-video failed: %s", e)
        raise HTTPException(500, f"ai_video_failed: {e.__class__.__name__}: {str(e)[:200]}")


class GSplatCollectRequest(BaseModel):
    address: str = Field(...)
    building_name: str = Field(default="")
    company: str = Field(default="")
    max_photos: int = Field(default=60, ge=10, le=200)


@router.post("/property/gsplat-collect", tags=["Property Intelligence"])
async def property_gsplat_collect(req: GSplatCollectRequest):
    """
    Phase 1 of Gaussian Splatting: collect public photos of the building.

    Returns collected count + COLMAP/training commands to run manually.
    Quality of GS reconstruction depends on photo COUNT (50+ ideal).
    """
    if not _GSPLAT_AVAILABLE:
        raise HTTPException(503, "GSplat not available")
    try:
        async with PropertyRegistry() as p:
            d = await p.lookup(req.address)
        async with GaussianSplattingPipeline() as gs:
            scene = await gs.collect(
                address=req.address,
                building_name=req.building_name,
                company_name=req.company,
                latitude=d.latitude, longitude=d.longitude,
                max_photos_per_source=req.max_photos,
            )
        return {
            "scene_dir": str(scene.scene_dir),
            "photo_count": scene.photo_count,
            "sources_used": scene.sources_used,
            "warnings": scene.warnings,
            "next_steps": {
                "colmap": scene.colmap_command,
                "training": scene.gsplat_command,
            },
        }
    except Exception as e:
        logger.exception("gsplat-collect failed: %s", e)
        raise HTTPException(500, f"gsplat_failed: {e.__class__.__name__}: {str(e)[:200]}")


class LocalVideoRequest(BaseModel):
    address: str = Field(default="")
    company: str = Field(default="")
    mode: str = Field(default="t2v", description="t2v (LTX text-to-video) | i2v (CogVideoX image-to-video)")
    prompt: str = Field(default="", description="Text prompt (auto-built from address+company if empty)")
    image_path: str = Field(default="", description="Path to reference image (i2v mode only)")
    chain_enhance: bool = Field(default=True, description="Auto-chain through Real-ESRGAN+RIFE for 5K 60fps")


@router.post("/property/local-video", tags=["Property Intelligence"])
async def property_local_video(req: LocalVideoRequest):
    """
    Generate AI video LOCALLY on your RTX 5060 Ti GPUs (no API cost).

    Modes:
      - t2v: LTX Video text-to-video (~5s @ 768x512 â†’ enhance to 5K 60fps)
      - i2v: CogVideoX-5b image-to-video (~6s @ 720x480 â†’ enhance)

    Optional chain_enhance=true (default): auto-pipe through Real-ESRGAN + RIFE.
    Run time: 3-8 min per clip (vs $0.80-$3 on Veo 3 API).
    """
    if not _LOCAL_VIDEO_AVAILABLE:
        raise HTTPException(503, "Local video gen not available â€” check diffusers + cinematic_pipeline")
    from pathlib import Path
    try:
        if req.mode == "t2v":
            prompt = req.prompt
            if not prompt and req.address:
                # Auto-build from BAG metadata
                async with PropertyRegistry() as p:
                    d = await p.lookup(req.address)
                from tools.ai_video_gen import _build_prompt
                prompt = _build_prompt(
                    address=req.address, company=req.company,
                    building_height_m=d.building_3d.height_max_m or 0.0,
                    building_year=d.pand.bouwjaar,
                    building_function=d.primary_function,
                )
            if not prompt:
                raise HTTPException(400, "either 'prompt' or 'address' is required")
            out = await t2v_cinematic(prompt=prompt, skip_enhance=not req.chain_enhance)
        elif req.mode == "i2v":
            if not req.image_path:
                raise HTTPException(400, "image_path required for i2v mode")
            img = Path(req.image_path)
            if not img.exists():
                raise HTTPException(404, f"image not found: {img}")
            out = await i2v_cinematic(image_path=img, prompt=req.prompt, skip_enhance=not req.chain_enhance)
        else:
            raise HTTPException(400, f"unknown mode: {req.mode} (use t2v or i2v)")

        return {
            "mp4_url": f"/renders/{out.name}",
            "size_bytes": out.stat().st_size,
            "mode": req.mode,
            "enhanced": req.chain_enhance,
            "warning": "AI-generated content â€” not geometrically accurate. Marketing/wow only.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("local-video failed: %s", e)
        raise HTTPException(500, f"local_video_failed: {e.__class__.__name__}: {str(e)[:200]}")


class RealisticDemoRequest(BaseModel):
    address: str = Field(...)
    company: str = Field(default="")
    website_url: str = Field(default="")
    num_keyframes: int = Field(default=5, ge=3, le=7)
    interior_clips: int = Field(default=0, ge=0, le=5, description="0 = exterior only; 2-4 = mix interior")
    fast: bool = Field(default=False, description="Wan 20 steps + 49 frames (faster, lower quality)")
    enhance: bool = Field(default=True, description="Real-ESRGAN+RIFE chain")
    parallel_gpus: int = Field(default=2, ge=1, le=2, description="2 = dual-GPU parallel (halves time)")
    seeds: str = Field(default="real_photos", description="real_photos (default â€” best quality) | cesium (game-engine look)")


class CompanyTourRequest(BaseModel):
    company_name: str = Field(...)
    website_url: str = Field(default="")
    address: str = Field(default="")
    max_per_source: int = Field(default=100, ge=10, le=500)


@router.post("/property/company-tour", tags=["Property Intelligence"])
async def property_company_tour(req: CompanyTourRequest):
    """
    Aggregeer publieke interior foto's van een bedrijf vanuit 5 bronnen parallel.

    Bronnen: Google Places + bedrijfswebsite crawl + YouTube frame extract +
             Wikipedia + DuckDuckGo image search + Matterport iframe detect.

    Output: ~50-400 interior foto's in ~/.duesight/company_tours/<slug>/photos/.
    Bruikbaar als input voor /property-photoreal (Gaussian Splatting), Wan I2V seeds,
    of style LoRA training.

    Run-tijd: 1-5 min (parallel HTTP fetches + 1-2 YouTube downloads).
    """
    if not _TOUR_AVAILABLE:
        raise HTTPException(503, "company_tour_aggregator not available")
    if not req.company_name.strip():
        raise HTTPException(400, "company_name is required")
    try:
        async with CompanyTourAggregator() as agg:
            tour = await agg.aggregate(
                company_name=req.company_name,
                website_url=req.website_url,
                address=req.address,
                max_per_source=req.max_per_source,
            )
        return {
            "tour_dir": str(tour.tour_dir),
            "photo_count": tour.photo_count,
            "sources_used": tour.sources_used,
            "sources_failed": tour.sources_failed,
            "matterport_urls": tour.matterport_urls,
            "warnings": tour.warnings,
            "by_source": {
                s: sum(1 for p in tour.photos if p.source == s)
                for s in {p.source for p in tour.photos}
            },
            "has_enough_for_gs": tour.has_enough_for_gs,
            "has_enough_for_lora": tour.has_enough_for_lora,
        }
    except Exception as e:
        logger.exception("company-tour failed: %s", e)
        raise HTTPException(500, f"tour_failed: {e.__class__.__name__}: {str(e)[:200]}")


@router.post("/property/realistic-demo", tags=["Property Intelligence"])
async def property_realistic_demo(req: RealisticDemoRequest):
    """
    Build maximally realistic cinematic demo: real Cesium geometry + AI generation.

    Pipeline: PropertyRegistry â†’ Cesium MP4 â†’ N keyframes â†’ Wan I2V Ã— N
              â†’ ffmpeg xfade concat â†’ Real-ESRGAN+RIFE â†’ master 5K 60fps MP4

    Run time: ~80-90 min per property (RTX 5060 Ti, default settings).
    Use fast=true for ~30 min variant (lower quality but quicker).

    NOTE: Requires uvicorn server running on 5050 for Cesium viewer rendering.
    The endpoint will self-call viewer at http://127.0.0.1:5050.
    """
    if not _REALISTIC_DEMO_AVAILABLE:
        raise HTTPException(503, "realistic_demo_pipeline not available")
    try:
        result = await realistic_demo(
            address=req.address,
            company=req.company,
            website_url=req.website_url,
            num_keyframes=req.num_keyframes,
            interior_clips=req.interior_clips,
            enhance=req.enhance,
            fast=req.fast,
            parallel_gpus=req.parallel_gpus,
            seeds=req.seeds,
        )
        return {
            "mp4_url": f"/renders/{result.master_mp4.name}",
            "duration_s": result.duration_s,
            "render_seconds": result.total_render_seconds,
            "cesium_url": f"/renders/{result.cesium_mp4.name}",
            "clip_count": len(result.keyframe_clips),
            "enhanced": result.enhanced_master is not None,
            "sources": result.sources_used,
        }
    except Exception as e:
        logger.exception("realistic-demo failed: %s", e)
        raise HTTPException(500, f"realistic_demo_failed: {e.__class__.__name__}: {str(e)[:200]}")


class EarthStudioRequest(BaseModel):
    address: str = Field(...)
    duration_s: float = Field(default=20.0, ge=5.0, le=60.0)


@router.post("/property/earth-studio", tags=["Property Intelligence"])
async def property_earth_studio(req: EarthStudioRequest):
    """
    Generate Google Earth Studio .esp project file for cinematic flythrough.

    User-side workflow:
      1. Open generated .esp in https://earth.google.com/studio/
      2. Render PNG sequence
      3. Drop into ~/.duesight/external_seeds/<label>/earth_studio/
      4. Use as seeds via /property-seeds

    Free with Google Earth attribution. No API key needed.
    """
    if not _EXTERNAL_SEEDS_AVAILABLE:
        raise HTTPException(503, "earth_studio_helper not available")
    try:
        async with PropertyRegistry() as p:
            d = await p.lookup(req.address)
        lat = d.latitude or 52.337
        lon = d.longitude or 4.874
        h = (d.building_3d.height_max_m if d.building_3d else None) or 100.0

        esp = generate_esp(
            address=req.address, latitude=lat, longitude=lon,
            building_height_m=h, duration_s=req.duration_s,
        )
        readme = write_user_instructions(esp, req.address)
        return {
            "esp_path": str(esp),
            "readme_path": str(readme),
            "instructions": (
                "Open .esp in https://earth.google.com/studio/, render PNG sequence, "
                "drop frames in ~/.duesight/external_seeds/<label>/earth_studio/, "
                "then ingest via /property-seeds."
            ),
            "coords": {"lat": lat, "lon": lon},
        }
    except Exception as e:
        logger.exception("earth-studio failed: %s", e)
        raise HTTPException(500, f"earth_studio_failed: {e.__class__.__name__}: {str(e)[:200]}")


class ExternalSeedsRequest(BaseModel):
    input_dir: str = Field(..., description="Directory met user-dropped media")
    source: str = Field(..., description=f"Type: {' | '.join(SOURCE_LICENSES.keys()) if _EXTERNAL_SEEDS_AVAILABLE else 'N/A'}")
    label: str = Field(default="", description="Label voor batch (default: dir name)")
    fps: float = Field(default=0.5, description="Frames per second uit video's")
    max_frames: int = Field(default=200, ge=10, le=1000)


@router.post("/property/external-seeds", tags=["Property Intelligence"])
async def property_external_seeds(req: ExternalSeedsRequest):
    """
    Ingest externe content (Earth Studio, game footage, drone, eigen foto's)
    in pipeline-ready directory.

    Game footage license tag = NON-COMMERCIAL â€” downstream pipeline respecteert dit.
    """
    if not _EXTERNAL_SEEDS_AVAILABLE:
        raise HTTPException(503, "external_seed_ingestor not available")
    if req.source not in SOURCE_LICENSES:
        raise HTTPException(400, f"unknown source. Use one of: {list(SOURCE_LICENSES.keys())}")
    try:
        from pathlib import Path as _P
        seed = ingest_external_seeds(
            input_dir=_P(req.input_dir),
            source=req.source,
            label=req.label or _P(req.input_dir).name,
            extract_fps=req.fps,
            max_frames=req.max_frames,
        )
        return {
            "label": seed.label,
            "source": seed.source,
            "license_tag": seed.license_tag,
            "seed_dir": str(seed.seed_dir),
            "photo_count": seed.photo_count,
            "video_count": seed.video_count,
            "extracted_frames": seed.extracted_frames,
            "warnings": seed.warnings,
        }
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.exception("external-seeds failed: %s", e)
        raise HTTPException(500, f"ingest_failed: {e.__class__.__name__}: {str(e)[:200]}")


class VideoBriefRequest(BaseModel):
    address: str = Field(...)
    company: str = Field(default="")
    website_url: str = Field(default="")
    duration_s: int = Field(default=8, ge=4, le=30)
    camera_motion: str = Field(default="drone_orbit",
                                description="drone_orbit | slow_dolly | establishing | facade_close")
    target_services: list = Field(default_factory=lambda: ["seedance", "kling", "veo3"])
    render_cesium_video: bool = Field(default=True,
                                       description="Render Cesium MP4 as @vid1 camera trajectory reference")


@router.post("/property/video-brief", tags=["Property Intelligence"])
async def property_video_brief(req: VideoBriefRequest):
    """
    Genereer video gen brief voor Seedance 2.0 / Kling 3.0 / Veo 3.1.

    Pipeline: PropertyRegistry + InteriorIntel + ExteriorScene + SeedQualityOptimizer
              + Cesium camera-as-video â†’ 12-slot Seedance + 4K Kling + 3-ref Veo payloads
              + studio_brief.md voor 3D studio inhuur.

    Output: ~/.duesight/video_briefs/<slug>_<ts>/ met alle payloads + 9 refs + 1-3 vids.
    """
    if not _VIDEO_BRIEF_AVAILABLE:
        raise HTTPException(503, "video_brief_generator not available")
    try:
        gen = VideoBriefGenerator()
        brief = await gen.generate(
            address=req.address, company=req.company, website_url=req.website_url,
            duration_s=req.duration_s, camera_motion=req.camera_motion,
            target_services=req.target_services,
            render_cesium_video=req.render_cesium_video,
        )
        return {
            "output_dir": str(brief.output_dir),
            "image_refs_count": len(brief.image_references),
            "video_refs_count": len(brief.video_references),
            "sources_used": sorted(set(brief.sources_used)),
            "facts_summary": {
                "address": brief.facts.get("address_resolved"),
                "city": brief.facts.get("city"),
                "bouwjaar": brief.facts.get("bouwjaar"),
                "height_m": brief.facts.get("building_height_max_m"),
                "function": brief.facts.get("function_primary"),
                "floor_area_m2": brief.facts.get("total_floor_area_m2"),
            },
            "intel_signal_count": len(brief.intel_signals),
            "prompt_short": brief.prompt_short,
            "service_payloads": {
                "seedance": bool(brief.seedance_payload),
                "kling": bool(brief.kling_payload),
                "veo3": bool(brief.veo3_payload),
            },
            "warnings": brief.warnings,
        }
    except Exception as e:
        logger.exception("video-brief failed: %s", e)
        raise HTTPException(500, f"brief_failed: {e.__class__.__name__}: {str(e)[:200]}")


@router.get("/property/health", tags=["Property Intelligence"])
async def property_health():
    return {
        "available": _AVAILABLE,
        "renderer_available": _RENDERER_AVAILABLE,
        "enhancer_available": _ENHANCER_AVAILABLE,
        "ai_video_available": _AI_VIDEO_AVAILABLE,
        "gsplat_available": _GSPLAT_AVAILABLE,
        "local_video_available": _LOCAL_VIDEO_AVAILABLE,
        "realistic_demo_available": _REALISTIC_DEMO_AVAILABLE,
        "company_tour_available": _TOUR_AVAILABLE,
        "external_seeds_available": _EXTERNAL_SEEDS_AVAILABLE,
        "modules": {
            "C_registry": "BAG + Kadaster + 3DBAG",
            "A_exterior": "Three.js scene spec + camera path",
            "B_interior": "DuckDuckGo + Wikipedia + Google Places",
            "D_viewer_three": "/property-viewer.html (procedural)",
            "D_viewer_cesium": "/property-viewer-cesium.html (real geometry)",
            "MP4_renderer": "Playwright + Chromium + ffmpeg",
            "MP4_enhancer": "Real-ESRGAN 4Ã— + RIFE 60fps (GPU)",
            "AI_video_paid": "Veo 3 via Gemini API ($0.10-0.50/sec, hallucinates)",
            "AI_video_local": "LTX (T2V) + CogVideoX (I2V) â€” FREE on local GPU",
            "Cinematic_chain": "AI gen â†’ Real-ESRGAN â†’ RIFE = 5K 60fps cinematic",
            "GSplat": "Photo collection + COLMAP-ready (manual training)",
            "UE5": "Templates in unreal_templates/ (manual install)",
        },
    }
