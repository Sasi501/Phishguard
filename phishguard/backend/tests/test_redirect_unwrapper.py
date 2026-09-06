import unittest
from unittest.mock import patch

from domain_module.redirect_unwrapper import unwrap_url


class MockResp:
    def __init__(self, url, status_code=200, headers=None):
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}
    def close(self):
        pass


class RedirectUnwrapperTests(unittest.TestCase):
    def test_no_redirect(self):
        def fake_get(url, allow_redirects, timeout, stream):
            return MockResp(url, status_code=200)

        with patch("requests.Session.get", side_effect=fake_get):
            res = unwrap_url("http://example.com/", max_redirects=5, timeout=1)
            self.assertEqual(res["final_url"], "http://example.com/")
            self.assertEqual(res["num_redirects"], 0)
            self.assertFalse(res["loop_detected"])

    def test_single_redirect_chain(self):
        # First URL -> redirect to second -> final
        def fake_get(url, allow_redirects, timeout, stream):
            if url == "http://short.url/":
                return MockResp(url, status_code=301, headers={"Location": "http://landing.page/"})
            elif url == "http://landing.page/":
                return MockResp(url, status_code=200)
            return MockResp(url, status_code=200)

        with patch("requests.Session.get", side_effect=fake_get):
            res = unwrap_url("http://short.url/", max_redirects=5, timeout=1)
            self.assertEqual(res["final_url"], "http://landing.page/")
            self.assertEqual(res["num_redirects"], 1)
            self.assertFalse(res["loop_detected"]) 

    def test_redirect_loop_detected(self):
        # A -> B -> A (loop)
        def fake_get(url, allow_redirects, timeout, stream):
            if url == "http://a/":
                return MockResp(url, status_code=301, headers={"Location": "http://b/"})
            elif url == "http://b/":
                return MockResp(url, status_code=301, headers={"Location": "http://a/"})
            return MockResp(url, status_code=200)

        with patch("requests.Session.get", side_effect=fake_get):
            res = unwrap_url("http://a/", max_redirects=10, timeout=1)
            self.assertTrue(res["loop_detected"]) 


if __name__ == "__main__":
    unittest.main()
