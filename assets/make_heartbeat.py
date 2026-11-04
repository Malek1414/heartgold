"""Turn the static golden-heart logo into a pumping-heart GIF (lub-dub beat, then rest).

Only the heart moves: it is cut out of the dark tile by brightness, holes filled, edges feathered, and scaled up
around its own center on each beat. Run: python assets/make_heartbeat.py <source.png>
"""
import math, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/heartgold-logo.png")
OUT = Path(__file__).parent / "heartgold-logo-animated.gif"
SIZE = 420           # output width/height in px
FRAMES = 36          # frames per heartbeat cycle
FRAME_MS = 40        # 36 x 40 ms = 1.44 s per cycle (about 42 beats/min, a calm resting pulse)

src = Image.open(SRC).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
rgb = np.asarray(src).astype(np.float32)

# 1) heart mask: gold pixels are bright and warm; the tile is near-black
r, g, b, a = rgb[..., 0], rgb[..., 1], rgb[..., 2], rgb[..., 3]
gold = ((r > 70) & (r - b > 25) & (a > 200)).astype(np.uint8) * 255
mask = Image.fromarray(gold, "L").filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
# fill holes (dark creases inside the heart): flood the outside from a corner, everything else is heart
inv = ImageChops.invert(mask).convert("L")
ImageDraw.floodfill(inv, (2, 2), 128)
heart_mask = Image.fromarray(np.where(np.asarray(inv) == 128, 0, 255).astype(np.uint8), "L")
heart_mask = heart_mask.filter(ImageFilter.GaussianBlur(1.6))

# 2) background tile without the heart: fill the heart area with the tile's own dark colour
tile = np.asarray(src).copy()
dark = rgb[(a > 250) & (r < 45) & (g < 45) & (b < 45)][:, :3]
fill = np.median(dark, axis=0).astype(np.uint8) if len(dark) else np.array([20, 18, 20], np.uint8)
hm = np.asarray(heart_mask) > 10
tile[hm, :3] = fill
tile = Image.fromarray(tile, "RGBA")

heart = src.copy()
heart.putalpha(ImageChops.multiply(src.getchannel("A"), heart_mask))
bbox = heart_mask.getbbox()
cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2


def beat(t):
    """Scale over one cycle: a strong 'lub', a softer 'dub', then rest. Always >= 1 so the tile never shows."""
    def pulse(center, width, height):
        return height * math.exp(-((t - center) / width) ** 2)
    return 1.0 + pulse(0.10, 0.055, 0.075) + pulse(0.30, 0.05, 0.045)


def brighten(img, k):
    if k <= 1.0:
        return img
    arr = np.asarray(img).astype(np.float32)
    arr[..., :3] = np.clip(arr[..., :3] * k, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


frames = []
for i in range(FRAMES):
    s = beat(i / FRAMES)
    w = int(round(SIZE * s))
    big = heart.resize((w, w), Image.LANCZOS)
    big = brighten(big, 1 + (s - 1) * 1.2)          # a little glow on each contraction
    frame = tile.copy()
    ox, oy = int(round(cx - cx * s)), int(round(cy - cy * s))
    frame.alpha_composite(big, (ox, oy)) if ox >= 0 and oy >= 0 else frame.paste(big, (ox, oy), big)
    # keep the rounded-tile shape: nothing outside the original tile
    frame.putalpha(src.getchannel("A"))
    frames.append(frame)

# GIF: shared palette, binary transparency for the rounded corners
pal_frames = []
for f in frames:
    alpha = f.getchannel("A")
    p = f.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    p.paste(255, mask=Image.eval(alpha, lambda v: 255 if v < 128 else 0))
    pal_frames.append(p)
pal_frames[0].save(OUT, save_all=True, append_images=pal_frames[1:], duration=FRAME_MS, loop=0,
                   transparency=255, disposal=2, optimize=False)
print(OUT, f"{OUT.stat().st_size / 1e6:.2f} MB", len(frames), "frames")
