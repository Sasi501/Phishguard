"""
Screenshot pipeline prototype for PhishGuard.

This module provides a safe, configurable interface to capture webpage screenshots.
It defaults to a stub implementation that returns a generated placeholder image
so the rest of the system can be integrated and tested without requiring a
headless browser runtime in all environments.

Enable a real headless browser capture by setting environment variable:
  SCREENSHOT_ENABLED=1

When enabled, the implementation will attempt to use Selenium + webdriver-manager
or Playwright if available. For security and production, run browser capture in
an isolated worker or container with strict timeouts and resource limits.
"""
import os
import io
import time
from typing import Dict, Any

from PIL import Image, ImageDraw, ImageFont

from dotenv import load_dotenv
load_dotenv()
SCREENSHOT_ENABLED = os.environ.get('SCREENSHOT_ENABLED') in ('1', 'true', 'True')


def _generate_placeholder_image(url: str, size=(1200, 800)) -> bytes:
    # Create a simple placeholder PNG with text
    img = Image.new('RGB', size, color=(240, 240, 245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    text = f"Screenshot placeholder\n{url}"
    draw.text((20, 20), text, fill=(30, 30, 30), font=font)

    # Convert to JPEG bytes
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=75)
    return buf.getvalue()


def _compute_ahash(img: Image.Image, hash_size: int = 8) -> str:
    """Compute a simple average hash (aHash) for an image and return hex string."""
    # convert to grayscale and resize to hash_size x hash_size
    small = img.convert('L').resize((hash_size, hash_size), resample=Image.Resampling.BILINEAR)
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    bits = ''.join('1' if p > avg else '0' for p in pixels)
    # convert bitstring to hex
    width = hash_size * hash_size
    hex_string = '%0*X' % ((width + 3) // 4, int(bits, 2))
    return hex_string


def capture_screenshot(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Capture a screenshot for the given URL.

    Returns:
      {
        'original_url': url,
        'final_url': url,   # if redirect resolution is used, return final URL
        'image_bytes': b'...'(JPEG),
        'width': int,
        'height': int,
        'phash': str (hex aHash),
        'thumb': b'...' (small JPEG)
      }

    When SCREENSHOT_ENABLED is not set, returns a generated placeholder image
    along with a thumbnail and a perceptual hash so downstream vision models
    can be exercised without a browser runtime.
    """
    start = time.time()

    try:
        if not SCREENSHOT_ENABLED:
            # Placeholder path
            buf_bytes = _generate_placeholder_image(url)
            img = Image.open(io.BytesIO(buf_bytes)).convert('RGB')
            w, h = img.size

            # generate thumbnail
            thumb = img.copy()
            thumb.thumbnail((320, 200))
            buf_thumb = io.BytesIO()
            thumb.save(buf_thumb, format='JPEG', quality=70)

            phash = _compute_ahash(img)

            return {
                'original_url': url,
                'final_url': url,
                'image_bytes': buf_bytes,
                'width': w,
                'height': h,
                'phash': phash,
                'thumb': buf_thumb.getvalue(),
                'elapsed': time.time() - start,
                'is_real_screenshot': False,
            }

        # Real screenshot path — Use a reliable public screenshot API instead of brittle local Selenium
        import requests
        api_url = f"https://image.thum.io/get/width/1200/crop/800/{url}"
        resp = requests.get(api_url, timeout=timeout)
        
        if resp.status_code != 200 or len(resp.content) < 1000:
            raise Exception(f"Screenshot API failed with status {resp.status_code}")
            
        png = resp.content

        # Create thumbnail and phash
        img = Image.open(io.BytesIO(png)).convert('RGB')
        w, h = img.size
        thumb = img.copy()
        thumb.thumbnail((320, 200))
        buf_thumb = io.BytesIO()
        thumb.save(buf_thumb, format='JPEG', quality=70)

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=80)

        phash = _compute_ahash(img)

        return {
            'original_url': url,
            'final_url': url,
            'image_bytes': buf.getvalue(),
            'width': w,
            'height': h,
            'phash': phash,
            'thumb': buf_thumb.getvalue(),
            'elapsed': time.time() - start,
            'is_real_screenshot': True,
        }
    except Exception as e:
        # Fall back to placeholder on any error but try to still provide thumb and phash
        buf_bytes = _generate_placeholder_image(url)
        img = Image.open(io.BytesIO(buf_bytes)).convert('RGB')
        w, h = img.size
        thumb = img.copy()
        thumb.thumbnail((320, 200))
        buf_thumb = io.BytesIO()
        thumb.save(buf_thumb, format='JPEG', quality=70)
        phash = _compute_ahash(img)

        return {
            'original_url': url,
            'final_url': url,
            'image_bytes': buf_bytes,
            'width': w,
            'height': h,
            'phash': phash,
            'thumb': buf_thumb.getvalue(),
            'elapsed': time.time() - start,
            'is_real_screenshot': False,
            'error': str(e),
        }
