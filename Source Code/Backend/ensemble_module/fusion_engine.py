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
    if risk_level == 'unavailable':
        return "No valid engine score was available to produce a final ensemble assessment."

    if risk_level == "safe":
        if safety_factors:
            ti_factor = next((f for f in safety_factors if 'threat-intelligence' in (f.get('title', '') + ' ' + f.get('description', '')).lower() or 'no match' in (f.get('description', '') or '').lower()), None)
            if ti_factor and ti_factor.get('description'):
                return f"Available engine scores produced a safe ensemble result. {ti_factor['description']}"
            support = safety_factors[0].get('description', '')
            if support:
                return f"Available engine scores produced a safe ensemble result. {support}"
        return "Available engine scores produced a safe ensemble result; no additional supporting evidence was reported."

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


def _build_engine_signals(
    scores: dict,
    domain_result: dict | None,
    threat_result: dict | None = None,
    engine_status: dict | None = None,
) -> list:
    engine_map = {
        'ml': ('URL Intelligence', 'url_ml'),
        'nlp': ('Text Intelligence', 'nlp'),
        'vision': ('Visual Intelligence', 'vision'),
        'domain': ('Domain Intelligence', 'domain_intelligence'),
    }
    signals = []
    for key, (label, status_key) in engine_map.items():
        status_info = (engine_status or {}).get(status_key, {})
        status = status_info.get('status', 'available')
        value = scores.get(key)
        input_scope = {
            'ml': 'original_url',
            'nlp': 'submitted_text',
            'vision': 'submitted_image',
            'domain': 'final_url',
        }[key]
        if key == 'vision':
            input_scope = status_info.get('input_scope', input_scope)
        if key in ('nlp', 'vision') and status_info.get('applicable') is False:
            input_scope = 'not_submitted'
        elif key == 'domain' and status == 'restricted':
            input_scope = 'not_collected'
        signal = {
            'engine': label,
            'status': status,
            'risk_level': _signal_from_engine_score(value) if status == 'available' and value is not None else status,
            'source': {
                'ml': 'url_ml',
                'nlp': 'nlp',
                'vision': 'vision',
                'domain': 'domain_intelligence',
            }[key],
            'score_type': 'engine_signal',
            'url_scope': input_scope,
        }
        if status == 'available' and isinstance(value, (int, float)):
            signal['score'] = round(float(value) * 100, 2)
        if status_info.get('reason'):
            signal['reason'] = status_info['reason']
        signals.append(signal)

    ti_hits = 0
    ti_sources = []
    if threat_result:
        ti_hits = int(threat_result.get('ti_hits', 0) or 0)
        ti_sources = threat_result.get('ti_sources', []) or []
    elif domain_result:
        ti_details = domain_result.get('ti_details') or domain_result.get('metadata', {}).get('ti_summary') or {}
        ti_hits = int(ti_details.get('ti_hits', 0) or 0)
        ti_sources = ti_details.get('ti_sources', []) or []

    ti_status = (engine_status or {}).get('threat_intelligence', {})
    ti_is_available = ti_status.get('status', 'available' if threat_result else 'unavailable') == 'available'
    ti_signal = {
        'engine': 'Threat Intelligence',
        'status': ti_status.get('status', 'available' if threat_result else 'unavailable'),
        'risk_level': ('phishing' if ti_hits > 0 else 'safe') if ti_is_available else 'unavailable',
        'source': 'threat_intelligence',
        'score_type': 'match_signal',
        'url_scope': ti_status.get('url_scope', 'final_url'),
    }
    if ti_is_available:
        ti_signal['score'] = 100.0 if ti_hits > 0 else 0.0
        ti_signal['match_status'] = 'MATCH' if ti_hits > 0 else 'NO MATCH'
        ti_signal['sources'] = ti_sources
    if ti_status.get('reason'):
        ti_signal['reason'] = ti_status['reason']
    signals.append(ti_signal)

    return signals


