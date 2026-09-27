"""
PhishGuard — Human-in-the-Loop (HITL) Service
Manages user-submitted URL labeling, admin resolutions, and security audit logging.
Now backed by MongoDB!
"""
import inspect
import time
from typing import Dict, Any, List, Optional
from db import get_db

REVIEW_STATUSES = {"pending", "under_review", "resolved", "needs_investigation"}
FINAL_LABELS = {"phishing", "safe", "suspicious"}
SNAPSHOT_FIELDS = (
    "captured_at",
    "source",
    "original_url",
    "final_url",
    "ensemble_score",
    "ensemble_risk_level",
    "engine_signals",
    "xai",
    "domain_intelligence",
    "threat_intelligence",
    "redirect_analysis",
)


def _normalize_evidence_snapshot(snapshot: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return None
    normalized = {
        key: snapshot[key]
        for key in SNAPSHOT_FIELDS
        if key in snapshot and snapshot[key] is not None
    }
    if not normalized:
        return None
    normalized.setdefault("captured_at", time.time())
    normalized.setdefault("source", "ensemble_analysis")
    return normalized


def _normalize_case(document: Dict[str, Any]) -> Dict[str, Any]:
    """Expose a stable analyst case shape while preserving legacy fields."""
    case = dict(document)
    identifier = str(case.get("_id", case.get("case_id", "")))
    case.pop("_id", None)
    case["case_id"] = identifier
    case.setdefault("submitted_at", case.get("created_at"))
    case.setdefault("current_ai_verdict", case.get("ai_verdict"))
    case.setdefault("ensemble_score", case.get("ai_score"))
    case.setdefault("risk_level", case.get("ai_risk_level"))
    case.setdefault("engine_signals", None)
    case.setdefault("xai_explanation", None)
    case.setdefault("url_anatomy", None)
    case.setdefault("domain_intelligence", None)
    case.setdefault("threat_intelligence", None)
    case.setdefault("redirect_analysis", None)
    case.setdefault("analyst_verdict", case.get("final_label"))
    case.setdefault("analyst_comment", case.get("comment"))
    case.setdefault("review_timestamp", case.get("reviewed_at"))
    case.setdefault("case_status", case.get("status", "pending"))
    return case


async def _write_audit(db: Any, url: str, action: str, reviewer: Optional[str],
                       case_id: Optional[str] = None, comment: Optional[str] = None) -> None:
    record = {
        "url": url,
        "action": action,
        "reviewer": reviewer,
        "timestamp": time.time(),
    }
    if case_id:
        record["case_id"] = case_id
    if comment:
        record["comment"] = comment
    insert = getattr(db.hitl_audit, "insert_one", None)
    if insert:
        result = insert(record)
        if inspect.isawaitable(result):
            await result


async def submit_url(
    url: str,
    user_label: str,
    evidence_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Submit a URL for review."""
    db = get_db()
    queue = db.hitl_queue
    
    # Check if already exists in queue (pending)
    existing = await queue.find_one({"url": url, "status": "pending"})
    if existing:
        return _normalize_case(existing)
            
    new_item = {
        "url": url,
        "user_label": user_label,
        "final_label": "unknown",
        "status": "pending",
        "created_at": time.time(),
        "updated_at": time.time(),
        "reviewer": None,
        "submitted_at": time.time(),
        "case_status": "pending",
        "analyst_verdict": None,
        "analyst_comment": None,
        "review_timestamp": None,
    }
    normalized_snapshot = _normalize_evidence_snapshot(evidence_snapshot)
    if normalized_snapshot:
        new_item["evidence_snapshot"] = normalized_snapshot
    
    result = await queue.insert_one(new_item)
    new_item["_id"] = str(result.inserted_id)
    await _write_audit(db, url, "Case submitted for review", None, str(result.inserted_id))
    return _normalize_case(new_item)

async def get_pending_urls() -> List[Dict[str, Any]]:
    """Get queued cases that still require analyst action."""
    db = get_db()
    cursor = db.hitl_queue.find({"status": {"$in": ["pending", "under_review"]}})
    results = []
    async for doc in cursor:
        results.append(_normalize_case(doc))
    return results

async def set_case_status(url: str, status: str, reviewer: str) -> Optional[Dict[str, Any]]:
    """Move a case into an explicit workflow state without changing its verdict."""
    if status not in {"under_review", "pending"}:
        raise ValueError("Unsupported HITL workflow status")
    db = get_db()
    now = time.time()
    result = await db.hitl_queue.find_one_and_update(
        {"url": url},
        {"$set": {"status": status, "case_status": status, "reviewer": reviewer, "updated_at": now}},
        return_document=True,
    )
    if not result:
        return None
    case = _normalize_case(result)
    await _write_audit(db, url, "Case moved to " + status, reviewer, case.get("case_id"))
    return case


async def resolve_url(
    url: str,
    final_label: str,
    reviewer: str,
    comment: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Resolve a URL labeling request."""
    if final_label not in FINAL_LABELS | {"needs_investigation"}:
        raise ValueError("Unsupported HITL verdict")
    db = get_db()
    
    # Update or insert into hitl_queue
    now = time.time()
    case_status = "needs_investigation" if final_label == "needs_investigation" else "resolved"
    analyst_verdict = None if final_label == "needs_investigation" else final_label
    result = await db.hitl_queue.find_one_and_update(
        {"url": url},
        {
            "$set": {
                "status": case_status,
                "case_status": case_status,
                "final_label": final_label,
                "analyst_verdict": analyst_verdict,
                "analyst_comment": comment,
                "reviewer": reviewer,
                "review_timestamp": now,
                "reviewed_at": now,
                "updated_at": now
            },
            "$setOnInsert": {
                "user_label": final_label,
                "created_at": now
            }
        },
        upsert=True,
        return_document=True
    )

    if not result:
        return None

    case = _normalize_case(result)
    case.update({
        "final_label": final_label,
        "analyst_verdict": analyst_verdict,
        "analyst_comment": comment,
        "reviewer": reviewer,
        "review_timestamp": now,
        "case_status": case_status,
        "status": case_status,
    })
    await _write_audit(
        db,
        url,
        f"Analyst verdict: {final_label}",
        reviewer,
        case.get("case_id"),
        comment,
    )
    return case

async def get_audit_logs() -> List[Dict[str, Any]]:
    """Get all audit logs."""
    db = get_db()
    cursor = db.hitl_audit.find().sort("timestamp", -1)
    results = []
    async for doc in cursor:
        results.append(_normalize_case(doc))
    return results

async def check_hitl_override(url: str) -> Optional[Dict[str, Any]]:
    """Check if URL has a resolved human override."""
    db = get_db()
    item = await db.hitl_queue.find_one({"url": url, "status": "resolved"})
    
    if item and item.get("final_label") in FINAL_LABELS:
        risk = item["final_label"]
        confidence = 100.0
        reasons = [f"Human reviewed override: marked as {risk}"]
        
        # Map risk level
        if risk == "phishing":
            score = 100.0
            summary = "This website has been manually identified as phishing by security administrators."
        elif risk == "suspicious":
            score = 50.0
            summary = "This website has been flagged as suspicious by security administrators."
        else:
            score = 0.0
            summary = "This website has been manually verified as safe by security administrators."
            
        return {
            "ensemble_score_percent": score,
            "confidence": confidence,
            "ensemble_risk_level": risk,
            "xai_summary": summary,
            "reasons": reasons,
            "individual_scores_percent": {
                "ml": score,
                "nlp": score,
                "vision": score,
                "domain": score
            },
            "hitl_override": True
        }
    return None
