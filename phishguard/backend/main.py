from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import base64
import hashlib
import hmac
import json
import os
import json
import logging
import secrets
import time
from urllib.parse import urlparse

from db import init_db, get_db, hash_password, verify_password

logger = logging.getLogger("phishguard.health")


def _internal_error(exc: Exception) -> HTTPException:
    """Log diagnostics server-side without disclosing internals to API clients."""
    logger.error("Unhandled API error: %s", exc)
    return HTTPException(status_code=500, detail="Internal server error.")

# Import engines
try:
    from ml.ml_service import predict_url, is_ml_available
    ML_READY = is_ml_available()
except ImportError:
    ML_READY = False
    
try:
    from nlp.nlp_service import analyze_text_with_nlp, is_nlp_available
    NLP_READY = is_nlp_available()
except ImportError:
    NLP_READY = False
    
try:
    from vision_module.vision_service import analyze_image_with_vision, is_vision_available
    VISION_READY = is_vision_available()
except ImportError:
    VISION_READY = False
    
try:
    from domain_module.domain_service import analyze_domain
    DOMAIN_READY = True
except ImportError:
    DOMAIN_READY = False
    
try:
    from ensemble_module.fusion_engine import calculate_ensemble_score
    ENSEMBLE_READY = True
except ImportError:
    ENSEMBLE_READY = False

app = FastAPI(
    title="PhishGuard AI Backend",
    description="Multi-modal AI phishing detection API",
    version="1.0.0"
)

APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY") or os.environ.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(32)


def _issue_auth_token(username: str) -> str:
    """Issue a signed, server-generated auth token for this prototype."""
    issued_at = int(time.time())
    expires_at = issued_at + 3600
    payload = {"sub": username, "iat": issued_at, "exp": expires_at}
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")
    digest = hmac.new(APP_SECRET_KEY.encode("utf-8"), payload_json, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def _validate_auth_token(token: Optional[str]) -> Optional[str]:
    """Return the username if the supplied token is valid and unexpired."""
    if not token or "." not in token:
        return None
    payload_b64, sig_b64 = token.split(".", 1)
    expected_sig = base64.urlsafe_b64encode(
        hmac.new(APP_SECRET_KEY.encode("utf-8"), base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)), hashlib.sha256).digest()
    ).decode("ascii").rstrip("=")
    if not hmac.compare_digest(sig_b64, expected_sig):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
    except Exception:
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None
    uname = payload.get("sub")
    return uname if isinstance(uname, str) and uname else None


@app.on_event("startup")
async def startup_event():
    await init_db()

# Restrict CORS to local dev origins and Chrome extensions
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1):\d+|chrome-extension://.*)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter — Redis-backed when REDIS_URL is set, falls back to in-memory
RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 60))  # seconds
RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 60))  # requests per window
_RATE_LIMIT_STORE: dict = {}  # in-memory fallback

_redis_client = None
try:
    _redis_url = os.environ.get('REDIS_URL')
    if _redis_url:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(_redis_url, decode_responses=True)
except Exception:
    _redis_client = None

async def _check_rate_limit_redis(client_ip: str) -> bool:
    """Returns True if request is allowed. Uses Redis sliding-window counter."""
    key = f'rl:{client_ip}'
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    pipe = _redis_client.pipeline()
    pipe.zremrangebyscore(key, '-inf', window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, RATE_LIMIT_WINDOW + 1)
    results = await pipe.execute()
    count = results[2]
    return count <= RATE_LIMIT_REQUESTS

