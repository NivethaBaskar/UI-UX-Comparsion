import numpy as np
from PIL import Image
from typing import List, Dict

WCAG_AA_NORMAL = 4.5   # contrast ratio required for normal text
WCAG_AA_LARGE  = 3.0   # contrast ratio required for large text (18pt+ or 14pt bold)
GRID           = 12    # divide screenshot into GRID×GRID cells for sampling


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """Vectorized WCAG relative luminance for an (N, 3) uint8 RGB array."""
    c = rgb.astype(np.float64) / 255.0
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return linear @ np.array([0.2126, 0.7152, 0.0722])


def _contrast_ratio(l1: float, l2: float) -> float:
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def check_accessibility(image_path: str) -> List[Dict]:
    """
    Scan the screenshot in a GRID×GRID grid for regions with low color contrast.
    Uses the WCAG 2.1 relative luminance formula on the 10th/90th percentile
    pixel luminances per cell (dark representative vs light representative).

    Skips near-uniform cells (solid backgrounds with no text) using luminance
    standard deviation as a proxy for content presence.

    Returns up to 8 issues sorted by worst contrast first.
    """
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    H, W = arr.shape[:2]

    cell_h = H // GRID
    cell_w = W // GRID

    issues: List[Dict] = []
    seen_zones: set = set()

    for row in range(GRID):
        for col in range(GRID):
            y0, y1 = row * cell_h, (row + 1) * cell_h
            x0, x1 = col * cell_w, (col + 1) * cell_w

            pixels = arr[y0:y1, x0:x1].reshape(-1, 3)
            lums   = _luminance(pixels)

            # Near-uniform cell = solid background, no text to check
            if lums.std() < 0.015:
                continue

            p10   = float(np.percentile(lums, 10))
            p90   = float(np.percentile(lums, 90))
            ratio = _contrast_ratio(p10, p90)

            if ratio < WCAG_AA_NORMAL:
                # Deduplicate: collapse adjacent cells into 3×3 super-zones
                zone = (col // 3, row // 3)
                if zone in seen_zones:
                    continue
                seen_zones.add(zone)

                severity = "high" if ratio < WCAG_AA_LARGE else "medium"
                issues.append({
                    "type":           "accessibility",
                    "component":      f"Region ({col + 1},{row + 1})",
                    "issue": (
                        f"Low color contrast {ratio:.1f}:1 — "
                        f"WCAG AA requires 4.5:1 for normal text, 3.0:1 for large text"
                    ),
                    "severity":        severity,
                    "contrast_ratio":  round(ratio, 2),
                    "wcag_standard":   "WCAG 2.1 AA",
                    "bbox": {
                        "x": x0 / W,
                        "y": y0 / H,
                        "w": cell_w / W,
                        "h": cell_h / H,
                    },
                })

    issues.sort(key=lambda i: i["contrast_ratio"])
    return issues[:8]
