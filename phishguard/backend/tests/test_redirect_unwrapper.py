import socket
import unittest
from unittest.mock import patch

import requests
from domain_module.redirect_unwrapper import unwrap_url, validate_url_for_fetch


class MockResp:
    def __init__(self, url, status_code=200, headers=None, body=b""):
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body
        self.requested_bytes = 0

    def iter_content(self, chunk_size=1024):
        for offset in range(0, len(self.body), chunk_size):
            chunk = self.body[offset:offset + chunk_size]
            self.requested_bytes += len(chunk)
            yield chunk

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
            self.assertEqual(res["resolution_state"], "completed")

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
            self.assertEqual(res["resolution_state"], "completed")

    def test_relative_redirect(self):
        def fake_get(url, allow_redirects, timeout, stream):
            if url == "http://example.com/start":
                return MockResp(url, status_code=302, headers={"Location": "/landing"})
            return MockResp(url, status_code=200)

        with patch("requests.Session.get", side_effect=fake_get):
            res = unwrap_url("http://example.com/start", max_redirects=5, timeout=1)
            self.assertEqual(res["final_url"], "http://example.com/landing")
            self.assertEqual(res["resolution_state"], "completed")

    def test_multiple_redirects(self):
        destinations = {
            "http://a.example/": "http://b.example/",
            "http://b.example/": "http://c.example/",
        }

        def fake_get(url, allow_redirects, timeout, stream):
            if url in destinations:
                return MockResp(url, status_code=301, headers={"Location": destinations[url]})
            return MockResp(url, status_code=200)

        with patch("requests.Session.get", side_effect=fake_get):
            res = unwrap_url("http://a.example/", max_redirects=5, timeout=1)
            self.assertEqual(res["num_redirects"], 2)
            self.assertEqual(res["final_url"], "http://c.example/")
            self.assertEqual(res["resolution_state"], "completed")

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
            self.assertEqual(res["resolution_state"], "loop")

    def test_url_blocked_localhost(self):
        with self.assertRaises(ValueError):
            validate_url_for_fetch("http://localhost/")

    def test_url_blocked_127_0_0_1(self):
        with self.assertRaises(ValueError):
            validate_url_for_fetch("http://127.0.0.1/")

    def test_url_blocked_private_ip(self):
        with self.assertRaises(ValueError):
            validate_url_for_fetch("http://10.0.0.5/")

    def test_url_blocked_metadata_endpoint(self):
        with self.assertRaises(ValueError):
            validate_url_for_fetch("http://169.254.169.254/latest/meta-data/")

    def test_url_blocked_ipv6_loopback(self):
        with self.assertRaises(ValueError):
            validate_url_for_fetch("http://[::1]/")

    def test_hostname_resolves_to_private_ip(self):
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.14.0.2", 80))]):
            with self.assertRaises(ValueError):
                validate_url_for_fetch("http://public.example/")

    def test_redirect_from_public_to_private_ip_blocked(self):
        def fake_get(url, allow_redirects, timeout, stream):
            if url == "https://public.example/":
                return MockResp(url, status_code=301, headers={"Location": "http://10.0.0.5/"})
            return MockResp(url, status_code=200)

        with patch("requests.Session.get", side_effect=fake_get), \
             patch("socket.getaddrinfo") as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = [
                [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
                [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 80))],
            ]
            res = unwrap_url("https://public.example/", max_redirects=3, timeout=1)
            self.assertIn("unsafe_redirect", str(res["errors"]))
            self.assertNotEqual(res["final_url"], "http://10.0.0.5/")
            self.assertEqual(res["resolution_state"], "blocked")

    def test_valid_public_https_url_allowed(self):
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]):
            self.assertEqual(validate_url_for_fetch("https://example.com/"), "https://example.com/")

    def test_redirect_limit_exceeded(self):
        def fake_get(url, allow_redirects, timeout, stream):
            return MockResp(url, status_code=302, headers={"Location": url + "next"})

        with patch("requests.Session.get", side_effect=fake_get):
            res = unwrap_url("http://example.com/", max_redirects=1, timeout=1)
            self.assertEqual(res["resolution_state"], "limit_exceeded")
            self.assertIn("redirect_limit_exceeded", str(res["errors"]))

    def test_request_timeout_is_failed(self):
        with patch("requests.Session.get", side_effect=requests.Timeout("slow response")):
            res = unwrap_url("http://example.com/", timeout=1)
            self.assertEqual(res["resolution_state"], "failed")
            self.assertIn("request_timeout", str(res["errors"]))

    def test_total_timeout_stops_before_request(self):
        with patch("requests.Session.get") as mock_get:
            res = unwrap_url("http://example.com/", total_timeout=0)
            mock_get.assert_not_called()
            self.assertEqual(res["resolution_state"], "failed")
            self.assertIn("total_timeout", str(res["errors"]))

    def test_meta_refresh(self):
        responses = {
            "http://example.com/": MockResp(
                "http://example.com/",
                body=b'<meta http-equiv="refresh" content="0;url=/landing">',
            ),
            "http://example.com/landing": MockResp("http://example.com/landing"),
        }

        with patch("requests.Session.get", side_effect=lambda url, **kwargs: responses[url]):
            res = unwrap_url("http://example.com/", timeout=1)
            self.assertEqual(res["final_url"], "http://example.com/landing")
            self.assertEqual(res["redirect_chain"][0]["note"], "meta_refresh")
            self.assertEqual(res["resolution_state"], "completed")

    def test_oversized_response_is_bounded(self):
        response = MockResp(
            "http://example.com/",
            body=(b"x" * 4096) + b'<meta http-equiv="refresh" content="0;url=/should-not-be-read">',
        )

        with patch("requests.Session.get", return_value=response):
            res = unwrap_url("http://example.com/", timeout=1)
            self.assertEqual(response.requested_bytes, 4096)
            self.assertEqual(res["resolution_state"], "completed")
            self.assertEqual(res["final_url"], "http://example.com/")


if __name__ == "__main__":
    unittest.main()