def _check_rate_limit_memory(client_ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    entries = [t for t in _RATE_LIMIT_STORE.get(client_ip, []) if t > window_start]
    if len(entries) >= RATE_LIMIT_REQUESTS:
        return False
    entries.append(now)
    _RATE_LIMIT_STORE[client_ip] = entries
    return True

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    try:
        client_ip = request.client.host if request.client else 'unknown'
    except Exception:
        client_ip = 'unknown'
    try:
        if _redis_client:
            allowed = await _check_rate_limit_redis(client_ip)
        else:
            allowed = _check_rate_limit_memory(client_ip)
    except Exception:
        allowed = _check_rate_limit_memory(client_ip)
    if not allowed:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    return await call_next(request)


# Admin dependency for protecting sensitive endpoints (use ADMIN_API_KEY env var)
from fastapi import Depends, Header

def require_admin(x_admin_key: str = Header(None, alias="X-ADMIN-KEY")):
    expected = os.environ.get('ADMIN_API_KEY')
    if not expected:
        # No admin key configured; deny by default to avoid accidental exposure
        raise HTTPException(status_code=403, detail='Admin key not configured')
    if x_admin_key != expected:
        raise HTTPException(status_code=403, detail='Forbidden')
    return True

class TextRequest(BaseModel):
    text: str

class DomainRequest(BaseModel):
    url: str

@app.get("/api/health/")
async def health_check():
    database = get_db()
    database_ready = False
    database_reason = "MongoDB unavailable"
    if database is not None:
        try:
            import asyncio
            await asyncio.wait_for(database.command("ping"), timeout=0.3)
            database_ready = True
            database_reason = None
        except Exception as exc:
            logger.warning("MongoDB readiness check failed: %s", exc)

    def readiness(ready: bool, reason: str | None = None) -> dict:
        status = {"ready": ready}
        if reason:
            status["reason"] = reason
        return status

    return {
        "status": "ok",
        "service": "PhishGuard FastAPI",
        "engines": {
            "url_ml": readiness(ML_READY),
            "nlp": readiness(NLP_READY),
            "vision": readiness(VISION_READY),
            "domain": readiness(DOMAIN_READY),
            "xai": readiness(
                ENSEMBLE_READY,
                None if ENSEMBLE_READY else "XAI analysis implementation is unavailable",
            ),
            "hitl": readiness(
                database_ready,
                None if database_ready else database_reason,
            ),
            "database": readiness(database_ready, database_reason),
            "ml_ready": ML_READY,
            "nlp_ready": NLP_READY,
            "vision_ready": VISION_READY,
            "domain_ready": DOMAIN_READY,
            "ensemble_ready": ENSEMBLE_READY
        }
    }

# ─── Global Stats ────────────────────────────────────────────────────────────

@app.get("/api/stats/")
async def api_stats():
    active_engines = sum([ML_READY, NLP_READY, VISION_READY, DOMAIN_READY, ENSEMBLE_READY])
    db = get_db()
    try:
        global_stats = await db.stats.find_one({"_id": "global"}) or {"total_scans": 0, "threats_blocked": 0}
    except Exception:
        global_stats = {"total_scans": 0, "threats_blocked": 0}
    return {
        "total_scans": global_stats.get("total_scans", 0),
        "threats_blocked": global_stats.get("threats_blocked", 0),
        "active_engines": active_engines
    }

# ─── Threat Intelligence Feeds ──────────────────────────────────────────────────

@app.get("/api/ti/status/")
async def api_ti_status():
    """Return status telemetry of Threat Intelligence feeds."""
    from domain_module.ti_integration import get_ti_feed_status
    return get_ti_feed_status()

@app.post("/api/ti/refresh/")
async def api_ti_refresh():
    """Trigger live sync of OpenPhish, PhishTank, and URLhaus feeds into fast O(1) memory index."""
    from domain_module.ti_integration import sync_threat_feeds_now
    return sync_threat_feeds_now()

# ─── Authentication ──────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str

@app.post("/api/login/")
async def login(req: AuthRequest):
    """Authenticate a user and issue a signed auth token."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    user = await db.users.find_one({"username": req.username})
    if user and verify_password(req.password, user.get("password", "")):
        return {"token": _issue_auth_token(req.username), "message": "Login successful"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/api/register/")
async def register(req: AuthRequest):
    """Register a user with a hashed password and return a signed auth token."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    existing = await db.users.find_one({"username": req.username})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    await db.users.insert_one({"username": req.username, "password": hash_password(req.password)})
    return {"token": _issue_auth_token(req.username), "message": "User registered successfully"}


# ─── Input validation helpers ────────────────────────────────────────────────

MAX_URL_LENGTH = 2048
MAX_TEXT_LENGTH = 5000
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}

