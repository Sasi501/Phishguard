import ipaddress
import os
import re
import socket
import time
from urllib.parse import urljoin, urlparse

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


_BLOCKED_IPV4_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
)

_METADATA_IP = ipaddress.ip_address("169.254.169.254")
_DEFAULT_TOTAL_TIMEOUT = float(os.environ.get("REDIRECT_RESOLUTION_TIMEOUT_SECONDS", "30"))
_META_REFRESH_MAX_BYTES = 4096


def _is_unsafe_ip(ip: ipaddress._BaseAddress) -> bool:
    if isinstance(ip, ipaddress.IPv4Address):
        if ip == _METADATA_IP:
            return True
        return any(ip in network for network in _BLOCKED_IPV4_NETWORKS) or ip.is_loopback or ip.is_private or ip.is_link_local
    if isinstance(ip, ipaddress.IPv6Address):
        return ip.is_loopback or ip.is_link_local or ip.is_private
    return False


def validate_url_for_fetch(url: str) -> str:
    """Validate a user-supplied URL before any network fetch or redirect follow."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https scheme")
    if not parsed.hostname:
        raise ValueError("URL hostname is required")

    try:
        infos = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        return url

    resolved_ips = []
    for _, _, _, _, sockaddr in infos:
        ip_text = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_text)
        except ValueError:
            continue
        resolved_ips.append(ip_obj)
        if _is_unsafe_ip(ip_obj):
            raise ValueError(f"Unsafe destination resolved to blocked address: {ip_obj}")

    if not resolved_ips:
        return url
    return url


def _extract_meta_refresh(html: str) -> str | None:
    """Return the URL from a supported HTML meta-refresh tag, if present."""
    pattern = r'<meta[^>]+http-equiv\s*=\s*["\']?\s*refresh\s*["\']?[^>]+content\s*=\s*["\']?\s*\d+\s*;\s*(?:url\s*=\s*)?([^"\'>]+)'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        url = match.group(1).strip().rstrip('"\'>')
        if url:
            return url
    return None


def _read_response_prefix(
    response,
    max_bytes: int = _META_REFRESH_MAX_BYTES,
    deadline: float | None = None,
) -> bytes:
    """Read only the bounded prefix needed to detect a meta refresh."""
    iterator = getattr(response, "iter_content", None)
    if callable(iterator):
        chunks = []
        total = 0
        for chunk in iterator(chunk_size=min(1024, max_bytes)):
            if deadline is not None and time.monotonic() >= deadline:
                raise requests.Timeout("total resolution budget exceeded")
            if not chunk:
                continue
            remaining = max_bytes - total
            chunks.append(chunk[:remaining])
            total += min(len(chunk), remaining)
            if total >= max_bytes:
                break
        return b"".join(chunks)

    content = getattr(response, "content", b"")
    if isinstance(content, str):
        content = content.encode("utf-8", errors="ignore")
    return content[:max_bytes]


def unwrap_url(
    url: str,
    max_redirects: int = 5,
    timeout: int = 5,
    use_browser: bool = False,
    total_timeout: float | None = None,
) -> dict:
    """
    Safely resolve a URL's redirect chain.

    HTTP redirects are followed manually with bounded per-request and total
    timeouts. Browser navigation remains opt-in and is not used by the main scan.
    """
    if total_timeout is None:
        total_timeout = _DEFAULT_TOTAL_TIMEOUT

    path = []
    errors = []
    loop_detected = False
    resolution_state = "failed"
    session = requests.Session()
    session.headers.update({"User-Agent": "PhishGuard/1.0 (+https://phishguard.local)"})

    current = url
    seen = set()
    redirects_followed = 0
    deadline = time.monotonic() + max(0.0, total_timeout)

    try:
        while True:
            if time.monotonic() >= deadline:
                errors.append("total_timeout:redirect resolution budget exceeded")
                resolution_state = "failed"
                break

            if current in seen:
                path.append({"url": current, "status_code": None, "note": "loop_detected"})
                loop_detected = True
                resolution_state = "loop"
                break
            seen.add(current)

            try:
                validate_url_for_fetch(current)
            except ValueError as exc:
                errors.append(f"unsafe_url:{exc}")
                path.append({"url": current, "status_code": None, "note": "unsafe_url"})
                resolution_state = "blocked"
                break

            response = None
            try:
                remaining = max(0.001, deadline - time.monotonic())
                response = session.get(
                    current,
                    allow_redirects=False,
                    timeout=min(timeout, remaining),
                    stream=True,
                )
                status = response.status_code
            except requests.Timeout as exc:
                errors.append(f"request_timeout:{exc}")
                path.append({"url": current, "status_code": None, "note": "request_timeout"})
                resolution_state = "failed"
                break
            except Exception as exc:
                errors.append(f"request_error:{exc}")
                path.append({"url": current, "status_code": None, "note": "request_failed"})
                resolution_state = "failed"
                break

            path.append({"url": current, "status_code": status})

            try:
                if status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        resolution_state = "completed"
                        break

                    next_url = urljoin(current, location)
                    if redirects_followed >= max_redirects:
                        errors.append("redirect_limit_exceeded:max_redirects reached")
                        path[-1]["note"] = "redirect_limit_exceeded"
                        resolution_state = "limit_exceeded"
                        break

                    try:
                        validate_url_for_fetch(next_url)
                    except ValueError as exc:
                        errors.append(f"unsafe_redirect:{exc}")
                        path.append({"url": next_url, "status_code": None, "note": "unsafe_redirect"})
                        resolution_state = "blocked"
                        break

                    current = next_url
                    redirects_followed += 1
                    continue

                partial_body = _read_response_prefix(response, deadline=deadline).decode("utf-8", errors="ignore")
                meta_url = _extract_meta_refresh(partial_body)
                if meta_url:
                    next_url = urljoin(current, meta_url)
                    if redirects_followed >= max_redirects:
                        errors.append("redirect_limit_exceeded:max_redirects reached")
                        path[-1]["note"] = "redirect_limit_exceeded"
                        resolution_state = "limit_exceeded"
                        break

                    try:
                        validate_url_for_fetch(next_url)
                    except ValueError as exc:
                        errors.append(f"unsafe_meta_refresh:{exc}")
                        path[-1]["note"] = "unsafe_meta_refresh"
                        resolution_state = "blocked"
                        break

                    path[-1]["note"] = "meta_refresh"
                    current = next_url
                    redirects_followed += 1
                    continue

                resolution_state = "completed"
                break
            except requests.Timeout as exc:
                if "total resolution budget" in str(exc):
                    errors.append(f"total_timeout:{exc}")
                    path[-1]["note"] = "total_timeout"
                else:
                    errors.append(f"response_timeout:{exc}")
                    path[-1]["note"] = "response_timeout"
                resolution_state = "failed"
                break
            except Exception as exc:
                errors.append(f"response_read_error:{exc}")
                path[-1]["note"] = "response_read_failed"
                resolution_state = "failed"
                break
            finally:
                if response is not None:
                    try:
                        response.close()
                    except Exception:
                        pass
    except Exception as exc:
        errors.append(f"unwrap_error:{exc}")
        resolution_state = "failed"

    final_url = current

    if use_browser and resolution_state == "completed":
        try:
            validate_url_for_fetch(final_url)
            chrome_options = Options()
            chrome_options.add_argument("--headless=new" if hasattr(Options(), "add_argument") else "--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            try:
                driver.set_page_load_timeout(timeout)
                driver.get(final_url)
                time.sleep(1.5)
                current_browser_url = driver.current_url
                if current_browser_url and current_browser_url != final_url:
                    validate_url_for_fetch(current_browser_url)
                    path.append({"url": current_browser_url, "status_code": "JS/Meta"})
                    final_url = current_browser_url
            finally:
                driver.quit()
        except ValueError as exc:
            errors.append(f"unsafe_browser_url:{exc}")
            resolution_state = "blocked"
        except Exception as exc:
            errors.append(f"browser_error:{exc}")
            resolution_state = "unavailable"

    suspicious = len(path) >= 3 or loop_detected
    return {
        "original_url": url,
        "final_url": final_url,
        "redirect_chain": path,
        "num_redirects": max(0, len(path) - 1),
        "loop_detected": bool(loop_detected),
        "suspicious_redirects": suspicious,
        "errors": errors,
        "resolution_state": resolution_state,
    }
