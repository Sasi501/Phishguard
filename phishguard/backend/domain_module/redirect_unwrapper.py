import requests
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import re


def _extract_meta_refresh(html: str) -> str | None:
    """
    Parse HTML content for <meta http-equiv="refresh" content="N;url=..."> tags.
    Returns the redirect URL if found, or None.
    """
    # Match: <meta http-equiv="refresh" content="0;url=https://example.com">
    # Also handles single quotes, varying whitespace, and missing url= prefix
    pattern = r'<meta[^>]+http-equiv\s*=\s*["\']?\s*refresh\s*["\']?[^>]+content\s*=\s*["\']?\s*\d+\s*;\s*(?:url\s*=\s*)?([^"\'>]+)'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        url = match.group(1).strip().rstrip('"\'>')
        if url:
            return url
    return None

def unwrap_url(url: str, max_redirects: int = 5, timeout: int = 5, use_browser: bool = False) -> dict:
    """
    Safely resolve a URL's redirect chain.

    - Follows HTTP Location headers manually up to `max_redirects` to avoid uncontrolled
      automatic following and to capture intermediate URLs and status codes.
    - Detects redirect loops and stops when the same URL repeats.
    - By default does NOT run a browser. Set `use_browser=True` to attempt a lightweight
      Selenium-based page load to capture JS/meta-refresh redirects (disabled in typical
      server deployments).

    Returns a dict with:
      original_url, final_url, redirect_chain (list of {url, status_code}),
      num_redirects, loop_detected, errors (list).
    """
    from urllib.parse import urljoin
    path = []
    errors = []

    session = requests.Session()
    # Use a conservative User-Agent
    session.headers.update({
        "User-Agent": "PhishGuard/1.0 (+https://phishguard.local)"
    })

    current = url
    seen = set()

    try:
        for i in range(max_redirects + 1):
            if current in seen:
                # loop detected
                path.append({"url": current, "status_code": None, "note": "loop_detected"})
                loop_detected = True
                break

            seen.add(current)

            try:
                # Use GET with stream=True so body isn't downloaded fully if server responds
                resp = session.get(current, allow_redirects=False, timeout=timeout, stream=True)
                status = resp.status_code
            except Exception as e:
                errors.append(f"request_error:{str(e)}")
                # Cannot proceed — treat current as final
                path.append({"url": current, "status_code": None, "note": "request_failed"})
                loop_detected = False
                break

            # Append current response to path
            path.append({"url": current, "status_code": status})

            # Redirect status codes
            if status in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location")
                if not loc:
                    # No Location header — stop here
                    loop_detected = False
                    break

                # Resolve relative redirects
                next_url = urljoin(current, loc)

                # Prepare for next iteration
                current = next_url
                # Close response to free connection
                try:
                    resp.close()
                except Exception:
                    pass

                # Continue loop to follow next redirect
                continue
            else:
                # Not a standard redirect — check for HTML meta-refresh
                try:
                    # Read only the first 4KB to find meta refresh tags
                    partial_body = resp.content[:4096].decode('utf-8', errors='ignore')
                    meta_url = _extract_meta_refresh(partial_body)
                    if meta_url:
                        next_url = urljoin(current, meta_url)
                        path[-1]["note"] = "meta_refresh"
                        current = next_url
                        continue
                except Exception:
                    pass
                
                # No meta-refresh found — done
                loop_detected = False
                break

        final_url = current
    except Exception as e:
        final_url = current
        errors.append(f"unwrap_error:{str(e)}")
        loop_detected = False

    # Optional: try JS/meta refresh via headless browser if requested
    if use_browser and not loop_detected:
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new" if hasattr(Options(), 'add_argument') else "--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")

            # Only attempt to use webdriver if available; do not auto-install in servers
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            driver.set_page_load_timeout(timeout)
            driver.get(final_url)

            # Wait briefly for JS redirects (minimal wait)
            time.sleep(1.5)

            current_browser_url = driver.current_url
            if current_browser_url and current_browser_url != final_url:
                path.append({"url": current_browser_url, "status_code": "JS/Meta"})
                final_url = current_browser_url

            try:
                driver.quit()
            except Exception:
                pass
        except Exception as e:
            errors.append(f"browser_error:{str(e)}")

    suspicious = len(path) >= 3 or loop_detected

    return {
        "original_url": url,
        "final_url": final_url,
        "redirect_chain": path,
        "num_redirects": max(0, len(path) - 1),
        "loop_detected": bool(loop_detected),
        "suspicious_redirects": suspicious,
        "errors": errors,
    }