def _build_feature_importance(ml_result: dict | None, nlp_result: dict | None, vision_result: dict | None) -> list:
    features = []
    for label, source, url_scope, payload in [
        ('url', 'url', 'original_url', ml_result.get('shap_features') if ml_result else []),
        ('text', 'text', 'submitted_text', nlp_result.get('shap_features') if nlp_result else []),
        ('vision', 'vision', 'submitted_image', vision_result.get('gradcam_features') if vision_result else []),
    ]:
        for item in payload or []:
            if label == 'vision':
                feature_name = item.get('feature')
                raw_impact = item.get('gradcam_activation')
                value = item.get('feature')
                method = 'grad_cam'
            else:
                feature_name = item.get('feature')
                if 'shap_value' in item:
                    raw_impact = item.get('shap_value')
                    method = 'shap'
                elif 'importance' in item:
                    raw_impact = item.get('importance')
                    method = 'catboost_feature_importance'
                else:
                    continue
                value = item.get('value')
            if not feature_name or not isinstance(raw_impact, (int, float)):
                continue
            features.append({
                'feature': feature_name,
                'value': value,
                'impact': round(float(raw_impact), 4),
                'source': source,
                'method': method,
                'url_scope': url_scope,
            })
    return sorted(features, key=lambda f: abs(float(f['impact'] or 0)), reverse=True)[:8]


