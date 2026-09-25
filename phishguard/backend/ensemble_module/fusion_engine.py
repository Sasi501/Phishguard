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


def _risk_level_from_score(score: float) -> str:
    if score >= 0.7:
        return "phishing"
    if score >= 0.35:
        return "suspicious"
    return "safe"


def _severity_for_score(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _build_xai_summary(risk_level: str, risk_factors: list, safety_factors: list) -> str:
    if risk_level == "safe":
        if safety_factors:
            ti_factor = next((f for f in safety_factors if 'threat-intelligence' in (f.get('title', '') + ' ' + f.get('description', '')).lower() or 'no match' in (f.get('description', '') or '').lower()), None)
            if ti_factor and ti_factor.get('description'):
                return f"PhishGuard found no strong phishing indicators in the available analysis. {ti_factor['description']}"
            support = safety_factors[0].get('description', '')
            if support:
                return f"PhishGuard found no strong phishing indicators in the available analysis. {support}"
        return "PhishGuard found no strong phishing indicators in the available analysis."

    if risk_factors:
        reasons = [factor.get('description', '').rstrip('.') for factor in risk_factors[:2] if factor.get('description')]
        if reasons:
            return f"PhishGuard classified this target as {risk_level} because the available evidence showed {'. '.join(reasons)}."
    return f"PhishGuard classified this target as {risk_level} based on the available engine evidence."


def _signal_from_engine_score(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.35:
        return "medium"
    return "safe"


def _build_engine_signals(scores: dict, domain_result: dict, threat_result: dict | None = None) -> list:
    engine_map = {
        'ml': 'URL Intelligence',
        'nlp': 'Text Intelligence',
        'vision': 'Visual Intelligence',
        'domain': 'Domain Intelligence',
    }
    signals = []
    for key, label in engine_map.items():
        value = float(scores.get(key, 0.0) or 0.0)
        signals.append({
            'engine': label,
            'score': round(value * 100, 2),
            'risk_level': _signal_from_engine_score(value),
            'source': {
                'ml': 'url_ml',
                'nlp': 'nlp',
                'vision': 'vision',
                'domain': 'domain_intelligence',
            }[key],
            'score_type': 'engine_signal',
            'url_scope': {
                'ml': 'original_url',
                'nlp': 'submitted_text',
                'vision': 'submitted_image',
                'domain': 'final_url',
            }[key],
        })

    ti_hits = 0
    ti_sources = []
    if threat_result:
        ti_hits = int(threat_result.get('ti_hits', 0) or 0)
        ti_sources = threat_result.get('ti_sources', []) or []
    elif domain_result:
        ti_details = domain_result.get('ti_details') or domain_result.get('metadata', {}).get('ti_summary') or {}
        ti_hits = int(ti_details.get('ti_hits', 0) or 0)
        ti_sources = ti_details.get('ti_sources', []) or []

    signals.append({
        'engine': 'Threat Intelligence',
        'score': 100.0 if ti_hits > 0 else 0.0,
        'risk_level': 'phishing' if ti_hits > 0 else 'safe',
        'match_status': 'MATCH' if ti_hits > 0 else 'NO MATCH',
        'sources': ti_sources,
        'source': 'threat_intelligence',
        'score_type': 'match_signal',
        'url_scope': 'final_url',
    })

    return signals


def _build_feature_importance(ml_result: dict | None, nlp_result: dict | None, vision_result: dict | None) -> list:
    features = []
    for label, source, payload in [
        ('url', 'url', ml_result.get('shap_features') if ml_result else []),
        ('text', 'text', nlp_result.get('shap_features') if nlp_result else []),
        ('vision', 'vision', vision_result.get('gradcam_features') if vision_result else []),
    ]:
        for item in payload or []:
            if label == 'vision':
                feature_name = item.get('feature')
                impact = float(item.get('gradcam_activation', 0) or 0)
                value = item.get('feature')
            else:
                feature_name = item.get('feature')
                impact = float(item.get('shap_value', item.get('importance', 0)) or 0)
                value = item.get('value')
            if not feature_name:
                continue
            features.append({
                'feature': feature_name,
                'value': value,
                'impact': round(impact, 4),
                'source': source,
            })
    return sorted(features, key=lambda f: abs(float(f['impact'] or 0)), reverse=True)[:8]


def _build_xai_structured(
    url: str,
    risk_level: str,
    scores: dict,
    ml_result: dict | None,
    nlp_result: dict | None,
    vision_result: dict | None,
    domain_result: dict | None,
    threat_result: dict | None,
    redirect_analysis: dict | None = None,
) -> dict:
    risk_factors = []
    safety_factors = []
    metadata = domain_result.get('metadata', {}) if domain_result else {}
    domain_signals = domain_result.get('domain_signals', []) if domain_result else []
    age_days = metadata.get('age_days')
    ssl_valid = bool(metadata.get('ssl_valid'))

    if ml_result and float(ml_result.get('ml_score', 0) or 0) > 0.5:
        risk_factors.append({
            'title': 'URL model risk',
            'description': f"URL analysis returned a phishing probability of {float(ml_result.get('ml_score', 0) or 0):.2f}. The model flagged the URL structure as risky.",
            'severity': _severity_for_score(float(ml_result.get('ml_score', 0) or 0)),
            'source': 'url',
        })
    elif ml_result and float(ml_result.get('ml_score', 0) or 0) <= 0.25:
        safety_factors.append({
            'title': 'Low-risk URL signal',
            'description': f"The URL model assigned a phishing probability of {float(ml_result.get('ml_score', 0) or 0):.2f}, which is below the suspicious threshold.",
            'source': 'url',
        })

    if nlp_result and float(nlp_result.get('nlp_score', 0) or 0) > 0.4:
        keywords = nlp_result.get('suspicious_keywords') or []
        if keywords:
            key_list = ', '.join(keywords[:3])
            desc = f"Text analysis returned a phishing probability of {float(nlp_result.get('nlp_score', 0) or 0):.2f} and highlighted urgency-style terms such as {key_list}."
        else:
            desc = f"Text analysis returned a phishing probability of {float(nlp_result.get('nlp_score', 0) or 0):.2f}."
        risk_factors.append({
            'title': 'Suspicious text indicators',
            'description': desc,
            'severity': _severity_for_score(float(nlp_result.get('nlp_score', 0) or 0)),
            'source': 'text',
        })
    elif nlp_result and float(nlp_result.get('nlp_score', 0) or 0) <= 0.3:
        safety_factors.append({
            'title': 'Low-risk text signal',
            'description': f"The text analysis assigned a phishing probability of {float(nlp_result.get('nlp_score', 0) or 0):.2f}, which did not rise above the suspicious threshold.",
            'source': 'text',
        })

    if vision_result and float(vision_result.get('vision_score', 0) or 0) > 0.5:
        risk_factors.append({
            'title': 'Visual phishing cues',
            'description': f"The screenshot classifier scored {float(vision_result.get('vision_score', 0) or 0):.2f} for phishing-related layout signals.",
            'severity': _severity_for_score(float(vision_result.get('vision_score', 0) or 0)),
            'source': 'vision',
        })
    elif vision_result and float(vision_result.get('vision_score', 0) or 0) <= 0.3:
        safety_factors.append({
            'title': 'Low-risk visual signal',
            'description': f"The visual classifier scored {float(vision_result.get('vision_score', 0) or 0):.2f}, so no strong screenshot-based phishing evidence was present.",
            'source': 'vision',
        })

    if domain_result:
        if 'threat_intel_match' in domain_signals or (threat_result and int(threat_result.get('ti_hits', 0) or 0) > 0):
            sources = []
            if threat_result:
                sources = threat_result.get('ti_sources', []) or []
            else:
                sources = (threat_result or {}).get('ti_sources', []) or []
            risk_factors.append({
                'title': 'Threat-intelligence match',
                'description': f"Threat-intelligence sources returned a match for this target: {', '.join(sources) if sources else 'blacklisted feed'}.",
                'severity': 'high',
                'source': 'threat_intelligence',
            })
        if 'domain_very_new' in domain_signals and age_days is not None:
            risk_factors.append({
                'title': 'Very new domain',
                'description': f"The domain age is {age_days} days, which is a weak signal for a fresh phishing site.",
                'severity': 'medium',
                'source': 'domain',
            })
        elif 'domain_relatively_new' in domain_signals and age_days is not None:
            risk_factors.append({
                'title': 'Recently registered domain',
                'description': f"The domain age is {age_days} days, so it is relatively new compared with long-established legitimate sites.",
                'severity': 'medium',
                'source': 'domain',
            })
        elif 'no_valid_ssl' in domain_signals:
            risk_factors.append({
                'title': 'Missing valid SSL',
                'description': 'The domain did not present a valid SSL certificate during analysis.',
                'severity': 'low',
                'source': 'domain',
            })
        elif 'suspicious_redirect_chain' in domain_signals:
            risk_factors.append({
                'title': 'Suspicious redirect chain',
                'description': 'The redirect analysis identified a suspicious chain that can be used to conceal the final destination.',
                'severity': 'medium',
                'source': 'domain',
            })

        ti_hits = int((threat_result or {}).get('ti_hits', 0) or 0)
        if not ti_hits:
            ti_details = domain_result.get('ti_details') or domain_result.get('metadata', {}).get('ti_summary') or {}
            ti_hits = int(ti_details.get('ti_hits', 0) or 0)
        if ti_hits == 0:
            safety_factors.append({
                'title': 'Threat-intelligence check',
                'description': 'Threat-intelligence checks returned no threat-intelligence match for this target.',
                'source': 'threat_intelligence',
            })
        if age_days is not None and age_days > 365 and ssl_valid:
            safety_factors.append({
                'title': 'Established domain with valid SSL',
                'description': f"The domain is {age_days} days old and presented a valid SSL certificate during analysis.",
                'source': 'domain',
            })
        elif age_days is not None and age_days > 365:
            safety_factors.append({
                'title': 'Established domain',
                'description': f"The domain is {age_days} days old, which is a positive signal for a long-lived and more established site.",
                'source': 'domain',
            })
        elif ssl_valid:
            safety_factors.append({
                'title': 'Valid SSL certificate',
                'description': 'The domain presented a valid SSL certificate.',
                'source': 'domain',
            })

    # If there were no explicit risk factors and the score is still risky, keep a generic evidence note.
    if risk_level != 'safe' and not risk_factors and scores:
        risk_factors.append({
            'title': 'Engine-level risk evidence',
            'description': 'The model stack produced a combined phishing signal, but the individual engine evidence was not detailed enough to assign a more specific factor.',
            'severity': 'medium',
            'source': 'url',
        })

    if risk_level == 'safe' and not safety_factors:
        safety_factors.append({
            'title': 'No strong risk indicators',
            'description': 'The available engines did not produce strong phishing evidence in the current analysis.',
            'source': 'url',
        })

    redirect_evidence = []
    if redirect_analysis:
        redirect_state = redirect_analysis.get('resolution_state', 'failed')
        redirect_count = int(redirect_analysis.get('num_redirects', 0) or 0)
        if redirect_count:
            redirect_evidence.append({
                'title': 'Redirect chain detected',
                'description': f"{redirect_count} redirect{'s' if redirect_count != 1 else ''} detected before the analyzed destination.",
                'source': 'redirect',
            })
        if redirect_state == 'completed':
            redirect_evidence.append({
                'title': 'Redirect chain resolved',
                'description': 'Redirect chain resolved successfully; domain and threat-intelligence evidence below refers to the final resolved URL.',
                'source': 'redirect',
            })
        elif redirect_state == 'loop':
            redirect_evidence.append({
                'title': 'Redirect loop detected',
                'description': 'Resolution stopped after a repeated URL was detected.',
                'source': 'redirect',
            })
        elif redirect_state == 'limit_exceeded':
            redirect_evidence.append({
                'title': 'Redirect limit reached',
                'description': 'Resolution stopped because the configured redirect limit was reached.',
                'source': 'redirect',
            })
        elif redirect_state == 'blocked':
            redirect_evidence.append({
                'title': 'Redirect destination blocked',
                'description': 'Resolution stopped because a destination was blocked by SSRF protection.',
                'source': 'redirect',
            })
        elif redirect_state in ('failed', 'unavailable'):
            redirect_evidence.append({
                'title': 'Redirect resolution incomplete',
                'description': f"Redirect resolution did not complete ({redirect_state}); the available result was preserved.",
                'source': 'redirect',
            })
        if redirect_analysis.get('suspicious_redirects'):
            redirect_evidence.append({
                'title': 'Suspicious redirect-chain indicator',
                'description': 'The existing redirect heuristic marked this chain as suspicious evidence; this is not a standalone phishing verdict.',
                'severity': 'medium',
                'source': 'redirect',
            })

    summary = _build_xai_summary(risk_level, risk_factors, safety_factors)
    xai = {
        'summary': summary,
        'risk_factors': risk_factors,
        'safety_factors': safety_factors,
        'engine_signals': _build_engine_signals(scores, domain_result, threat_result),
        'feature_importance': _build_feature_importance(ml_result, nlp_result, vision_result),
        'redirect_analysis': redirect_analysis,
        'redirect_evidence': redirect_evidence,
    }
    return xai


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
    redirect_analysis = {
        'original_url': url,
        'final_url': url,
        'redirect_chain': [],
        'num_redirects': 0,
        'loop_detected': False,
        'suspicious_redirects': False,
        'has_meta_refresh': False,
        'resolution_state': 'unavailable',
        'errors': ['Redirect analysis was not available from Domain Intelligence.'],
    }
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

    # 2. Domain Intelligence & Redirects (Module 4). URL ML above continues
    # to score the original submitted URL; redirects are domain evidence only.
    domain_age_days = None
    domain_result = None
    if DOMAIN_READY and url:
        try:
            domain_res = analyze_domain(url)
            if domain_res:
                domain_result = domain_res
                redirect_analysis = domain_res.get('redirect_analysis', redirect_analysis)
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

    # Build structured XAI evidence using actual engine outputs, SHAP, and domain metadata.
    threat_result = None
    if domain_result:
        ti_details = domain_result.get('ti_details') or domain_result.get('metadata', {}).get('ti_summary')
        if ti_details:
            threat_result = ti_details

    ml_result = None
    nlp_result = None
    vision_result = None
    if ML_READY and url:
        try:
            ml_result = predict_url(url)
        except Exception:
            ml_result = None
    if NLP_READY and text:
        try:
            nlp_result = analyze_text_with_nlp(text)
        except Exception:
            nlp_result = None
    if VISION_READY and image_bytes:
        try:
            vision_result = analyze_image_with_vision(image_bytes)
        except Exception:
            vision_result = None

    xai_payload = _build_xai_structured(
        url=url,
        risk_level=risk_level,
        scores=scores,
        ml_result=ml_result,
        nlp_result=nlp_result,
        vision_result=vision_result,
        domain_result=domain_result,
        threat_result=threat_result,
        redirect_analysis=redirect_analysis,
    )

    # XAI LLM Summary for High/Medium risk
    xai_summary = xai_payload['summary']
    if risk_level in ["phishing", "suspicious"]:
        generated = generate_xai_summary(reasons, shap_nlp, shap_url, gradcam_vision, url, round(final_score * 100, 2))
        if generated:
            xai_summary = generated
            xai_payload['summary'] = generated

    xai_payload['summary'] = xai_summary
    return {
        "ensemble_score_percent": round(final_score * 100, 2),
        "confidence": round(final_score * 100, 2),
        "ensemble_risk_level": risk_level,
        "xai_summary": xai_summary,
        "xai": xai_payload,
        "reasons": reasons,
        "individual_scores_percent": {k: round(v * 100, 2) for k, v in scores.items()},
        "redirect_analysis": redirect_analysis,
    }
