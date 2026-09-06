"""
PhishGuard — NLP Service (Multilingual Edition)
Routes text to the correct model based on detected language:
  - English  → fine-tuned local DistilBERT
  - Other    → XLM-RoBERTa zero-shot classification (100 languages)
"""
import os
import logging

NLP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(NLP_DIR, "models")

logger = logging.getLogger(__name__)


# ─── Language Detection ───────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """Detect ISO 639-1 language code of the given text. Falls back to 'en'."""
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return "en"


# ─── Multilingual Zero-Shot Service ──────────────────────────────────────────

class MultilingualNLPService:
    """Zero-shot phishing classifier using XLM-RoBERTa — works for 100+ languages."""
    _instance = None
    _pipeline = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load(self):
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline
            logger.info("[PhishGuard NLP] Loading XLM-RoBERTa zero-shot pipeline...")
            self._pipeline = pipeline(
                "zero-shot-classification",
                model="joeddav/xlm-roberta-large-xnli",
                device=-1,   # CPU
            )
            logger.info("[PhishGuard NLP] XLM-RoBERTa loaded.")
        except Exception as e:
            logger.error(f"[PhishGuard NLP] Failed to load multilingual model: {e}")
            self._pipeline = None

    def analyze(self, text: str, lang_code: str) -> dict:
        self._load()

        candidate_labels = ["phishing scam", "legitimate message"]

        if self._pipeline is None:
            # Fallback: keyword-only scoring
            return self._keyword_fallback(text, lang_code)

        try:
            result = self._pipeline(
                text[:512],
                candidate_labels=candidate_labels,
                hypothesis_template="This message is {}.",
            )
            # scores[0] = phishing probability
            phishing_prob = result["scores"][0]
        except Exception as e:
            logger.warning(f"[PhishGuard NLP] Multilingual inference failed: {e}")
            return self._keyword_fallback(text, lang_code)

        from nlp.multilingual_keywords import extract_keywords_multilingual
        keywords = extract_keywords_multilingual(text, lang_code)

        if phishing_prob >= 0.70:
            risk = "phishing"
        elif phishing_prob >= 0.40:
            risk = "suspicious"
        else:
            risk = "safe"

        return {
            "nlp_score": round(phishing_prob, 4),
            "nlp_risk_level": risk,
            "detected_language": lang_code,
            "suspicious_keywords": keywords,
            "model": "xlm-roberta-zero-shot",
        }

    def _keyword_fallback(self, text: str, lang_code: str) -> dict:
        """Pure keyword scoring when models unavailable."""
        from nlp.multilingual_keywords import extract_keywords_multilingual
        keywords = extract_keywords_multilingual(text, lang_code)
        score = min(len(keywords) * 0.15, 1.0)
        risk = "phishing" if score >= 0.70 else ("suspicious" if score >= 0.30 else "safe")
        return {
            "nlp_score": round(score, 4),
            "nlp_risk_level": risk,
            "detected_language": lang_code,
            "suspicious_keywords": keywords,
            "model": "keyword-fallback",
        }

    def is_available(self) -> bool:
        try:
            from transformers import pipeline as _  # noqa
            return True
        except ImportError:
            return False


# ─── English DistilBERT Service ───────────────────────────────────────────────

class NLPService:
    _instance = None
    _model = None
    _tokenizer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is not None and self._tokenizer is not None:
            return
        if not os.path.exists(MODEL_DIR):
            raise FileNotFoundError(
                f"NLP model not found at {MODEL_DIR}. Run train_nlp.py first."
            )
        import torch
        from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
        logger.info(f"[PhishGuard NLP] Loading DistilBERT from {MODEL_DIR}")
        self._tokenizer = DistilBertTokenizer.from_pretrained(MODEL_DIR)
        self._model = DistilBertForSequenceClassification.from_pretrained(MODEL_DIR)
        self._model.eval()
        logger.info("[PhishGuard NLP] DistilBERT loaded.")

    def analyze_text(self, text: str) -> dict:
        import torch
        self._load_model()
        inputs = self._tokenizer(
            text, return_tensors="pt", truncation=True, padding=True, max_length=512
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        phishing_prob = probs[0][1].item()

        if phishing_prob >= 0.7:
            risk = "phishing"
        elif phishing_prob >= 0.4:
            risk = "suspicious"
        else:
            risk = "safe"

        from nlp.multilingual_keywords import extract_keywords_multilingual
        
        shap_features = []
        try:
            import shap
            # Create a simple wrapper for the model to use with SHAP
            def f(x):
                inps = self._tokenizer(list(x), return_tensors="pt", truncation=True, padding=True, max_length=512)
                with torch.no_grad():
                    outs = self._model(**inps)
                    return torch.nn.functional.softmax(outs.logits, dim=-1).numpy()
            
            # Use SHAP to explain the prediction
            explainer = shap.Explainer(f, self._tokenizer)
            shap_values = explainer([text])
            
            # Extract top contributing tokens (positive SHAP values pushing towards class 1)
            token_shap_pairs = []
            for token, val in zip(shap_values.data[0], shap_values.values[0][:, 1]):
                if val > 0 and token.strip() not in ['', '[CLS]', '[SEP]']:
                    token_shap_pairs.append({
                        "feature": token.strip(),
                        "shap_value": round(float(val), 4)
                    })
                    
            shap_features = sorted(token_shap_pairs, key=lambda x: x["shap_value"], reverse=True)[:3]
            
        except ImportError:
            # Fallback to simple keyword extraction if shap is unavailable
            keywords = extract_keywords_multilingual(text, "en") if risk != "safe" else []
            shap_features = [{"feature": kw, "shap_value": 0.5} for kw in keywords[:3]]

        return {
            "nlp_score": round(phishing_prob, 4),
            "nlp_risk_level": risk,
            "detected_language": "en",
            "shap_features": shap_features,
            "model": "distilbert-english",
        }

    def is_available(self) -> bool:
        return os.path.exists(MODEL_DIR)


# ─── Module-Level Singletons ─────────────────────────────────────────────────

_en_service = NLPService()
_ml_service = MultilingualNLPService()


def analyze_text_with_nlp(text: str) -> dict:
    """
    Analyze text for phishing intent.
    Automatically routes:
      - English → fine-tuned DistilBERT
      - Other   → XLM-RoBERTa zero-shot (100 languages)
    """
    lang = detect_language(text)
    logger.info(f"[PhishGuard NLP] Detected language: {lang}")

    if lang == "en" and _en_service.is_available():
        try:
            return _en_service.analyze_text(text)
        except Exception as e:
            logger.warning(f"[PhishGuard NLP] English model failed ({e}), falling back to multilingual.")

    # Non-English or English model unavailable → multilingual
    return _ml_service.analyze(text, lang)


def is_nlp_available() -> bool:
    return _en_service.is_available() or _ml_service.is_available()
