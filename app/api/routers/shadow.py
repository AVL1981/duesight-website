import asyncio
import os
import logging
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger("api.shadow")
router = APIRouter()

_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$"
)
_COMPANY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,&'()_-]{1,120}$")
_KVK_RE = re.compile(r"^\d{8}$")
_DANGEROUS_CHARS_RE = re.compile(r"[;&|`$<>\\\r\n]")


class ShadowRequest(BaseModel):
    target: str
    kvk_number: str = ""
    sandbox_mode: bool = False

class ShadowResponse(BaseModel):
    status: str
    target: str
    message: str
    job_id: str


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return max(1, int(value))
    except ValueError:
        logger.warning("Invalid integer env %s=%r; using %s", name, value, default)
        return default


def normalize_kvk_number(value: str) -> str:
    compact = re.sub(r"\s+", "", value or "")
    if not compact:
        return ""
    if not _KVK_RE.fullmatch(compact):
        raise HTTPException(status_code=400, detail="Invalid kvk_number: expected 8 digits.")
    return compact


def normalize_shadow_target(value: str) -> str:
    raw = (value or "").strip()
    if len(raw) < 2 or len(raw) > 253:
        raise HTTPException(status_code=400, detail="Invalid target length.")
    if _DANGEROUS_CHARS_RE.search(raw):
        raise HTTPException(status_code=400, detail="Invalid target characters.")

    if "://" in raw:
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise HTTPException(status_code=400, detail="Target URL must be http(s).")
        if parsed.username or parsed.password:
            raise HTTPException(status_code=400, detail="Target URL credentials are not allowed.")
        host = parsed.hostname.lower()
        if not _DOMAIN_RE.fullmatch(host):
            raise HTTPException(status_code=400, detail="Target URL host is invalid.")
        return host

    if " " not in raw and _DOMAIN_RE.fullmatch(raw):
        return raw.lower()

    if not _COMPANY_RE.fullmatch(raw):
        raise HTTPException(status_code=400, detail="Target must be a domain, URL, or company name.")
    return re.sub(r"\s+", " ", raw)


def resolve_shadow_script() -> tuple[Path, Path]:
    current_dir = Path.cwd()
    agent_dir = current_dir.parent / "duesight-agent"
    script_path = agent_dir / "shadow_crawler.py"

    if script_path.exists():
        return agent_dir, script_path

    fallback_agent_dir = Path(r"C:\Users\arian\OneDrive\Desktop\DueSight website\duesight-agent")
    fallback_script_path = fallback_agent_dir / "shadow_crawler.py"
    if fallback_script_path.exists():
        return fallback_agent_dir, fallback_script_path

    raise HTTPException(
        status_code=500,
        detail="Terminal error: shadow_crawler.py missing from expected paths.",
    )


def build_shadow_command(script_path: Path, target: str, sandbox: bool) -> list[str]:
    if sandbox:
        if not _env_flag("DUESIGHT_SHADOW_DOCKER_ENABLED", default=False):
            raise HTTPException(status_code=403, detail="Shadow Docker mode is disabled.")
        return [
            "docker",
            "run",
            "--rm",
            "--env",
            "OLLAMA_URL=http://host.docker.internal:11434/api/generate",
            "shadow_crawler",
            "--target",
            target,
        ]

    return [sys.executable, str(script_path), "--target", target]


@router.post("/infiltrate", response_model=ShadowResponse)
async def trigger_shadow_infilration(req: ShadowRequest, background_tasks: BackgroundTasks):
    """
    Admin-only endpoint for the shadow crawler.

    The crawler is disabled by default. Enable it explicitly with
    DUESIGHT_SHADOW_ENABLED=true in a controlled environment.
    """
    if not _env_flag("DUESIGHT_SHADOW_ENABLED", default=False):
        raise HTTPException(status_code=503, detail="Shadow crawler is disabled.")

    job_id = f"shdw_{os.urandom(4).hex()}"
    kvk_number = normalize_kvk_number(req.kvk_number)
    target = kvk_number or normalize_shadow_target(req.target)
    agent_dir, script_path = resolve_shadow_script()
    timeout_seconds = _env_int("DUESIGHT_SHADOW_TIMEOUT_SECONDS", default=180)
    cmd = build_shadow_command(script_path, target, req.sandbox_mode)

    async def _run_stealth_crawler(command: list[str], safe_target: str, w_dir: Path):
        logger.info("[%s] Starting shadow crawler for target=%s", job_id, safe_target)

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(w_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                logger.error("[%s] Shadow crawler timed out after %ss", job_id, timeout_seconds)
                return

            if process.returncode == 0:
                logger.info("[%s] Shadow extraction succeeded", job_id)
                logger.debug(stdout.decode()[:1000])
            else:
                logger.error("[%s] Shadow extraction failed. Code: %s", job_id, process.returncode)
                logger.error(stderr.decode())

        except Exception as e:
            logger.error("[%s] Subprocess execution crashed: %s", job_id, str(e))

    background_tasks.add_task(
        _run_stealth_crawler,
        cmd,
        target,
        agent_dir
    )

    return ShadowResponse(
        status="active",
        target=target,
        message="Shadow crawler job accepted.",
        job_id=job_id
    )
