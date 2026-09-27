"""Regression coverage for fusion correctness fixes B2 / B3 / B4 and Parts 5-7.

The governing semantic rule under test:

    applicable=False  => "this engine is not relevant to this scan input".
                          It did not run, therefore it contributes no evidence,
                          no weight, no denominator mass, and no failure.
    applicable & available => a real measurement.

Nothing here mocks ``get_meta_learner`` for the cases that must prove the real
artifact is used; those call the production loader.
"""
import unittest
import warnings
from contextlib import ExitStack
from unittest.mock import AsyncMock, Mock, patch

import numpy as np

from ensemble_module import fusion_engine


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
def _redirect(state: str = "completed", final_url: str = "https://final.test/") -> dict:
    return {
        "original_url": "https://submitted.test/",
        "final_url": final_url,
        "redirect_chain": [{"url": final_url, "status_code": 200, "note": "ok"}],
        "num_redirects": 1,
        "loop_detected": state == "loop",
        "suspicious_redirects": False,
        "has_meta_refresh": False,
        "resolution_state": state,
        "errors": [] if state == "completed" else [f"fixture:{state}"],
    }


def _domain_result(
    domain_score: float | None = 0.6,
    *,
    age_days: int | None = None,
    status: str = "available",
    ti_status: str = "available",
    ti_hits: int = 0,
    redirect_state: str = "completed",
) -> dict:
    result = {
        "status": status,
        "domain_score": domain_score,
        "domain_risk_level": "safe" if (domain_score or 0) < 0.35 else "suspicious",
        "domain_signals": [],
        "metadata": {"age_days": age_days, "ssl_valid": True},
        "ti_status": {"status": ti_status, "url_scope": "final_url"},
        "ti_details": {
            "status": ti_status,
            "ti_hits": ti_hits,
            "ti_sources": ["openphish"] if ti_hits else [],
        },
        "redirect_analysis": _redirect(redirect_state),
    }
    if status != "available":
        result["domain_score"] = None
        result["reason"] = "Network/domain inspection was restricted."
    return result


class _UseRealMeta:
    """Sentinel: leave ``get_meta_learner`` untouched (exercise the real artifact)."""


REAL_META = _UseRealMeta()


def _expected_weighted(measured: dict, moderation: float = 1.0) -> float:
    """Renormalised weighted score over the *measured* engines only."""
    active = sum(fusion_engine.FUSION_WEIGHTS[key] for key in measured)
    total = sum(value * fusion_engine.FUSION_WEIGHTS[key] for key, value in measured.items())
    return round(total / active * 100, 2)


async def _scan(
    url: str = "https://submitted.test/",
    *,
    text: str | None = None,
    image_bytes: bytes | None = None,
    vision_status: dict | None = None,
    ml_score: float = 0.4,
    nlp_score: float = 0.3,
    vision_score: float = 0.3,
    domain_score: float | None = 0.6,
    domain_result: dict | None = None,
    meta=REAL_META,
    ml_ready: bool = True,
    nlp_ready: bool = True,
    vision_ready: bool = True,
    domain_ready: bool = True,
) -> dict:
    if domain_result is None:
        domain_result = _domain_result(domain_score)

    with ExitStack() as stack:
        stack.enter_context(
            patch.multiple(
                fusion_engine,
                ML_READY=ml_ready,
                NLP_READY=nlp_ready,
                VISION_READY=vision_ready,
                DOMAIN_READY=domain_ready,
            )
        )
        stack.enter_context(
            patch(
                "detector.hitl_service.check_hitl_override",
                new=AsyncMock(return_value=None),
            )
        )
        stack.enter_context(
            patch.object(
                fusion_engine, "predict_url",
                return_value={"ml_score": ml_score, "ml_risk_level": "safe"},
            )
        )
        stack.enter_context(
            patch.object(fusion_engine, "analyze_domain", return_value=domain_result)
        )
        stack.enter_context(
            patch.object(
                fusion_engine, "analyze_text_with_nlp",
                return_value={"nlp_score": nlp_score, "suspicious_keywords": []},
            )
        )
        stack.enter_context(
            patch.object(
                fusion_engine, "analyze_image_with_vision",
                return_value={"vision_score": vision_score},
            )
        )
        if meta is not REAL_META:
            stack.enter_context(
                patch.object(fusion_engine, "get_meta_learner", return_value=meta)
            )

        return await fusion_engine.calculate_ensemble_score(
            url, text=text, image_bytes=image_bytes, vision_status=vision_status
        )


