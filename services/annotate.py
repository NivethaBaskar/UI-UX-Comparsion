import tempfile
import os
from PIL import Image, ImageDraw, ImageFont

_SEV_COLOR = {
    "critical": (220, 38,  38),
    "high":     (234, 88,  12),
    "medium":   (202, 138,  4),
    "low":      (22,  163, 74),
}
_DEFAULT_COLOR = (99, 102, 241)  # indigo


def _load_font(size: int):
    for name in ["DejaVuSans-Bold.ttf", "arial.ttf", "Arial.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def annotate_screenshot(ui_path: str, issues: list, output_path: str) -> str:
    """
    Draw severity-colored bounding boxes on the screenshot for every issue
    that has a 'bbox' field. bbox values are fractions of the image size.
    Saves the annotated image to output_path and returns it.
    """
    base = Image.open(ui_path).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    img_w, img_h = base.size

    font_label = _load_font(13)

    for issue in issues:
        bbox = issue.get("bbox")
        if not bbox:
            continue

        sev = issue.get("severity", "low").lower()
        rgb = _SEV_COLOR.get(sev, _DEFAULT_COLOR)
        border_color = (*rgb, 230)
        fill_color   = (*rgb, 40)

        x  = int(bbox.get("x", 0) * img_w)
        y  = int(bbox.get("y", 0) * img_h)
        x2 = int((bbox.get("x", 0) + bbox.get("w", 0)) * img_w)
        y2 = int((bbox.get("y", 0) + bbox.get("h", 0)) * img_h)

        # Clamp to image bounds
        x, y   = max(0, x),   max(0, y)
        x2, y2 = min(img_w, x2), min(img_h, y2)
        if x2 <= x or y2 <= y:
            continue

        # Semi-transparent fill + border
        draw.rectangle([x, y, x2, y2], fill=fill_color, outline=border_color, width=3)

        # Label pill above the box
        label = f" {sev.upper()}: {issue.get('component', '')} "
        try:
            bbox_text = draw.textbbox((0, 0), label, font=font_label)
            lw = bbox_text[2] - bbox_text[0]
            lh = bbox_text[3] - bbox_text[1]
        except AttributeError:
            lw, lh = draw.textsize(label, font=font_label)

        pad = 3
        lx1 = x
        ly1 = max(0, y - lh - pad * 2)
        lx2 = min(img_w, lx1 + lw + pad * 2)
        ly2 = ly1 + lh + pad * 2

        draw.rectangle([lx1, ly1, lx2, ly2], fill=(*rgb, 220))
        draw.text((lx1 + pad, ly1 + pad), label, fill=(255, 255, 255), font=font_label)

    combined = Image.alpha_composite(base, overlay).convert("RGB")
    combined.save(output_path)
    return output_path


def crop_issue_region(ui_path: str, issue: dict, padding: int = 40) -> str | None:
    """
    Crop the screenshot to the issue's bbox area (+ padding), draw a colored
    highlight border, and save to a temp file.  Returns the temp file path,
    or None if the issue has no usable bbox.

    The caller is responsible for deleting the temp file after use.
    """
    bbox = issue.get("bbox")
    if not bbox:
        return None

    if not os.path.exists(ui_path):
        return None

    img = Image.open(ui_path).convert("RGBA")
    img_w, img_h = img.size

    x  = int(bbox.get("x", 0) * img_w)
    y  = int(bbox.get("y", 0) * img_h)
    x2 = int((bbox.get("x", 0) + bbox.get("w", 0)) * img_w)
    y2 = int((bbox.get("y", 0) + bbox.get("h", 0)) * img_h)

    # Add padding and clamp
    cx1 = max(0,     x  - padding)
    cy1 = max(0,     y  - padding)
    cx2 = min(img_w, x2 + padding)
    cy2 = min(img_h, y2 + padding)

    if cx2 <= cx1 or cy2 <= cy1:
        return None

    crop = img.crop((cx1, cy1, cx2, cy2))

    # Draw highlight on the cropped image (coordinates relative to crop origin)
    overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _load_font(14)

    sev = issue.get("severity", "low").lower()
    rgb = _SEV_COLOR.get(sev, _DEFAULT_COLOR)

    rx1, ry1 = x - cx1, y - cy1
    rx2, ry2 = x2 - cx1, y2 - cy1

    draw.rectangle([rx1, ry1, rx2, ry2], fill=(*rgb, 35), outline=(*rgb, 230), width=3)

    # Label pill
    label = f" {sev.upper()}: {issue.get('component', '')} "
    try:
        tb = draw.textbbox((0, 0), label, font=font)
        lw, lh = tb[2] - tb[0], tb[3] - tb[1]
    except AttributeError:
        lw, lh = draw.textsize(label, font=font)

    pad = 4
    lx1 = rx1
    ly1 = max(0, ry1 - lh - pad * 2)
    draw.rectangle([lx1, ly1, lx1 + lw + pad * 2, ly1 + lh + pad * 2], fill=(*rgb, 220))
    draw.text((lx1 + pad, ly1 + pad), label, fill=(255, 255, 255), font=font)

    combined = Image.alpha_composite(crop, overlay).convert("RGB")

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, prefix="jira_crop_")
    tmp.close()
    combined.save(tmp.name)
    return tmp.name
