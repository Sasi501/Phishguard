import unittest
from unittest.mock import patch

from domain_module.shortener_expander import is_likely_shortener, expand_short_url


class ShortenerExpanderTests(unittest.TestCase):
    def test_is_likely_shortener_true(self):
        self.assertTrue(is_likely_shortener("http://bit.ly/abc123"))
        self.assertTrue(is_likely_shortener("https://t.co/XYZ"))

    def test_is_likely_shortener_false(self):
        self.assertFalse(is_likely_shortener("https://example.com/"))

    @patch("domain_module.shortener_expander.unwrap_url")
    def test_expand_short_url_delegates(self, mock_unwrap):
        mock_unwrap.return_value = {
            "original_url": "http://bit.ly/abc",
            "final_url": "http://landing.example/",
            "redirect_chain": [{"url": "http://bit.ly/abc", "status_code": 301}, {"url": "http://landing.example/", "status_code": 200}],
            "num_redirects": 1,
            "loop_detected": False,
            "suspicious_redirects": False,
            "errors": []
        }

        res = expand_short_url("http://bit.ly/abc")
        self.assertEqual(res["final_url"], "http://landing.example/")
        self.assertTrue(res["is_shortener"]) 

    @patch("domain_module.shortener_expander.unwrap_url")
    @patch(
        "domain_module.shortener_expander.validate_url_for_fetch",
        side_effect=ValueError("Unsafe destination resolved to blocked address: 127.0.0.1"),
    )
    def test_private_shortener_is_structured_blocked_without_following(self, mock_validate, mock_unwrap):
        result = expand_short_url("http://bit.ly/unsafe")

        mock_validate.assert_called_once()
        mock_unwrap.assert_not_called()
        self.assertEqual(result["resolution_state"], "blocked")
        self.assertIn("127.0.0.1", result["blocked_reason"])


if __name__ == "__main__":
    unittest.main()