def _signals(result: dict) -> dict:
    return {item["source"]: item for item in result["xai"]["engine_signals"]}


# --------------------------------------------------------------------------- #
# B2 — fusion_method must describe the method that actually ran
# --------------------------------------------------------------------------- #
class FusionMethodProvenanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_meta_learner_executes_and_is_labelled(self):
        """A. Real meta-learner (unmocked) => fusion_method == meta_learner."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = await _scan(text="benign text", image_bytes=b"png", meta=REAL_META)

        clf = fusion_engine.get_meta_learner()
        self.assertIsNotNone(clf, "production meta-learner did not load")
        expected = clf.predict_proba(np.array([[0.4, 0.3, 0.3, 0.6]]))[0][1]

        self.assertEqual(result["fusion_method"], "meta_learner")
        self.assertEqual(
            result["ensemble_score_percent"], round(float(expected) * 100, 2)
        )
        self.assertEqual(result["analysis_status"], "complete")

    async def test_meta_learner_receives_only_measured_engines(self):
        """The 4-value vector must be the four engines that actually ran."""
        spy = Mock()
        spy.predict_proba.return_value = [[0.25, 0.75]]

        result = await _scan(text="benign text", image_bytes=b"png", meta=spy)

        spy.predict_proba.assert_called_once()
        vector = spy.predict_proba.call_args[0][0]
        np.testing.assert_allclose(vector, [[0.4, 0.3, 0.3, 0.6]])
        self.assertEqual(result["fusion_method"], "meta_learner")
        self.assertEqual(result["ensemble_score_percent"], 75.0)

    async def test_meta_unavailable_reports_weighted_fallback(self):
        """B. Loader returns None => weighted fallback, never 'meta_learner'."""
        result = await _scan(text="benign text", image_bytes=b"png", meta=None)

        self.assertEqual(result["fusion_method"], "weighted_available_engines")
        self.assertNotEqual(result["fusion_method"], "meta_learner")
        expected = _expected_weighted(
            {"ml": 0.4, "nlp": 0.3, "vision": 0.3, "domain": 0.6}
        )
        self.assertEqual(result["ensemble_score_percent"], expected)
        # Unavailability of the meta-learner is not a scan failure.
        self.assertEqual(result["analysis_status"], "complete")

    async def test_meta_prediction_failure_reports_weighted_fallback(self):
        """C. Loader succeeds, prediction raises => weighted fallback label."""
        broken = Mock()
        broken.predict_proba.side_effect = RuntimeError("simulated prediction failure")

        result = await _scan(text="benign text", image_bytes=b"png", meta=broken)

        broken.predict_proba.assert_called_once()
        self.assertEqual(result["fusion_method"], "weighted_available_engines")
        self.assertNotEqual(result["fusion_method"], "meta_learner")
        expected = _expected_weighted(
            {"ml": 0.4, "nlp": 0.3, "vision": 0.3, "domain": 0.6}
        )
        self.assertEqual(result["ensemble_score_percent"], expected)
        self.assertEqual(result["analysis_status"], "complete")

    async def test_meta_returning_unusable_score_reports_weighted_fallback(self):
        nan_model = Mock()
        nan_model.predict_proba.return_value = [float("nan"), float("nan")]

        result = await _scan(text="benign text", image_bytes=b"png", meta=nan_model)

        self.assertEqual(result["fusion_method"], "weighted_available_engines")
        self.assertIsNotNone(result["ensemble_score_percent"])


# --------------------------------------------------------------------------- #
# B3 — non-applicable engines carry no evidence and no weight
# --------------------------------------------------------------------------- #
class NonApplicableWeightTests(unittest.IsolatedAsyncioTestCase):
    async def test_url_only_scan_renormalises_over_measured_engines_only(self):
        result = await _scan(meta=None)

        measured = {"ml": 0.4, "domain": 0.6}
        renormalised = _expected_weighted(measured)          # (0.14 + 0.18) / 0.65
        unnormalised = round(sum(measured[k] * fusion_engine.FUSION_WEIGHTS[k]
                                 for k in measured) * 100, 2)

        self.assertEqual(result["ensemble_score_percent"], renormalised)
        # The pre-fix value counted NLP/Vision as measured "0.0 = safe".
        self.assertNotEqual(result["ensemble_score_percent"], unnormalised)
        self.assertEqual(result["fusion_method"], "weighted_available_engines")

    async def test_url_only_scan_never_feeds_the_meta_learner_zeros(self):
        """A non-applicable engine must not enter the meta-learner vector."""
        spy = Mock()
        spy.predict_proba.return_value = [0.5, 0.5]

        result = await _scan(meta=spy)   # no text, no image

        spy.predict_proba.assert_not_called()
        self.assertEqual(result["fusion_method"], "weighted_available_engines")

    async def test_applicable_failure_excludes_that_engine_from_the_denominator(self):
        """A failed-but-applicable engine is excluded, exactly like the partial
        branch already did — both branches share the same semantics."""
        result = await _scan(text="benign text", nlp_ready=False, meta=None)

        measured = {"ml": 0.4, "domain": 0.6}
        self.assertEqual(result["ensemble_score_percent"], _expected_weighted(measured))
        self.assertEqual(result["individual_scores_percent"], {"ml": 40.0, "domain": 60.0})

    async def test_configured_weights_are_unchanged(self):
        self.assertEqual(
            fusion_engine.FUSION_WEIGHTS,
            {"ml": 0.35, "nlp": 0.15, "vision": 0.20, "domain": 0.30},
        )


# --------------------------------------------------------------------------- #
# B4 — analysis_status semantics
# --------------------------------------------------------------------------- #
class AnalysisStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_applicable_engines_alone_do_not_make_a_scan_partial(self):
        result = await _scan(meta=None)          # URL + domain only

        self.assertFalse(result["engine_status"]["nlp"]["applicable"])
        self.assertFalse(result["engine_status"]["vision"]["applicable"])
        self.assertEqual(result["analysis_status"], "complete")

    async def test_applicable_engine_failure_makes_a_scan_partial(self):
        result = await _scan(text="benign text", nlp_ready=False, meta=None)

        self.assertTrue(result["engine_status"]["nlp"]["applicable"])
        self.assertNotEqual(result["engine_status"]["nlp"]["status"], "available")
        self.assertEqual(result["analysis_status"], "partial")

    async def test_applicable_domain_failure_makes_a_scan_partial(self):
        result = await _scan(
            domain_result=_domain_result(status="restricted"), meta=None
        )

        self.assertEqual(result["engine_status"]["domain_intelligence"]["status"], "restricted")
        self.assertEqual(result["analysis_status"], "partial")

    async def test_all_applicable_engines_failing_is_failed_not_partial(self):
        result = await _scan(
            ml_ready=False, domain_ready=False, meta=None
        )

        self.assertEqual(result["analysis_status"], "failed")
        self.assertIsNone(result["ensemble_score_percent"])
        self.assertEqual(result["fusion_method"], "unavailable")
        self.assertEqual(result["individual_scores_percent"], {})


# --------------------------------------------------------------------------- #
# Part 5 — individual_scores_percent must not fake measurements
# --------------------------------------------------------------------------- #
class IndividualScoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_url_only_scan_reports_only_the_measured_engines(self):
        result = await _scan(meta=None)

        self.assertEqual(
            sorted(result["individual_scores_percent"]), ["domain", "ml"]
        )
        self.assertNotIn("nlp", result["individual_scores_percent"])
        self.assertNotIn("vision", result["individual_scores_percent"])

    async def test_measured_zero_is_still_reported_as_zero(self):
        """Measured 0.0 and not-applicable must be distinguishable: a measured
        zero stays in individual_scores_percent, a non-applicable engine is
        simply absent (and separately described by engine_status)."""
        result = await _scan(
            text="benign", image_bytes=b"png",
            ml_score=0.0, nlp_score=0.0, vision_score=0.0, domain_score=0.0,
            meta=None,
        )

        self.assertEqual(
            result["individual_scores_percent"],
            {"ml": 0.0, "nlp": 0.0, "vision": 0.0, "domain": 0.0},
        )
        self.assertEqual(result["analysis_status"], "complete")

    async def test_unavailable_applicable_engine_is_absent_not_zero(self):
        result = await _scan(text="benign", image_bytes=b"png", meta=None,
                             vision_ready=False)

        self.assertNotIn("vision", result["individual_scores_percent"])
        self.assertEqual(
            result["engine_status"]["vision"]["status"], "unavailable"
        )


# --------------------------------------------------------------------------- #
# Part 6 — XAI must agree with applicability / status / fusion method
# --------------------------------------------------------------------------- #
class XaiApplicabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_xai_does_not_describe_non_applicable_engines_as_safe(self):
        result = await _scan(meta=None)          # URL + domain only
        signals = _signals(result)

        for source in ("nlp", "vision"):
            signal = signals[source]
            self.assertEqual(signal["url_scope"], "not_submitted")
            self.assertNotEqual(signal["risk_level"], "safe")
            self.assertEqual(signal["risk_level"], "unavailable")
            self.assertNotIn("score", signal)

        # XAI must not present text/vision safety or risk factors it never measured.
        structured = result["xai"]
        for factor in structured.get("risk_factors", []) + structured.get("safety_factors", []):
            self.assertNotIn(factor.get("source"), ("text", "vision"))

        # Fusion method, individual scores and analysis_status stay consistent.
        self.assertEqual(result["fusion_method"], "weighted_available_engines")
        self.assertEqual(result["analysis_status"], "complete")

    async def test_xai_describes_a_measured_engine(self):
        result = await _scan(text="benign", image_bytes=b"png", meta=None)
        signals = _signals(result)

        self.assertEqual(signals["nlp"]["status"], "available")
        self.assertEqual(signals["nlp"]["score"], 30.0)
        self.assertEqual(signals["nlp"]["url_scope"], "submitted_text")
        self.assertEqual(signals["vision"]["status"], "available")
        self.assertEqual(signals["vision"]["score"], 30.0)

    async def test_xai_url_evidence_matches_the_score_used_by_fusion(self):
        result = await _scan(meta=None)
        evidence = result["xai"]["url_ml_evidence"]

        self.assertEqual(
            evidence["engine_signal_percent"], result["individual_scores_percent"]["ml"]
        )
        self.assertEqual(evidence["raw_model_probability_percent"], 40.0)
        self.assertIsNone(evidence["engine_signal_adjustment"])


# --------------------------------------------------------------------------- #
# Part 7 #10 — redirect / domain / threat intelligence behaviour is untouched
# --------------------------------------------------------------------------- #
class UnchangedEngineBehaviourTests(unittest.IsolatedAsyncioTestCase):
    async def test_redirect_domain_and_ti_evidence_are_preserved(self):
        result = await _scan(
            meta=None,
            domain_result=_domain_result(
                0.6, ti_status="available", ti_hits=2, redirect_state="completed"
            ),
        )

        redirect = result["redirect_analysis"]
        self.assertEqual(redirect["resolution_state"], "completed")
        self.assertEqual(redirect["num_redirects"], 1)
        self.assertEqual(redirect["final_url"], "https://final.test/")

        signals = _signals(result)
        threat = signals["threat_intelligence"]
        self.assertEqual(threat["match_status"], "MATCH")
        self.assertEqual(threat["sources"], ["openphish"])
        self.assertEqual(threat["url_scope"], "final_url")
        self.assertEqual(result["xai"]["threat_intelligence"]["ti_hits"], 2)

        self.assertEqual(signals["url_ml"]["score"], 40.0)
        self.assertEqual(signals["domain_intelligence"]["score"], 60.0)
        self.assertEqual(signals["url_ml"]["url_scope"], "original_url")
        self.assertEqual(signals["domain_intelligence"]["url_scope"], "final_url")

    async def test_domain_age_moderation_still_applies_in_weighted_fusion(self):
        moderated = await _scan(
            domain_result=_domain_result(0.6, age_days=2000), meta=None
        )

        # 0.4 * 0.05 moderated, renormalised over {ml, domain}.
        expected = _expected_weighted({"ml": 0.02, "domain": 0.6})
        self.assertEqual(moderated["ensemble_score_percent"], expected)
        evidence = moderated["xai"]["url_ml_evidence"]
        self.assertEqual(evidence["raw_model_probability_percent"], 40.0)
        self.assertEqual(evidence["engine_signal_percent"], 2.0)
        self.assertEqual(evidence["engine_signal_adjustment"], "domain_age_moderation")


if __name__ == "__main__":
    unittest.main()