def _validate_url(url: str) -> None:
    _validate_url_syntax(url)
    try:
        from domain_module.redirect_unwrapper import validate_url_for_fetch
        validate_url_for_fetch(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f'Unsafe URL destination: {exc}') from exc


def _validate_url_syntax(url: str) -> None:
    if not url or len(url) > MAX_URL_LENGTH:
        raise HTTPException(status_code=400, detail=f'URL must be 1–{MAX_URL_LENGTH} characters')
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(status_code=400, detail='URL must use http or https scheme')
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail='URL hostname is required')
    try:
        parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='URL port is invalid') from exc

async def _validate_image(image: UploadFile) -> bytes:
    content_type = (image.content_type or '').lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f'Unsupported image type: {content_type}')
    data = await image.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail='Image exceeds 10 MB limit')
    return data


@app.post("/api/analyze-text/")
async def analyze_text(request: TextRequest):
    if not NLP_READY:
        raise HTTPException(status_code=503, detail="NLP Engine is not available yet.")
    
    if not request.text or len(request.text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f'Invalid text input. Must be 1–{MAX_TEXT_LENGTH} characters.')
        
    try:
        result = analyze_text_with_nlp(request.text)
        return result
    except Exception as e:
        raise _internal_error(e)

@app.post("/api/analyze-vision/")
async def analyze_vision(image: UploadFile = File(...)):
    if not VISION_READY:
        raise HTTPException(status_code=503, detail="Vision Engine is not available yet.")
    try:
        image_bytes = await _validate_image(image)
        result = analyze_image_with_vision(image_bytes)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise _internal_error(e)


