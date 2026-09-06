"""
Generate PhishGuard extension icons (grey/default state) as PNG files.
Run once: python generate_icons.py
Requires: pip install Pillow
"""
import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "--break-system-packages"])
    from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 32, 48, 128]
ICONS_DIR = Path(__file__).parent / "extension" / "icons"
ICONS_DIR.mkdir(exist_ok=True)

COLORS = {
    "grey":     "#6b7280",
    "safe":     "#22c55e",
    "suspicious": "#f59e0b",
    "phishing": "#ef4444",
}

LABELS = {
    "grey":       "?",
    "safe":       "✓",
    "suspicious": "!",
    "phishing":   "✕",
}


def draw_icon(size, color_hex, label):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Parse hex color
    c = color_hex.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

    # Background circle
    margin = 1
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(r, g, b, 255)
    )

    # Inner lighter ring
    inner_margin = margin + max(2, size // 10)
    draw.ellipse(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        fill=(min(r + 30, 255), min(g + 30, 255), min(b + 30, 255), 60)
    )

    # Label text
    font_size = max(6, int(size * 0.45))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2 - bbox[0]
    y = (size - text_h) / 2 - bbox[1]
    draw.text((x, y), label, fill=(255, 255, 255, 255), font=font)

    return img


def main():
    for color_name, color_hex in COLORS.items():
        label = LABELS[color_name]
        for size in SIZES:
            img = draw_icon(size, color_hex, label)
            path = ICONS_DIR / f"icon-{color_name}-{size}.png"
            img.save(path, "PNG")
            print(f"  ✓ {path.name}")

    print(f"\nAll icons saved to: {ICONS_DIR}")
    print("Note: Reference icons in manifest.json as icons/icon-grey-*.png")


if __name__ == "__main__":
    main()
