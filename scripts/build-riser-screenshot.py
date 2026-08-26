#!/usr/bin/env python3
"""Build the Riser Manager screenshot from the Chorus Tools landing canvas."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://www.chorus-tools.com/landing/riser-canvas.png"
SOURCE_PATH = ROOT / "assets" / ".riser-canvas-source.png"
OUTPUT_PATH = ROOT / "assets" / "chorus-tools-riser.png"

CONTENT_THRESHOLD = 12
PADDING_RATIO = 0.08
MIN_PADDING = 72


def download_source() -> None:
    if SOURCE_PATH.exists():
        return
    try:
        import urllib.request

        req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp, SOURCE_PATH.open("wb") as out:
            out.write(resp.read())
    except Exception as exc:  # pragma: no cover - network optional in CI if cached
        if not SOURCE_PATH.exists():
            raise SystemExit(f"Missing source image and download failed: {exc}") from exc


def content_mask(arr: np.ndarray, bg: np.ndarray) -> np.ndarray:
    diff = np.abs(arr.astype(int) - bg).sum(axis=2)
    mask = diff > CONTENT_THRESHOLD

    # Mask only corner nav chrome; the horseshoe apex extends above y=78 in the center.
    nav = np.zeros(mask.shape, dtype=bool)
    nav[:90, :240] = True
    nav[:90, 1200:] = True
    mask[nav] = False
    return mask


def build() -> tuple[int, int]:
    download_source()
    src = Image.open(SOURCE_PATH).convert("RGB")
    arr = np.array(src)
    bg = arr[0, 0]

    mask = content_mask(arr, bg)
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        raise SystemExit("Could not detect riser content in source image")

    top, bottom = int(rows[0]), int(rows[-1])
    left, right = int(cols[0]), int(cols[-1])
    riser = src.crop((left, top, right + 1, bottom + 1))

    pad = max(MIN_PADDING, int(max(riser.size) * PADDING_RATIO))
    out = Image.new("RGB", (riser.width + 2 * pad, riser.height + 2 * pad), tuple(bg))
    out.paste(riser, (pad, pad))
    out.save(OUTPUT_PATH, optimize=True)
    return out.size


if __name__ == "__main__":
    size = build()
    print(f"Wrote {OUTPUT_PATH} ({size[0]}x{size[1]})")