@app.post('/api/screenshot/')
async def screenshot_endpoint(url: str = Form(...)):
    """Capture or generate a screenshot for the given URL. Returns JPEG bytes base64-encoded and metadata."""
    from vision_module.screenshot_pipeline import capture_screenshot
    try:
        _validate_url(url)
        res = capture_screenshot(url)
        # Return metadata and base64-encoded image for simplicity
        import base64
        img_b64 = base64.b64encode(res['image_bytes']).decode('ascii') if res.get('image_bytes') else None
        return {
            'original_url': res.get('original_url'),
            'final_url': res.get('final_url'),
            'width': res.get('width'),
            'height': res.get('height'),
            'phash': res.get('phash'),
            'elapsed': res.get('elapsed'),
            'image_base64': img_b64,
            'error': res.get('error')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise _internal_error(e)

@app.get("/api/analyze-domain/")
async def analyze_domain_help():
    return {
        "detail": "This endpoint accepts POST requests with JSON { 'url': 'https://example.com' }. Use POST to analyze a domain."
    }

@app.post("/api/analyze-domain/")
async def analyze_domain_endpoint(request: DomainRequest):
    if not DOMAIN_READY:
        raise HTTPException(status_code=503, detail="Domain Engine is not available yet.")
    _validate_url_syntax(request.url)
        
    try:
        result = analyze_domain(request.url)
        return result
    except Exception as e:
        raise _internal_error(e)

@app.post("/api/unwrap-redirect/")
async def unwrap_redirect_endpoint(request: DomainRequest):
    """
    Dedicated endpoint to unwrap a URL's full redirect chain.
    Returns the original URL, final destination, every hop in between,
    meta-refresh detections, shortener flags, and domain metadata.
    """
    _validate_url_syntax(request.url)
    
    try:
        from domain_module.shortener_expander import is_likely_shortener, expand_short_url
        from domain_module.redirect_unwrapper import unwrap_url
        from domain_module.domain_intelligence import get_domain_metadata, calculate_domain_risk
        
        is_shortener = is_likely_shortener(request.url)
        
        # Unwrap the full chain
        if is_shortener:
            unwrap_result = expand_short_url(request.url)
        else:
            unwrap_result = unwrap_url(request.url)
        
        final_url = unwrap_result.get("final_url", request.url)
        
        blocked = unwrap_result.get("resolution_state") == "blocked"
        if blocked:
            blocked_reason = unwrap_result.get("blocked_reason") or "Unsafe destination blocked by URL validation."
            metadata = {"status": "restricted", "reason": blocked_reason}
            risk = {
                "status": "restricted",
                "reason": blocked_reason,
                "domain_score": None,
                "domain_risk_level": "unavailable",
                "domain_signals": [],
                "metadata": metadata,
            }
        else:
            metadata = get_domain_metadata(final_url)
            risk = calculate_domain_risk(metadata)
        
        # Update stats safely
        try:
            db = get_db()
            if db is not None:
                stats_inc = {"total_scans": 1}
                if risk.get("domain_risk_level") == "phishing":
                    stats_inc["threats_blocked"] = 1
                await db.stats.update_one({"_id": "global"}, {"$inc": stats_inc})
        except Exception:
            pass
        
        return {
            "original_url": request.url,
            "final_url": final_url,
            "is_shortener": is_shortener,
            "redirect_chain": unwrap_result.get("redirect_chain", []),
            "num_redirects": unwrap_result.get("num_redirects", 0),
            "loop_detected": unwrap_result.get("loop_detected", False),
            "suspicious_redirects": unwrap_result.get("suspicious_redirects", False),
            "resolution_state": unwrap_result.get("resolution_state", "failed"),
            "blocked_reason": unwrap_result.get("blocked_reason"),
            "status": "restricted" if blocked else "available",
            "has_meta_refresh": any(
                hop.get("note") == "meta_refresh" 
                for hop in unwrap_result.get("redirect_chain", [])
            ),
            "domain_risk": risk,
            "domain_metadata": metadata,
            "errors": unwrap_result.get("errors", []),
        }
    except Exception as e:
        raise _internal_error(e)

# Registry endpoints
@app.get('/api/registry/models/')
async def api_list_models():
    try:
        from registry.registry import list_models
        return list_models()
    except Exception as e:
        raise _internal_error(e)


@app.get('/api/registry/models/{name}/latest')
async def api_get_latest(name: str):
    try:
        from registry.registry import get_model_metadata, get_latest_model_path, get_artifact_path
        meta = get_model_metadata(name)
        path = get_latest_model_path(name)
        artifact = get_artifact_path(name)
        size = None
        if artifact and os.path.exists(artifact):
            try:
                size = os.path.getsize(artifact)
            except Exception:
                size = None
        return { 'metadata': meta, 'artifact_path': path, 'artifact_size': size }
    except Exception as e:
        raise _internal_error(e)


@app.get('/api/registry/models/{name}/versions')
async def api_list_versions(name: str):
    try:
        from registry.registry import list_models, get_model_metadata, get_artifact_path
        versions_map = list_models(name)
        versions = versions_map.get(name, [])
        out = []
        for v in versions:
            meta = get_model_metadata(name, version=v)
            artifact = get_artifact_path(name, version=v)
            size = None
            if artifact and os.path.exists(artifact):
                try:
                    size = os.path.getsize(artifact)
                except Exception:
                    size = None
            out.append({'version': v, 'metadata': meta, 'artifact': os.path.basename(artifact) if artifact else None, 'size': size})
        return {'name': name, 'versions': out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/registry/models/{name}/versions/{version}/artifact', dependencies=[Depends(require_admin)])
async def api_get_artifact(name: str, version: str):
    """Download a model artifact file for inspection. Returns 404 if not found."""
    try:
        from registry.registry import get_artifact_path
        artifact = get_artifact_path(name, version=version)
        if not artifact or not os.path.exists(artifact):
            raise HTTPException(status_code=404, detail='Artifact not found')
        # Basic safety: ensure artifact is inside registry models directory
        registry_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'registry', 'models'))
        artifact_abs = os.path.abspath(artifact)
        if not artifact_abs.startswith(registry_root):
            raise HTTPException(status_code=400, detail='Invalid artifact path')
        return FileResponse(artifact_abs, media_type='application/octet-stream', filename=os.path.basename(artifact_abs))
    except HTTPException:
        raise
    except Exception as e:
        raise _internal_error(e)


