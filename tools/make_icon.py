# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
"""Derive transparent idle/transfer icons from the approved brand artwork."""
from __future__ import annotations

from math import hypot
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
CANVAS_SIZE = 512
CYAN = (20, 218, 221)
BLUE = (36, 84, 171)
RED = (255, 75, 85)
DARK_RED = (181, 39, 56)
MARK_FILL = 0.70
TILE_FILL = 0.92
TILE_RADIUS = 0.24
TILE_NAVY = (4, 20, 47)
TILE_GLOW = (13, 47, 91)


def render() -> Image.Image:
    source_path = ROOT / "assets" / "microglow-logo.png"
    with Image.open(source_path) as source:
        source = source.convert("RGBA")
        side = min(int(source.width * 0.70), int(source.height * 0.78))
        left = int(source.width * 0.15)
        # Segment at the artwork's native resolution. Only the final icon is
        # resized; the old extra 514→512 pass softened and rang its edges.
        return source.crop((left, 0, left + side, side))


def _fit_mark(idle: Image.Image, transfer: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Fit the original mark inside the restored tile without distortion."""
    bounds = idle.getchannel("A").getbbox()
    if bounds is None:
        return idle, transfer
    target = round(CANVAS_SIZE * MARK_FILL)
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    scale = target / max(width, height)
    new_size = (round(width * scale), round(height * scale))

    enlarged = []
    for frame in (idle, transfer):
        artwork = frame.crop(bounds).resize(new_size, Image.Resampling.BICUBIC)
        canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
        canvas.paste(artwork, ((CANVAS_SIZE - new_size[0]) // 2,
                               (CANVAS_SIZE - new_size[1]) // 2))
        enlarged.append(canvas)
    enlarged[1].putalpha(enlarged[0].getchannel("A"))
    return enlarged[0], enlarged[1]


def _rounded_tile() -> Image.Image:
    """Deep navy tile with clean transparent corners, even on light taskbars."""
    gradient = Image.radial_gradient("L").resize((CANVAS_SIZE, CANVAS_SIZE),
                                                  Image.Resampling.BICUBIC)
    tile = ImageOps.colorize(gradient, black=TILE_NAVY, white=TILE_GLOW).convert("RGBA")
    scale = 4
    pad = round(CANVAS_SIZE * (1 - TILE_FILL) / 2)
    mask = Image.new("L", (CANVAS_SIZE * scale, CANVAS_SIZE * scale), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((pad * scale, pad * scale,
                            (CANVAS_SIZE - pad) * scale - 1,
                            (CANVAS_SIZE - pad) * scale - 1),
                           radius=round(CANVAS_SIZE * TILE_RADIUS * scale), fill=255)
    tile.putalpha(mask.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS))
    return tile


def render_frames() -> tuple[Image.Image, Image.Image]:
    """Restore the navy tile; idle is cyan and transfer is red.

    The navy circle immediately behind the core becomes a small coloured halo,
    so the white point stays visible. Only the rounded corners are transparent.
    """
    source = render().convert("RGB")
    idle = Image.new("RGBA", source.size, (0, 0, 0, 0))
    transfer = Image.new("RGBA", source.size, (0, 0, 0, 0))
    original = source.load()
    normal = idle.load()
    swapped = transfer.load()
    cx = cy = source.width / 2

    for y in range(source.height):
        for x in range(source.width):
            red, green, blue = original[x, y]
            radius = hypot(x - cx, y - cy)
            # Green/cyan chroma separates the strokes from the dark tile and
            # white canvas. The gradual edge preserves antialiasing.
            stroke = max(0, min(255, (green - 110) * 3,
                                (green - red - 40) * 4,
                                (blue - red - 30) * 4))
            # Restrict the white mask to the central point; the source canvas
            # is also white and must never become part of the icon.
            white = int(max(0, min(255, (min(red, green, blue) - 155) * 3,
                                   (43 - radius) * 24)))
            halo = int(max(0, min(230, (73 - radius) * 20)))
            alpha = max(stroke, white, halo)
            if not alpha:
                continue
            if white >= stroke and white >= halo:
                normal[x, y] = (255, 255, 255, alpha)
                swapped[x, y] = (255, 255, 255, alpha)
            elif stroke >= halo:
                normal[x, y] = (*CYAN, alpha)
                swapped[x, y] = (*RED, alpha)
            else:
                normal[x, y] = (*BLUE, alpha)
                swapped[x, y] = (*DARK_RED, alpha)
    idle_mark, transfer_mark = _fit_mark(idle, transfer)
    tile = _rounded_tile()
    return Image.alpha_composite(tile, idle_mark), Image.alpha_composite(tile, transfer_mark)


def main() -> int:
    directory = ROOT / "assets"
    directory.mkdir(parents=True, exist_ok=True)
    idle, transfer = render_frames()
    idle.save(directory / "microglow-icon-idle.png")
    transfer.save(directory / "microglow-icon-transfer.png")
    target = directory / "app.ico"
    idle.save(target, format="ICO", sizes=SIZES)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
