#!/usr/bin/env python3
"""Badge Factory assembler: circle crop → 1371 PNG → optional wide metal rim.

Portable: no repo-specific paths. Requires: pillow, numpy.
"""
from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

DEFAULT_SIZE = 1371
HERE = Path(__file__).resolve().parent
PALETTES = HERE.parent / "recipes" / "rim-palettes.json"


def to_circle(src: Path, size: int = DEFAULT_SIZE) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    a = np.array(im)
    rgb = a[..., :3].astype(np.int16)
    alpha = a[..., 3]
    h, w = alpha.shape
    corners_black = all(
        rgb[y, x].max() <= 25 for y, x in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1))
    )
    near_bg = ((rgb.min(axis=2) >= 248) & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 12)) | (
        alpha < 10
    )
    if corners_black:
        near_bg = near_bg | ((rgb.max(axis=2) <= 18) & (alpha > 200))
    seen = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if near_bg[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if near_bg[y, x] and not seen[y, x]:
                seen[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and near_bg[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    ys, xs = np.where(~seen)
    if len(xs) < 50:
        side = min(w, h)
        x0c = (w - side) // 2
        y0c = (h - side) // 2
    else:
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        side = int(np.ceil(max(max(cx - x0, x1 - cx), max(cy - y0, y1 - cy)) * 2 * 1.005))
        x0c, y0c = int(round(cx - side / 2)), int(round(cy - side / 2))
    pad = max(0, -x0c, -y0c, x0c + side - w, y0c + side - h)
    if pad:
        canvas = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        canvas.paste(im, (pad, pad))
        im = canvas
        x0c += pad
        y0c += pad
    im = im.crop((x0c, y0c, x0c + side, y0c + side)).resize(
        (size, size), Image.Resampling.LANCZOS
    )
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0))
    oa = np.array(out)
    oa[..., 3] = np.minimum(oa[..., 3], np.array(mask))
    return Image.fromarray(oa, "RGBA")


def load_palette(name: str) -> tuple[list[tuple[float, list[int]]], float]:
    data = json.loads(PALETTES.read_text(encoding="utf-8"))
    if name not in data["palettes"]:
        raise SystemExit(f"Unknown rim '{name}'. Choose: {', '.join(data['palettes'])}")
    p = data["palettes"][name]
    stops = [(float(s[0]), list(s[1])) for s in p["stops"]]
    return stops, float(p.get("default_inner_frac", 0.9))


def draw_rim(size: int, inner_frac: float, stops: list[tuple[float, list[int]]]) -> Image.Image:
    R = (size - 1) / 2
    inner_r, outer_r = inner_frac * R, 0.997 * R
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = (size - 1) / 2
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    ring = (dist >= inner_r) & (dist <= outer_r)
    t = np.clip((outer_r - dist) / max(outer_r - inner_r, 1e-6), 0, 1)
    ang = np.arctan2(yy - cy, xx - cx)
    tube = 0.55 + 0.45 * np.sin(np.pi * t)
    light = 0.70 + 0.30 * np.cos(ang - (-2.35))
    shade = tube * light
    stop_t = np.array([s[0] for s in stops], dtype=np.float32)
    cols = np.array([s[1] for s in stops], dtype=np.float32)
    rgba = np.zeros((size, size, 4), dtype=np.float32)
    for ch in range(3):
        rgba[..., ch] = np.clip(np.interp(t, stop_t, cols[:, ch]) * shade, 0, 255)
    rgba[..., 3] = np.where(ring, 255, 0)
    return Image.fromarray(rgba.astype(np.uint8), "RGBA")


def apply_rim(im: Image.Image, palette: str, inner_frac: float | None, strip_frac: float) -> Image.Image:
    size = im.size[0]
    stops, default_inner = load_palette(palette)
    inner = default_inner if inner_frac is None else inner_frac
    a = np.array(im)
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = (size - 1) / 2
    R = min(cx, cy)
    a[np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) > strip_frac * R, 3] = 0
    ys, xs = np.where(a[..., 3] > 10)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    side = max(x1 - x0, y1 - y0)
    cx2, cy2 = (x0 + x1) / 2, (y0 + y1) / 2
    x0c, y0c = int(round(cx2 - side / 2)), int(round(cy2 - side / 2))
    art = Image.fromarray(a, "RGBA").crop((x0c, y0c, x0c + side, y0c + side))
    target = int(round(size * inner))
    scaled = art.resize((target, target), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    off = (size - target) // 2
    canvas.paste(scaled, (off, off), scaled)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((off, off, off + target - 1, off + target - 1), fill=255)
    ca = np.array(canvas)
    ca[..., 3] = np.minimum(ca[..., 3], np.array(mask))
    placed = Image.fromarray(ca, "RGBA")
    rim = draw_rim(size, inner, stops)
    out = Image.alpha_composite(Image.new("RGBA", (size, size), (0, 0, 0, 0)), placed)
    out = Image.alpha_composite(out, rim)
    fmask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(fmask).ellipse((0, 0, size - 1, size - 1), fill=255)
    oa = np.array(out)
    oa[..., 3] = np.minimum(oa[..., 3], np.array(fmask))
    return Image.fromarray(oa, "RGBA")


def main() -> None:
    ap = argparse.ArgumentParser(description="Assemble a print-ready circular badge")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE)
    ap.add_argument("--rim", choices=["gold_wide", "rose_romantic", "olive_bronze", "gunmetal", "silver_chrome"])
    ap.add_argument("--inner", type=float, default=None, help="Inner art radius fraction 0..1")
    ap.add_argument("--strip", type=float, default=0.965, help="Strip old thin rim outside this fraction")
    args = ap.parse_args()
    out = to_circle(args.input, args.size)
    if args.rim:
        out = apply_rim(out, args.rim, args.inner, args.strip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output)
    a = np.array(out)
    print(f"wrote {args.output} {out.size} corners_a={a[0,0,3]} center_a={a[args.size//2,args.size//2,3]}")


if __name__ == "__main__":
    main()
