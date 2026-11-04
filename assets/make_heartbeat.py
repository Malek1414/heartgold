"""Animate the golden-heart logo with a physiologically ordered cardiac cycle (72 bpm, one loop = one beat).

Each anatomical part of the image gets its own smooth displacement field, timed to the real cycle:

  phase (fraction of a 0.83 s beat)      what moves
  0.00-0.13  atrial systole (P wave)     both atria squeeze toward their centres ("atrial kick")
  0.13-0.40  ventricular systole         ventricles narrow; the base (AV groove) is pulled DOWN toward the
                                         apex, which stays almost still; the ventricles wring (twist);
                                         the atria stretch and fill
  0.17-0.50  ejection pressure wave      aortic arch and pulmonary trunk bulge, then recoil, with a small
                                         second bump (dicrotic notch, when the aortic valve closes)
  0.40-0.60  rapid ventricular filling   ventricles spring back, the base rises, the atria empty
  0.60-1.00  diastasis                   rest, slow filling

Run: python assets/make_heartbeat.py ~/Desktop/golden-heart-app-icon-v2.png
"""
import math, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/heartgold-logo.png")
OUT = Path(__file__).parent / "heartgold-logo-animated.gif"
OUT_SIZE = 440
BPM = 72
FRAME_MS = 30
N = round(60000 / BPM / FRAME_MS)       # frames per beat (28 at 72 bpm, 30 ms)
AMP = 1.0                                # global motion amplitude (1.0 = clearly visible, still anatomical)

img = cv2.imread(str(SRC), cv2.IMREAD_UNCHANGED)                     # BGRA, 1254 x 1254
H, W = img.shape[:2]
k = W / 1254.0                                                       # landmarks below are in 1254-px space

# ---------------------------------------------------------------- landmarks (from the annotated logo)
RA = (360 * k, 560 * k, 135 * k)        # right atrium: the lumpy lobe on the viewer's left
LA = (865 * k, 505 * k, 100 * k)        # left atrial appendage: the small lobe on the viewer's right
BASE_Y = 615 * k                        # AV groove: atria above, ventricles below
APEX = (590 * k, 1150 * k)
V_CX = 615 * k                          # ventricular long axis (x)
ARCH = (660 * k, 260 * k, 150 * k)      # aortic arch and its branches
PULM = (720 * k, 400 * k, 95 * k)       # pulmonary trunk

# ---------------------------------------------------------------- separate the heart from the tile
b, g, r, a = [img[..., i].astype(np.float32) for i in range(4)]
gold = ((r > 70) & (r - b > 25) & (a > 200)).astype(np.uint8) * 255
gold = cv2.morphologyEx(gold, cv2.MORPH_CLOSE, np.ones((17, 17), np.uint8))
flood = gold.copy()
cv2.floodFill(flood, np.zeros((H + 2, W + 2), np.uint8), (2, 2), 128)
heart_mask = np.where(flood == 128, 0, 255).astype(np.uint8)          # holes (dark creases) filled
heart_alpha = cv2.GaussianBlur(heart_mask, (0, 0), 2.0)

# tile without the heart: inpaint the heart area so the dark gradient continues underneath
tile = img.copy()
tile[..., :3] = cv2.inpaint(img[..., :3], cv2.dilate(heart_mask, np.ones((15, 15), np.uint8)), 25, cv2.INPAINT_TELEA)

heart = img.copy()
heart[..., 3] = (heart_alpha.astype(np.float32) * a / 255).astype(np.uint8)

# ---------------------------------------------------------------- region weights (smooth, 0..1)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def blob(cx, cy, s):
    return np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s)))


def ramp(v, lo, hi):
    return np.clip((v - lo) / (hi - lo), 0, 1)