@app.post('/api/registry/promote', dependencies=[Depends(require_admin)])
async def api_promote_model(name: str = Form(...), version: Optional[str] = Form(None)):
    """Promote a registry model version to the active meta-learner used by the ensemble.
    POST form fields: name (required), version (optional — defaults to latest)
    Returns JSON: { "promoted_to": <path> }
    """
    try:
        from registry.registry import promote_model
        dest = promote_model(name, version=version)
        if not dest:
            raise HTTPException(status_code=404, detail='Model/version not found')
        return { 'promoted_to': dest }
    except HTTPException:
        raise
    except Exception as e:
        raise _internal_error(e)


@app.post("/api/analyze-ensemble/")
async def analyze_ensemble(
    url: str = Form(...),
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    if not ENSEMBLE_READY:
        raise HTTPException(status_code=503, detail="Ensemble Engine is not available yet.")
    _validate_url_syntax(url)
    if text and len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f'Text exceeds {MAX_TEXT_LENGTH} character limit')
    vision_image_bytes = None
    vision_status = None
    thumbnail_b64 = None
    if image:
        image_bytes = await _validate_image(image)
        vision_image_bytes = image_bytes
        vision_status = {"status": "available", "applicable": True, "input_scope": "submitted_image"}
    else:
        try:
            from vision_module.screenshot_pipeline import SCREENSHOT_ENABLED, capture_screenshot

            # When screenshot capture is disabled, set vision_status immediately and skip the call.
            if not SCREENSHOT_ENABLED:
                vision_status = {
                    "status": "unavailable",
                    "reason": "Automatic screenshot acquisition is disabled (SCREENSHOT_ENABLED=False).",
                    "applicable": False,
                    "input_scope": "not_collected",
                }
            else:
                # Screenshot enabled — check for SSRF block before proceeding.
                try:
                    from domain_module.redirect_unwrapper import validate_url_for_fetch
                    validate_url_for_fetch(url)
                except ValueError as exc:
                    vision_status = {
                        "status": "restricted",
                        "reason": f"Screenshot acquisition blocked for unsafe network destination: {exc}",
                        "applicable": True,
                    }

            if vision_status is None:
                ss_res = capture_screenshot(url)
                thumb = ss_res.get('thumb')
                thumbnail_b64 = base64.b64encode(thumb).decode('ascii') if thumb else None
                if ss_res.get('is_real_screenshot'):
                    vision_image_bytes = ss_res.get('image_bytes')
                    vision_status = {"status": "available", "applicable": True, "input_scope": "captured_screenshot"}
                elif ss_res.get('error'):
                    vision_status = {
                        "status": "error",
                        "reason": str(ss_res['error']),
                        "applicable": SCREENSHOT_ENABLED,
                        "input_scope": "captured_screenshot" if SCREENSHOT_ENABLED else "not_collected",
                    }
                else:
                    vision_status = {
                        "status": "unavailable",
                        "reason": "Automatic screenshot acquisition did not produce a real screenshot.",
                        "applicable": SCREENSHOT_ENABLED,
                        "input_scope": "not_collected",
                    }
        except Exception as exc:
            vision_status = {
                "status": "error",
                "reason": str(exc),
                "applicable": bool(os.environ.get('SCREENSHOT_ENABLED') in ('1', 'true', 'True')),
                "input_scope": "not_collected",
            }

    try:
        result = await calculate_ensemble_score(
            url,
            text=text,
            image_bytes=vision_image_bytes,
            vision_status=vision_status,
        )
        # Attach thumbnail if we generated one server-side
        if thumbnail_b64:
            result['thumbnail_base64'] = thumbnail_b64
            
        # Update global stats safely
        try:
            db = get_db()
            if db is not None:
                stats_inc = {"total_scans": 1}
                if result.get('ensemble_risk_level') == 'phishing':
                    stats_inc["threats_blocked"] = 1
                await db.stats.update_one({"_id": "global"}, {"$inc": stats_inc})
        except Exception as stats_err:
            pass
            
        return result
    except Exception as e:
        raise _internal_error(e)

