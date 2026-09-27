import unittest
from unittest.mock import patch

from domain_module import domain_service


class DomainServiceRedirectTests(unittest.TestCase):
    def setUp(self):
        domain_service._CACHE.clear()

    @patch("domain_module.ti_integration.check_url_against_feeds")
    @patch("domain_module.domain_service.calculate_domain_risk")
    @patch("domain_module.domain_service.get_domain_metadata")
    @patch("domain_module.domain_service.unwrap_url")
    def test_domain_and_ti_provenance_uses_final_url(
        self,
        mock_unwrap,
        mock_metadata,
        mock_risk,
        mock_ti,
    ):
        redirect = {
            "original_url": "https://short.example/a",
            "final_url": "https://landing.example/login",
            "redirect_chain": [
                {"url": "https://short.example/a", "status_code": 302},
                {"url": "https://landing.example/login", "status_code": 200},
            ],
            "num_redirects": 1,
            "loop_detected": False,
            "suspicious_redirects": False,
            "resolution_state": "completed",
            "errors": [],
        }
        mock_unwrap.return_value = redirect
        mock_metadata.return_value = {"age_days": 2000, "ssl_valid": True}
        mock_risk.return_value = {
            "domain_score": 0.1,
            "domain_risk_level": "safe",
            "domain_signals": [],
            "metadata": mock_metadata.return_value,
        }
        mock_ti.return_value = {"ti_hits": 0, "ti_sources": []}

        result = domain_service.analyze_domain("https://short.example/a")

        mock_metadata.assert_called_once_with("https://landing.example/login")
        mock_ti.assert_called_once_with("https://landing.example/login")
        self.assertEqual(result["redirect_analysis"]["original_url"], "https://short.example/a")
        self.assertEqual(result["redirect_analysis"]["final_url"], "https://landing.example/login")
        self.assertEqual(result["final_url"], "https://landing.example/login")

    @patch("domain_module.domain_service.get_domain_metadata")
    @patch("domain_module.ti_integration.check_url_against_feeds")
    @patch("domain_module.domain_service.unwrap_url")
    def test_loopback_restriction_skips_metadata_and_returns_partial_evidence(
        self,
        mock_unwrap,
        mock_ti,
        mock_metadata,
    ):
        url = "http://127.0.0.1:8000/api/scan/"
        reason = "Unsafe destination resolved to blocked address: 127.0.0.1"
        mock_unwrap.return_value = {
            "original_url": url,
            "final_url": url,
            "redirect_chain": [{"url": url, "status_code": None, "note": "unsafe_url"}],
            "num_redirects": 0,
            "loop_detected": False,
            "suspicious_redirects": False,
            "resolution_state": "blocked",
            "blocked_reason": reason,
            "errors": [f"unsafe_url:{reason}"],
        }
        mock_ti.return_value = {"ti_hits": 0, "ti_sources": []}

        result = domain_service.analyze_domain(url, cache_ttl=0)

        mock_metadata.assert_not_called()
        mock_ti.assert_called_once_with(url)
        self.assertEqual(result["status"], "restricted")
        self.assertIsNone(result["domain_score"])
        self.assertEqual(result["redirect_analysis"]["resolution_state"], "blocked")
        self.assertEqual(result["redirect_analysis"]["blocked_reason"], reason)
        self.assertEqual(result["ti_status"]["status"], "available")


if __name__ == "__main__":
    unittest.main()