w_ra, w_la = blob(*RA), blob(*LA)
w_vent = ramp(yy, BASE_Y - 60 * k, BASE_Y + 90 * k) * (1 - 0.6 * np.maximum(w_ra, w_la))
w_arch = blob(*ARCH)
w_pulm = blob(*PULM)
# how much of the base's downward travel each height receives: full at the AV groove, fading to the tip
# (the apex barely moves) and fading upward into the great vessels (anchored to the body)
long_w = np.where(yy >= BASE_Y, 1 - ramp(yy, BASE_Y, APEX[1]), 1 - 0.55 * ramp(BASE_Y - yy, 0, BASE_Y - 90 * k))


# ---------------------------------------------------------------- the cardiac cycle (t in [0, 1))
def smooth(t, a0, a1):
    x = min(max((t - a0) / (a1 - a0), 0.0), 1.0)
    return x * x * (3 - 2 * x)


def bump(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


def phases(t):
    atrial_kick = bump(t, 0.07, 0.04)
    ventricle = smooth(t, 0.13, 0.33) - smooth(t, 0.42, 0.60)              # contraction 0..1
    pressure = smooth(t, 0.17, 0.27) * (math.exp(-max(t - 0.27, 0) / 0.11) if t > 0.27 else 1)
    pressure += 0.18 * bump(t, 0.46, 0.022)                                 # dicrotic notch
    atrial_fill = smooth(t, 0.18, 0.40) * (1 - smooth(t, 0.44, 0.62))       # atria swell while AV valves closed
    return atrial_kick, ventricle, pressure, atrial_fill


def displacement(t):
    kick, V, P, fill = phases(t)
    dx = np.zeros((H, W), np.float32)
    dy = np.zeros((H, W), np.float32)
    # atria: squeeze toward their centres on the kick, swell while filling
    for (cx, cy, _), w in ((RA, w_ra), (LA, w_la)):
        s = (-0.11 * kick + 0.05 * fill) * AMP
        dx += (xx - cx) * s * w
        dy += (yy - cy) * s * w
    # ventricles: narrow toward the long axis (walls thicken, cavity empties)
    dx += -(xx - V_CX) * 0.08 * V * AMP * w_vent
    # longitudinal shortening: the AV plane descends toward the apex, which stays put
    dy += (APEX[1] - BASE_Y) * 0.085 * V * AMP * long_w
    # wringing twist: the lower ventricle turns relative to the base
    twist = 0.06 * V * AMP * ramp(yy, BASE_Y, APEX[1])
    dx += -(yy - BASE_Y) * twist * 0.25 * w_vent
    # great arteries: bulge on ejection, recoil, notch
    for (cx, cy, _), w, s in ((ARCH, w_arch, 0.06), (PULM, w_pulm, 0.07)):
        dx += (xx - cx) * s * P * AMP * w
        dy += (yy - cy) * s * P * AMP * w - 6 * k * P * AMP * w
    return dx, dy


# ---------------------------------------------------------------- render
frames = []
for i in range(N):
    dx, dy = displacement(i / N)
    warped = cv2.remap(heart, xx - dx, yy - dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    al = warped[..., 3:4].astype(np.float32) / 255
    out = tile.astype(np.float32)
    out[..., :3] = warped[..., :3] * al + out[..., :3] * (1 - al)
    out[..., 3] = img[..., 3]                                                # keep the rounded tile shape
    rgba = cv2.cvtColor(out.astype(np.uint8), cv2.COLOR_BGRA2RGBA)
    frames.append(Image.fromarray(rgba).resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS))

pal = []
for f in frames:
    p = f.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    p.paste(255, mask=f.getchannel("A").point(lambda v: 255 if v < 128 else 0))
    pal.append(p)
pal[0].save(OUT, save_all=True, append_images=pal[1:], duration=FRAME_MS, loop=0, transparency=255, disposal=2)
print(f"{OUT}  {OUT.stat().st_size / 1e6:.2f} MB  {N} frames x {FRAME_MS} ms = {N * FRAME_MS} ms/beat ({BPM} bpm)")
