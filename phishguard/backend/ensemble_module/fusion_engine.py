import logging
import os
import joblib
import numpy as np
from google import genai

# Import all modules
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

ENSEMBLE_DIR = os.path.dirname(os.path.abspath(__file__))
META_LEARNER_PATH = os.path.join(ENSEMBLE_DIR, "models", "meta_learner.pkl")

def get_meta_learner():
    # Prefer a model from the local registry if available (registry is a prototype under backend/registry)
    try:
        from registry.registry import get_latest_model_path
        registry_path = get_latest_model_path('meta_learner')
        if registry_path and os.path.exists(registry_path):
            try:
                return joblib.load(registry_path)
            except Exception:
                # Fall through to file-system meta learner
                pass
    except Exception:
        # Registry not available in this environment
        pass

    if os.path.exists(META_LEARNER_PATH):
        try:
            return joblib.load(META_LEARNER_PATH)
        except Exception:
            return None
    return None

_KEY_INDEX = 0

def get_api_key_pool() -> list:
    keys_str = os.environ.get("GEMINI_API_KEYS", "").strip()
    if keys_str:
        keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        if keys:
            return keys
    single_key = os.environ.get("GEMINI_API_KEY", "").strip()
    return [single_key] if single_key else []

def generate_xai_summary(reasons: list, shap_nlp: list, shap_url: list, gradcam_vision: list, url: str, confidence: float) -> str:
    """Use Gemini LLM to summarize the reasons and technical XAI features.
    Rotates through GEMINI_API_KEYS pool with automatic failover on rate-limit/error.
    """
    global _KEY_INDEX
    keys = get_api_key_pool()
    formatted_fallback = ". ".join([r.strip().rstrip('.') for r in reasons if r.strip()]) + "." if reasons else ""
    if not keys or not reasons:
        return formatted_fallback

    # Build rich context string for the LLM
    context = f"Target URL: {url}\nConfidence of Phishing: {confidence}%\n\nGeneral Reasons:\n"
    context += "\n".join(f"- {r}" for r in reasons) + "\n\n"
    
    if shap_url:
        context += "URL Features (SHAP):\n" + "\n".join(f"- {f['feature']} (impact: {f['shap_value']})" for f in shap_url) + "\n\n"
    if shap_nlp:
        context += "Text Tokens (SHAP):\n" + "\n".join(f"- {f['feature']} (impact: {f['shap_value']})" for f in shap_nlp) + "\n\n"
    if gradcam_vision:
        context += "Visual Regions (Grad-CAM):\n" + "\n".join(f"- {f['feature']} (activation: {f['gradcam_activation']})" for f in gradcam_vision) + "\n\n"

    prompt = (
        "You are a senior AI cybersecurity analyst. Explain to a non-technical end user why the target page is a phishing scam. "
        "Use the provided technical XAI signals (SHAP for text/URL features, Grad-CAM for visual features). "
        "Write exactly ONE clear, readable paragraph. Do not use overly dense jargon, but do mention exactly which words, URL parts, or visual elements triggered the detection.\n\n"
        f"Technical Context:\n{context}"
    )

    num_keys = len(keys)
    start_idx = _KEY_INDEX % num_keys

    for attempt in range(num_keys):
        current_idx = (start_idx + attempt) % num_keys
        target_key = keys[current_idx]

        def _call_gemini(key_to_use):
            client = genai.Client(api_key=key_to_use)
            response = client.models.generate_content(
                model='gemini-3.1-pro-preview',
                contents=prompt,
            )
            return response.text

        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini, target_key)
                result = future.result(timeout=15)
                # Success: Rotate to next key for next request
                _KEY_INDEX = (current_idx + 1) % num_keys
                return result
        except Exception as e:
            logging.warning(f"LLM Key Pool: Key #{current_idx + 1} failed ({e}). Failover to next key in pool...")

    logging.error("LLM Summary Error: All API keys in pool failed or timed out.")
    return formatted_fallback

