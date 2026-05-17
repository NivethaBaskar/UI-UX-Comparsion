from PIL import Image, ImageDraw, ImageFont

_SEV_RGB = {
    "critical": (220, 38,  38),
    "high":     (234, 88,  12),
    "medium":   (202, 138,  4),
    "low":      (22,  163, 74),
}

def resize_images(img1: Image.Image, img2: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Scale img2 to match img1's dimensions for accurate pixel comparison."""
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)
    return img1, img2


def annotate_screenshot(image_path: str, issues: list, output_path: str) -> str:
    """Overlay colored bounding boxes + severity labels on a screenshot.

    Boxes are drawn on a transparent overlay so the original is preserved.
    Issues without a bbox are skipped silently.
    Returns output_path.
    """
    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    img_w, img_h = img.size

    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()

    for issue in issues:
        bbox = issue.get("bbox")
        if not bbox:
            continue

        sev = str(issue.get("severity", "low")).lower()
        rgb = _SEV_RGB.get(sev, (100, 100, 100))

        x0 = int(bbox.get("x", 0) * img_w)
        y0 = int(bbox.get("y", 0) * img_h)
        x1 = int((bbox.get("x", 0) + bbox.get("w", 0)) * img_w)
        y1 = int((bbox.get("y", 0) + bbox.get("h", 0)) * img_h)

        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(img_w - 1, x1), min(img_h - 1, y1)
        if x1 <= x0 or y1 <= y0:
            continue

        # Semi-transparent fill + solid 3px border
        draw.rectangle([x0, y0, x1, y1], fill=rgb + (40,), outline=rgb + (255,), width=3)

        # Label: "HIGH · navbar"
        component = str(issue.get("component", ""))[:25]
        label = f" {sev.upper()} · {component} "
        try:
            tb = draw.textbbox((0, 0), label, font=font)
            lw, lh = tb[2] - tb[0], tb[3] - tb[1]
        except AttributeError:
            lw, lh = len(label) * 7, 14

        pad = 2
        lx = x0
        ly = y0 - lh - pad * 2
        if ly < 0:
            ly = y0 + pad  # place inside box when bbox touches top edge
        draw.rectangle([lx, ly, lx + lw, ly + lh + pad * 2], fill=rgb + (220,))
        draw.text((lx, ly + pad), label, fill=(255, 255, 255, 255), font=font)

    Image.alpha_composite(img, overlay).convert("RGB").save(output_path)
    return output_path
