#!/usr/bin/env python3
"""Validate the Riser Manager screenshot crop and padding."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMAGE_PATH = ROOT / "assets" / "chorus-tools-riser.png"

CONTENT_THRESHOLD = 12
MIN_PADDING = 64
MARGIN_TOLERANCE = 0.18  # max deviation from mean margin
TOP_CLEAR_RATIO = 0.07   # top 7% of image must be background at center


def load_mask(path: Path) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int]]:
    im = Image.open(path).convert("RGB")
    arr = np.array(im)
    bg = tuple(arr[0, 0])
    diff = np.abs(arr.astype(int) - np.array(bg)).sum(axis=2)
    return arr, diff > CONTENT_THRESHOLD, bg


def margins(mask: np.ndarray) -> dict[str, int]:
    h, w = mask.shape
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        raise ValueError("No content detected")
    top, bottom = int(rows[0]), int(rows[-1])
    left, right = int(cols[0]), int(cols[-1])
    return {
        "top": top,
        "bottom": h - 1 - bottom,
        "left": left,
        "right": w - 1 - right,
    }


def center_top_is_clear(arr: np.ndarray, bg: tuple[int, int, int]) -> bool:
    h, w = arr.shape[:2]
    cx = w // 2
    scan_rows = max(1, int(h * TOP_CLEAR_RATIO))
    strip = arr[:scan_rows, cx - 40 : cx + 40]
    return not (np.abs(strip.astype(int) - np.array(bg)).sum(axis=2) > CONTENT_THRESHOLD).any()


def validate(path: Path = IMAGE_PATH) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"Missing image: {path}"]

    arr, mask, bg = load_mask(path)
    h, w = arr.shape[:2]

    if w <= h:
        errors.append(f"Expected landscape image, got {w}x{h}")

    m = margins(mask)
    values = list(m.values())
    avg = sum(values) / len(values)

    for side, value in m.items():
        if value < MIN_PADDING:
            errors.append(f"{side} margin {value}px is below minimum {MIN_PADDING}px")

    spread = max(values) - min(values)
    if avg > 0 and spread / avg > MARGIN_TOLERANCE:
        errors.append(
            "Uneven padding: "
            f"top={m['top']} right={m['right']} bottom={m['bottom']} left={m['left']} "
            f"(spread {spread}px, avg {avg:.1f}px)"
        )

    if not center_top_is_clear(arr, bg):
        errors.append("Top center is not clear background; horseshoe apex may be clipped")

    # Edge strip must stay background-only.
    edge = min(m["top"], m["bottom"], m["left"], m["right"]) // 2
    edge = max(8, edge)
    if mask[:edge, :].any():
        errors.append("Content detected in top edge strip")
    if mask[-edge:, :].any():
        errors.append("Content detected in bottom edge strip")
    if mask[:, :edge].any():
        errors.append("Content detected in left edge strip")
    if mask[:, -edge:].any():
        errors.append("Content detected in right edge strip")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Riser screenshot validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"OK: {IMAGE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
