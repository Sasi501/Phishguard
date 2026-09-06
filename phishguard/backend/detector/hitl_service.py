"""
PhishGuard — Human-in-the-Loop (HITL) Service
Manages user-submitted URL labeling, admin resolutions, and security audit logging.
Now backed by MongoDB!
"""
import time
from typing import Dict, Any, List, Optional
from db import get_db

async def submit_url(url: str, user_label: str) -> Dict[str, Any]:
    """Submit a URL for review."""
    db = get_db()
    queue = db.hitl_queue
    
    # Check if already exists in queue (pending)
    existing = await queue.find_one({"url": url, "status": "pending"})
    if existing:
        existing["_id"] = str(existing["_id"])
        return existing
            
    new_item = {
        "url": url,
        "user_label": user_label,
        "final_label": "unknown",
        "status": "pending",
        "created_at": time.time(),
        "updated_at": time.time(),
        "reviewer": None
    }
    
    result = await queue.insert_one(new_item)
    new_item["_id"] = str(result.inserted_id)
    return new_item

async def get_pending_urls() -> List[Dict[str, Any]]:
    """Get all pending URLs."""
    db = get_db()
    cursor = db.hitl_queue.find({"status": "pending"})
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results

async def resolve_url(url: str, final_label: str, reviewer: str) -> Optional[Dict[str, Any]]:
    """Resolve a URL labeling request."""
    db = get_db()
    
    # Update or insert into hitl_queue
    now = time.time()
    result = await db.hitl_queue.find_one_and_update(
        {"url": url},
        {
            "$set": {
                "status": "resolved",
                "final_label": final_label,
                "reviewer": reviewer,
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
    
    if result:
        result["_id"] = str(result["_id"])
        
    # Write audit log
    await db.hitl_audit.insert_one({
        "url": url,
        "action": f"Classified as {final_label}",
        "reviewer": reviewer,
        "timestamp": now
    })
    
    return result

async def get_audit_logs() -> List[Dict[str, Any]]:
    """Get all audit logs."""
    db = get_db()
    cursor = db.hitl_audit.find().sort("timestamp", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results

async def check_hitl_override(url: str) -> Optional[Dict[str, Any]]:
    """Check if URL has a resolved human override."""
    db = get_db()
    item = await db.hitl_queue.find_one({"url": url, "status": "resolved"})
    
    if item:
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