# ─── Compatibility Scan Endpoint ────────────────────────────────────────────────────────

@app.get("/api/scan/")
async def scan_help_get():
    return {
        "detail": "This endpoint accepts POST (form) with field 'url'. Use POST to scan URLs. Example: curl -X POST -F 'url=https://example.com' http://127.0.0.1:8000/api/scan/"
    }

@app.post("/api/scan/")
async def scan(
    url: str = Form(...),
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    """Legacy endpoint kept for the browser extension.
    It forwards the request to the ensemble analyzer and returns the same payload.
    """
    return await analyze_ensemble(url=url, text=text, image=image)


# ─── Human-in-the-Loop (HITL) Endpoints ─────────────────────────────────────

@app.post("/api/hitl/submit/")
async def api_hitl_submit(
    url: str = Form(...),
    user_label: str = Form(...),
    evidence_snapshot: Optional[str] = Form(None),
):
    _validate_url(url)
    if user_label not in ("phishing", "safe", "suspicious"):
        raise HTTPException(status_code=400, detail="Invalid user label. Must be phishing, safe, or suspicious.")
    from detector.hitl_service import submit_url
    snapshot = None
    if evidence_snapshot:
        try:
            parsed_snapshot = json.loads(evidence_snapshot)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid evidence snapshot JSON.")
        if not isinstance(parsed_snapshot, dict):
            raise HTTPException(status_code=400, detail="Evidence snapshot must be an object.")
        snapshot = parsed_snapshot
    return await submit_url(url, user_label, snapshot)

@app.get("/api/hitl/pending/", dependencies=[Depends(require_admin)])
async def api_hitl_pending():
    from detector.hitl_service import get_pending_urls
    return await get_pending_urls()

@app.post("/api/hitl/claim/", dependencies=[Depends(require_admin)])
async def api_hitl_claim(
    url: str = Form(...),
    reviewer: Optional[str] = Form("admin"),
):
    _validate_url(url)
    from detector.hitl_service import set_case_status
    try:
        result = await set_case_status(url, "under_review", reviewer or "admin")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="HITL case not found")
    return result

@app.post("/api/hitl/resolve/", dependencies=[Depends(require_admin)])
async def api_hitl_resolve(
    url: str = Form(...),
    final_label: str = Form(...),
    reviewer: Optional[str] = Form("admin"),
    comment: Optional[str] = Form(None),
):
    _validate_url(url)
    if final_label not in ("phishing", "safe", "suspicious", "needs_investigation"):
        raise HTTPException(
            status_code=400,
            detail="Invalid label. Must be phishing, safe, suspicious, or needs_investigation.",
        )
    from detector.hitl_service import resolve_url
    try:
        res = await resolve_url(url, final_label, reviewer or "admin", comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not res:
        raise HTTPException(status_code=404, detail="URL not found in HITL queue")
    return res

@app.get("/api/hitl/audit-logs/", dependencies=[Depends(require_admin)])
async def api_hitl_audit_logs():
    from detector.hitl_service import get_audit_logs
    return await get_audit_logs()