async def calculate_ensemble_score(url: str, text: str = None, image_bytes: bytes = None) -> dict:
    """
    Fuses outputs from URL ML, NLP, Vision, and Domain Intelligence into a single score using Meta-Learner.
    No whitelists — purely engine-driven classification.
    """
    try:
        from detector.hitl_service import check_hitl_override
        override = await check_hitl_override(url)
        if override:
            return override
    except Exception:
        pass

    scores = {'ml': 0.0, 'nlp': 0.0, 'vision': 0.0, 'domain': 0.0}
    reasons = []
    
    # XAI Features
    shap_url = []
    shap_nlp = []
    gradcam_vision = []
    
    # 1. URL ML Engine (Module 1)
    if ML_READY and url:
        try:
            ml_res = predict_url(url)
            if ml_res:
                scores['ml'] = ml_res['ml_score']
                if ml_res['ml_score'] > 0.5:
                    reasons.append(f"URL analysis flagged high risk ({ml_res['ml_score']:.2f})")
                if 'shap_features' in ml_res:
                    shap_url = ml_res['shap_features']
        except Exception as e:
            logging.error(f"ML module error: {e}")

    # 2. Domain Intelligence & Redirects (Module 4)
    domain_age_days = None
    if DOMAIN_READY and url:
        try:
            domain_res = analyze_domain(url)
            if domain_res:
                scores['domain'] = domain_res['domain_score']
                domain_age_days = domain_res.get('metadata', {}).get('age_days')
                for sig in domain_res.get('domain_signals', []):
                    reasons.append(f"Domain flagged for {sig.replace('_', ' ')}")
        except Exception as e:
            logging.error(f"Domain module error: {e}")
            
    # 3. Vision Engine (Module 3)
    if VISION_READY and image_bytes:
        try:
            vision_res = analyze_image_with_vision(image_bytes)
            if vision_res:
                scores['vision'] = vision_res['vision_score']
                if vision_res['vision_score'] > 0.5:
                    reasons.append(f"Visual layout imitation detected ({vision_res['vision_score']:.2f})")
                if 'gradcam_features' in vision_res:
                    gradcam_vision = vision_res['gradcam_features']
        except Exception as e:
            logging.error(f"Vision module error: {e}")
            
    # 4. NLP Engine (Module 2)
    if NLP_READY and text:
        try:
            nlp_res = analyze_text_with_nlp(text)
            if nlp_res:
                scores['nlp'] = nlp_res['nlp_score']
                keywords = nlp_res.get('suspicious_keywords', [])
                if keywords:
                    reasons.append(f"Urgency/phishing keywords found: {', '.join(keywords)}")
                if 'shap_features' in nlp_res:
                    shap_nlp = nlp_res['shap_features']
        except Exception as e:
            logging.error(f"NLP module error: {e}")

    # Compute Meta-Learner Prediction
    clf = get_meta_learner()
    if clf:
        X = np.array([[scores['ml'], scores['nlp'], scores['vision'], scores['domain']]])
        final_score = clf.predict_proba(X)[0][1] # Probability of Phishing (class 1)
    else:
        # Multi-Modal Correlation:
        # If the domain is highly established (e.g., > 2 years old), structural ML anomalies 
        # (like deep Wikipedia paths or subdomains) are likely benign false positives.
        if domain_age_days is not None:
            if domain_age_days > 1825: # > 5 years old
                scores['ml'] = scores['ml'] * 0.05
                reasons = [r for r in reasons if "URL analysis flagged" not in r]
            elif domain_age_days > 730: # > 2 years old
                scores['ml'] = scores['ml'] * 0.20
                if scores['ml'] < 0.5:
                    reasons = [r for r in reasons if "URL analysis flagged" not in r]
            elif domain_age_days > 365: # > 1 year old
                scores['ml'] = scores['ml'] * 0.50
                if scores['ml'] < 0.5:
                    reasons = [r for r in reasons if "URL analysis flagged" not in r]

        # Weighted average of ALL 4 engines (not just active ones).
        # This ensures that when 3 engines say safe (0%) and 1 says moderate risk,
        # the final score reflects reality instead of inflating the single engine's score.
        # Weights: ML=0.35, Domain=0.30, Vision=0.20, NLP=0.15
        weights = {'ml': 0.35, 'nlp': 0.15, 'vision': 0.20, 'domain': 0.30}
        final_score = sum(scores[k] * weights[k] for k in scores)
    
    # Classify
    if final_score >= 0.7:
        risk_level = "phishing"
    elif final_score >= 0.35:
        risk_level = "suspicious"
    else:
        risk_level = "safe"
        if not reasons:
            reasons.append("All provided signals appear safe.")
            
    # XAI LLM Summary for High/Medium risk
    xai_summary = ""
    if risk_level in ["phishing", "suspicious"]:
        xai_summary = generate_xai_summary(reasons, shap_nlp, shap_url, gradcam_vision, url, round(final_score * 100, 2))
            
    return {
        "ensemble_score_percent": round(final_score * 100, 2),
        "confidence": round(final_score * 100, 2),
        "ensemble_risk_level": risk_level,
        "xai_summary": xai_summary,
        "reasons": reasons,
        "individual_scores_percent": {k: round(v * 100, 2) for k, v in scores.items()}
    }