def _build_domain_xai_evidence(domain_result: dict | None, threat_result: dict | None) -> tuple[dict | None, dict | None]:
    if not domain_result:
        return None, None

    metadata = domain_result.get('metadata') or {}
    metadata_fields = (
        'domain',
        'registrable_domain',
        'age_days',
        'ssl_valid',
        'ssl_issuer',
        'ssl_error',
        'resolved_ips',
        'mx_records',
        'rdns',
        'error',
    )
    domain_evidence = {
        'status': domain_result.get(
            'status',
            'available' if domain_result.get('domain_score') is not None else 'unavailable',
        ),
        'reason': domain_result.get('reason'),
        'final_url': domain_result.get('final_url'),
        'domain_score': domain_result.get('domain_score'),
        'domain_risk_level': domain_result.get('domain_risk_level'),
        'metadata': {key: metadata[key] for key in metadata_fields if key in metadata},
    }

    ti = threat_result or domain_result.get('ti_details') or metadata.get('ti_summary') or {}
    ti_status = domain_result.get('ti_status') or {}
    threat_evidence = {
        'status': ti_status.get('status', ti.get('status', 'unavailable')),
        'reason': ti_status.get('reason') or ti.get('reason'),
        'url_scope': ti_status.get('url_scope', 'final_url'),
        'ti_hits': ti.get('ti_hits'),
        'ti_sources': ti.get('ti_sources', []),
        'is_exact_url_match': ti.get('is_exact_url_match'),
        'unavailable_sources': ti.get('unavailable_sources', ti_status.get('unavailable_sources', [])),
    }
    return domain_evidence, threat_evidence


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
    engine_status: dict | None = None,
) -> dict:
    risk_factors = []
    safety_factors = []
    raw_url_probability = _valid_engine_score(ml_result.get('ml_score')) if ml_result else None
    url_engine_signal = _valid_engine_score(scores.get('ml'))
    raw_url_probability_percent = (
        round(raw_url_probability * 100, 2) if raw_url_probability is not None else None
    )
    url_engine_signal_percent = (
        round(url_engine_signal * 100, 2) if url_engine_signal is not None else None
    )
    url_signal_adjusted = (
        raw_url_probability_percent is not None
        and url_engine_signal_percent is not None
        and raw_url_probability_percent != url_engine_signal_percent
    )
    url_ml_evidence = {
        'raw_model_probability_percent': raw_url_probability_percent,
        'engine_signal_percent': url_engine_signal_percent,
        'engine_signal_adjustment': 'domain_age_moderation' if url_signal_adjusted else None,
    } if raw_url_probability_percent is not None else None
    metadata = domain_result.get('metadata', {}) if domain_result else {}
    domain_signals = domain_result.get('domain_signals', []) if domain_result else []
    age_days = metadata.get('age_days')
    ssl_valid = bool(metadata.get('ssl_valid'))

    if raw_url_probability is not None and raw_url_probability > 0.5:
        risk_factors.append({
            'title': 'URL model risk',
            'description': (
                f"Raw URL-model probability: {raw_url_probability_percent:.2f}%. "
                f"URL ML engine signal used in fusion: {url_engine_signal_percent:.2f}%"
                f"{' after existing domain-age moderation' if url_signal_adjusted else ''}. "
                'The model flagged the URL structure as risky.'
            ),
            'severity': _severity_for_score(raw_url_probability),
            'source': 'url',
        })
    elif raw_url_probability is not None and raw_url_probability <= 0.25:
        safety_factors.append({
            'title': 'Low-risk URL signal',
            'description': (
                f"Raw URL-model probability: {raw_url_probability_percent:.2f}%. "
                f"URL ML engine signal used in fusion: {url_engine_signal_percent:.2f}%"
                f"{' after existing domain-age moderation' if url_signal_adjusted else ''}. "
                'The raw probability is below the suspicious threshold.'
            ),
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
        ti_status = (engine_status or {}).get('threat_intelligence', {})
        ti_available = ti_status.get('status', 'available' if threat_result else 'unavailable') == 'available'
        if ti_hits == 0 and ti_available:
            safety_factors.append({
                'title': 'Threat-intelligence check',
                'description': 'Available threat-intelligence sources returned no threat-intelligence match for this target. This is not proof that the target is safe.',
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
    if risk_level in ('phishing', 'suspicious') and not risk_factors and scores:
        risk_factors.append({
            'title': 'Engine-level risk evidence',
            'description': 'The model stack produced a combined phishing signal, but the individual engine evidence was not detailed enough to assign a more specific factor.',
            'severity': 'medium',
            'source': 'url',
        })

    if risk_level == 'safe' and not safety_factors:
        safety_factors.append({
            'title': 'No strong risk indicators',
            'description': 'The available engines did not produce strong phishing evidence in the current analysis. This does not establish that the target is safe outside the available evidence.',
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
        elif redirect_state == 'blocked':
            blocked_reason = redirect_analysis.get('blocked_reason') or 'The destination was blocked by URL safety validation.'
            redirect_evidence.append({
                'title': 'Redirect resolution restricted',
                'description': f'{blocked_reason} This restriction is not itself evidence of phishing.',
                'source': 'redirect',
                'status': 'restricted',
            })

    summary = _build_xai_summary(risk_level, risk_factors, safety_factors)
    status_map = engine_status or {}
    restricted_engines = [
        name.replace('_', ' ')
        for name, info in status_map.items()
        if info.get('applicable', True) and info.get('status') == 'restricted'
    ]
    unavailable_engines = [
        name.replace('_', ' ')
        for name, info in status_map.items()
        if info.get('applicable', True) and info.get('status') in ('unavailable', 'error')
    ]
    if restricted_engines:
        summary += (
            ' Network-based evidence was restricted for this destination '
            f'({", ".join(restricted_engines)}); that restriction is not itself evidence of phishing.'
        )
    elif unavailable_engines:
        summary += f' Some applicable evidence was unavailable ({", ".join(unavailable_engines)}).'
    domain_xai, threat_xai = _build_domain_xai_evidence(domain_result, threat_result)
    xai = {
        'summary': summary,
        'risk_factors': risk_factors,
        'safety_factors': safety_factors,
        'url_ml_evidence': url_ml_evidence,
        'engine_signals': _build_engine_signals(scores, domain_result, threat_result, engine_status),
        'engine_status': engine_status or {},
        'feature_importance': _build_feature_importance(ml_result, nlp_result, vision_result),
        'redirect_analysis': redirect_analysis,
        'redirect_evidence': redirect_evidence,
        'domain_intelligence': domain_xai,
        'threat_intelligence': threat_xai,
    }
    return xai


def _valid_engine_score(value) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if np.isfinite(score) and 0.0 <= score <= 1.0 else None


# ── Applicability semantics (single source of truth) ─────────────────────────
# The four engines that take part in score fusion, keyed by engine_status name.
FUSION_ENGINE_KEYS = ('url_ml', 'nlp', 'vision', 'domain_intelligence')

# Configured fusion weights. Values are unchanged; they are renormalised over
# the engines that actually ran (see calculate_ensemble_score).
FUSION_WEIGHTS = {'ml': 0.35, 'nlp': 0.15, 'vision': 0.20, 'domain': 0.30}


def _is_applicable(status: dict) -> bool:
    """True unless the engine explicitly reported `applicable: False`.

    `applicable: False` means "this engine is not relevant to this scan input",
    i.e. it never ran. Such an engine must not contribute evidence, must not
    contribute weight, and must not make a scan partial.
    """
    return bool(status.get('applicable', True))


def _is_available(status: dict) -> bool:
    """True only for an engine that is applicable *and* returned a score."""
    return _is_applicable(status) and status.get('status') == 'available'


def _meta_learner_score(scores: dict) -> float | None:
    """Run the meta-learner on the four engine scores.

    Returns None when no model can be loaded or when prediction fails, so the
    caller can fall back to weighted fusion. The caller must only report
    ``fusion_method == 'meta_learner'`` when this returns a usable score.
    """
    try:
        clf = get_meta_learner()
    except Exception as e:
        logging.error("Meta-learner could not be loaded: %s", e)
        return None
    if clf is None:
        return None

    try:
        X = np.array([[scores['ml'], scores['nlp'], scores['vision'], scores['domain']]])
        predicted = clf.predict_proba(X)[0][1]
    except Exception as e:
        logging.error("Meta-learner prediction failed; using weighted fusion instead: %s", e)
        return None

    score = _valid_engine_score(predicted)
    if score is None:
        logging.error("Meta-learner returned an unusable score: %r", predicted)
    return score


async def calculate_ensemble_score(
    url: str,
    text: str = None,
    image_bytes: bytes = None,
    vision_status: dict | None = None,
) -> dict:
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
    score_keys = set()
    engine_status = {
        'url_ml': {
            'status': 'unavailable',
            'reason': 'URL ML model is not ready.',
            'applicable': True,
        },
        'nlp': {
            'status': 'unavailable',
            'reason': 'No text input was submitted.',
            'applicable': bool(text),
        },
        'vision': vision_status or {
            'status': 'unavailable',
            'reason': 'No screenshot or image was available.',
            'applicable': bool(image_bytes),
        },
        'domain_intelligence': {
            'status': 'unavailable',
            'reason': 'Domain Intelligence did not return a result.',
            'applicable': True,
        },
        'threat_intelligence': {
            'status': 'unavailable',
            'reason': 'Threat Intelligence did not return a result.',
            'applicable': True,
        },
        'redirect': {
            'status': 'unavailable',
            'reason': 'Redirect analysis did not return a result.',
            'applicable': True,
        },
    }
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
    ml_result = None
    nlp_result = None
    vision_result = None
    
    # 1. URL ML Engine (Module 1)
    if ML_READY and url:
        try:
            ml_result = predict_url(url)
            if ml_result:
                ml_score = _valid_engine_score(ml_result.get('ml_score'))
                if ml_score is not None:
                    scores['ml'] = ml_score
                    score_keys.add('ml')
                    engine_status['url_ml'] = {'status': 'available', 'applicable': True}
                    if ml_score > 0.5:
                        reasons.append(f"URL analysis flagged high risk ({ml_score:.2f})")
                else:
                    engine_status['url_ml'] = {
                        'status': 'error',
                        'reason': 'URL ML did not return a valid score.',
                        'applicable': True,
                    }
                if 'shap_features' in ml_result:
                    shap_url = ml_result['shap_features']
            else:
                engine_status['url_ml'] = {
                    'status': 'error',
                    'reason': 'URL ML did not return a result.',
                    'applicable': True,
                }
        except Exception as e:
            logging.error(f"ML module error: {e}")
            engine_status['url_ml'] = {'status': 'error', 'reason': str(e), 'applicable': True}

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
                reported_domain_status = domain_res.get('status')
                domain_score = _valid_engine_score(domain_res.get('domain_score'))
                if reported_domain_status == 'restricted':
                    engine_status['domain_intelligence'] = {
                        'status': 'restricted',
                        'reason': domain_res.get('reason', 'Network/domain inspection was restricted.'),
                        'applicable': True,
                    }
                elif domain_score is not None:
                    scores['domain'] = domain_score
                    score_keys.add('domain')
                    engine_status['domain_intelligence'] = {'status': 'available', 'applicable': True}
                    domain_age_days = (domain_res.get('metadata') or {}).get('age_days')
                    for sig in domain_res.get('domain_signals', []):
                        reasons.append(f"Domain flagged for {sig.replace('_', ' ')}")
                else:
                    engine_status['domain_intelligence'] = {
                        'status': reported_domain_status if reported_domain_status in ('restricted', 'unavailable', 'error') else 'error',
                        'reason': domain_res.get('reason', 'Domain Intelligence did not return a valid score.'),
                        'applicable': True,
                    }

                ti_details = domain_res.get('ti_details') or (domain_res.get('metadata') or {}).get('ti_summary')
                reported_ti_status = domain_res.get('ti_status') or {}
                if reported_ti_status.get('status') in ('available', 'restricted', 'unavailable', 'error'):
                    engine_status['threat_intelligence'] = {
                        **reported_ti_status,
                        'applicable': True,
                    }
                elif ti_details is not None:
                    engine_status['threat_intelligence'] = {'status': 'available', 'applicable': True}
                else:
                    engine_status['threat_intelligence'] = {
                        'status': 'unavailable',
                        'reason': 'Threat-intelligence lookup returned no status or result.',
                        'applicable': True,
                    }
        except Exception as e:
            logging.error(f"Domain module error: {e}")
            engine_status['domain_intelligence'] = {'status': 'error', 'reason': str(e), 'applicable': True}
            engine_status['threat_intelligence'] = {'status': 'error', 'reason': str(e), 'applicable': True}

    redirect_state = redirect_analysis.get('resolution_state', 'unavailable')
    if redirect_state == 'completed':
        engine_status['redirect'] = {'status': 'available', 'applicable': True}
    elif redirect_state == 'blocked':
        engine_status['redirect'] = {
            'status': 'restricted',
            'reason': redirect_analysis.get('blocked_reason') or 'Unsafe destination blocked by URL validation.',
            'applicable': True,
        }
    elif redirect_state in ('loop', 'limit_exceeded'):
        engine_status['redirect'] = {
            'status': 'unavailable',
            'reason': f'Redirect resolution ended with state: {redirect_state}.',
            'applicable': True,
        }
    elif redirect_state == 'failed':
        engine_status['redirect'] = {
            'status': 'error',
            'reason': '; '.join(redirect_analysis.get('errors', [])) or 'Redirect analysis failed.',
            'applicable': True,
        }
    else:
        engine_status['redirect'] = {
            'status': 'unavailable',
            'reason': 'Redirect analysis was not available.',
            'applicable': True,
        }
            
    # 3. Vision Engine (Module 3)
    if VISION_READY and image_bytes:
        try:
            vision_result = analyze_image_with_vision(image_bytes)
            if vision_result:
                vision_score = _valid_engine_score(vision_result.get('vision_score'))
                if vision_score is not None:
                    scores['vision'] = vision_score
                    score_keys.add('vision')
                    engine_status['vision'] = {
                        'status': 'available',
                        'applicable': True,
                        'input_scope': (vision_status or {}).get('input_scope', 'submitted_image'),
                    }
                    if vision_score > 0.5:
                        reasons.append(f"Visual layout imitation detected ({vision_score:.2f})")
                else:
                    engine_status['vision'] = {
                        'status': 'error',
                        'reason': 'Vision did not return a valid score.',
                        'applicable': True,
                        'input_scope': (vision_status or {}).get('input_scope', 'submitted_image'),
                    }
                if 'gradcam_features' in vision_result:
                    gradcam_vision = vision_result['gradcam_features']
            else:
                engine_status['vision'] = {
                    'status': 'error',
                    'reason': 'Vision did not return a result.',
                    'applicable': True,
                    'input_scope': (vision_status or {}).get('input_scope', 'submitted_image'),
                }
        except Exception as e:
            logging.error(f"Vision module error: {e}")
            engine_status['vision'] = {
                'status': 'error',
                'reason': str(e),
                'applicable': True,
                'input_scope': (vision_status or {}).get('input_scope', 'submitted_image'),
            }
    elif vision_status is not None and vision_status.get('status') != 'available':
        engine_status['vision'] = {
            **vision_status,
            'applicable': vision_status.get('applicable', True),
        }
    elif vision_status is not None:
        engine_status['vision'] = {
            'status': 'unavailable',
            'reason': 'A screenshot was captured, but the Vision model did not return a score.',
            'applicable': vision_status.get('applicable', True),
        }
    elif image_bytes:
        engine_status['vision'] = {
            'status': 'unavailable',
            'reason': 'Vision model is not ready.',
            'applicable': True,
        }
    else:
        engine_status['vision'] = {
            'status': 'unavailable',
            'reason': 'No screenshot or image was available.',
            'applicable': False,
        }
            
    # 4. NLP Engine (Module 2)
    if NLP_READY and text:
        try:
            nlp_result = analyze_text_with_nlp(text)
            if nlp_result:
                nlp_score = _valid_engine_score(nlp_result.get('nlp_score'))
                if nlp_score is not None:
                    scores['nlp'] = nlp_score
                    score_keys.add('nlp')
                    engine_status['nlp'] = {'status': 'available', 'applicable': True}
                else:
                    engine_status['nlp'] = {
                        'status': 'error',
                        'reason': 'NLP did not return a valid score.',
                        'applicable': True,
                    }
                keywords = nlp_result.get('suspicious_keywords', [])
                if keywords:
                    reasons.append(f"Urgency/phishing keywords found: {', '.join(keywords)}")
                if 'shap_features' in nlp_result:
                    shap_nlp = nlp_result['shap_features']
            else:
                engine_status['nlp'] = {
                    'status': 'error',
                    'reason': 'NLP did not return a result.',
                    'applicable': True,
                }
        except Exception as e:
            logging.error(f"NLP module error: {e}")
            engine_status['nlp'] = {'status': 'error', 'reason': str(e), 'applicable': True}
    elif text:
        engine_status['nlp'] = {
            'status': 'unavailable',
            'reason': 'NLP model is not ready.',
            'applicable': True,
        }
    else:
        engine_status['nlp'] = {
            'status': 'unavailable',
            'reason': 'No text input was submitted.',
            'applicable': False,
        }

    # analysis_status is evaluated over *applicable* engines only: an engine
    # that did not run (applicable: False) is not a failure, so it alone can
    # never make a scan partial.
    incomplete_evidence = any(
        _is_applicable(item) and item.get('status') != 'available'
        for item in engine_status.values()
    )
    analysis_status = 'partial' if incomplete_evidence else 'complete'

    # The meta-learner consumes a fixed [ml, nlp, vision, domain] vector, so it
    # may only run when every fusion engine produced a measurement. Feeding it
    # engines that never ran would encode "not measured" as "measured 0.0".
    fusion_vector_complete = all(
        _is_available(engine_status.get(key, {})) for key in FUSION_ENGINE_KEYS
    )

    # fusion_method describes the method that ACTUALLY produced final_score.
    # It is only set to 'meta_learner' after a successful prediction, never
    # optimistically before the model is loaded.
    final_score = None
    fusion_method = 'unavailable'

    if not score_keys:
        # No applicable engine produced a measurement: there is nothing to fuse.
        analysis_status = 'failed'
    else:
        if fusion_vector_complete:
            meta_score = _meta_learner_score(scores)
            if meta_score is not None:
                final_score = meta_score
                fusion_method = 'meta_learner'

        if final_score is None:
            # Weighted fallback — also used when the meta-learner is unavailable
            # or its prediction failed.

            # Multi-Modal Correlation:
            # If the domain is highly established (e.g., > 2 years old), structural ML anomalies
            # are likely benign false positives.
            if domain_age_days is not None:
                if domain_age_days > 1825:
                    scores['ml'] = scores['ml'] * 0.05
                    reasons = [r for r in reasons if "URL analysis flagged" not in r]
                elif domain_age_days > 730:
                    scores['ml'] = scores['ml'] * 0.20
                    if scores['ml'] < 0.5:
                        reasons = [r for r in reasons if "URL analysis flagged" not in r]
                elif domain_age_days > 365:
                    scores['ml'] = scores['ml'] * 0.50
                    if scores['ml'] < 0.5:
                        reasons = [r for r in reasons if "URL analysis flagged" not in r]

            # Keep the configured weights unchanged, but renormalise them over
            # the engines that actually ran. Without this, engines with
            # applicable: False would silently leave part of the total weight
            # attributed to an unmeasured "0.0 = safe".
            active_weight = sum(FUSION_WEIGHTS[key] for key in score_keys)
            final_score = sum(scores[key] * FUSION_WEIGHTS[key] for key in score_keys) / active_weight
            fusion_method = 'weighted_available_engines'

    if final_score is None:
        risk_level = 'unavailable'
    elif final_score >= 0.7:
        risk_level = "phishing"
    elif final_score >= 0.35:
        risk_level = "suspicious"
    else:
        risk_level = "safe"
        if not reasons:
            reasons.append(
                "Available engine scores remained below the suspicious threshold."
                if analysis_status == 'partial'
                else "All provided signals appear safe."
            )

    # Build structured XAI evidence using actual engine outputs, SHAP, and domain metadata.
    threat_result = None
    if domain_result:
        ti_details = domain_result.get('ti_details') or domain_result.get('metadata', {}).get('ti_summary')
        if ti_details:
            threat_result = ti_details

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
        engine_status=engine_status,
    )

    # The displayed XAI summary is deterministic structured evidence. Do not replace
    # it with free-form LLM output: an LLM narrative cannot be verified against the
    # evidence returned for this scan and may imply observations that were unavailable.
    xai_summary = xai_payload['summary']

    xai_payload['summary'] = xai_summary
    # Only engines that produced a measurement are reported. An engine with
    # applicable: False is absent rather than reported as a measured 0.0;
    # its availability/applicability is exposed separately in engine_status.
    returned_scores = {key: scores[key] for key in score_keys}
    return {
        "ensemble_score_percent": round(final_score * 100, 2) if final_score is not None else None,
        "confidence": round(final_score * 100, 2) if final_score is not None else None,
        "ensemble_risk_level": risk_level,
        "analysis_status": analysis_status,
        "engine_status": engine_status,
        "fusion_method": fusion_method,
        "xai_summary": xai_summary,
        "xai": xai_payload,
        "reasons": reasons,
        "individual_scores_percent": {k: round(v * 100, 2) for k, v in returned_scores.items()},
        "redirect_analysis": redirect_analysis,
    }
