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


if __name__ == "__main__":
    unittest.main()
