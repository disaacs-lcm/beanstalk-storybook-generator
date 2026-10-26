"""Generate the tiling surface textures in static/textures/.

Every texture is built from noise filtered in the frequency domain, which makes it tile seamlessly.
Run from the repo root (needs numpy and pillow, dev-only):  python tools/make_textures.py
"""
import os

import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "textures")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(368)


def noise(n, sx, sy=None):
    """Seamless Gaussian-filtered noise, normalized to 0..1. sx/sy are blur sizes in pixels (anisotropic if they differ)."""
    sy = sx if sy is None else sy
    f = np.fft.fftfreq(n)
    fy, fx = np.meshgrid(f, f, indexing="ij")
    g = np.exp(-2 * np.pi ** 2 * ((sx * fx) ** 2 + (sy * fy) ** 2))
    out = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * g))
    return (out - out.min()) / (out.max() - out.min())


def emboss(h, strength):
    """Light a height map from the top left, wrapping at the edges so it stays seamless."""
    dx = h - np.roll(h, 1, axis=1)
    dy = h - np.roll(h, 1, axis=0)
    light = -(dx + dy)
    light = light / (np.abs(light).max() + 1e-9)
    return np.clip(1 + strength * light, 0, 1)


def save_gray(name, v):
    Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8), "L").save(os.path.join(OUT, name), optimize=True)


def speckles(n, density, depth):
    s = np.ones((n, n))
    mask = rng.random((n, n)) < density
    s[mask] -= depth * rng.random(mask.sum())
    return s


# Cold-press paper tooth: for cards, page paper, and over the art so pages look printed. Multiplied, so near white.
n = 384
h = 0.55 * noise(n, 1.1) + 0.45 * noise(n, 3.5)
save_gray("paper.png", 0.9 + 0.1 * emboss(h, 0.9) * speckles(n, 0.004, 0.25))

# Parchment desk (colored): two-tone mottling, age stains, foxing spots, fibers, and tooth. Large tile so it doesn't visibly repeat.
n = 1024
mottle = 0.5 * noise(n, 90) + 0.3 * noise(n, 28) + 0.2 * noise(n, 8)
stains = np.clip((noise(n, 70) - 0.6) * 3.2, 0, 1) ** 1.5           # broad darker tide marks
fibers = np.clip((noise(n, 18, 0.9) - 0.6) * 3.5, 0, 1)             # long horizontal fibers
fibers2 = np.clip((noise(n, 0.9, 12) - 0.64) * 3.5, 0, 1)           # a few crossing ones
fox = np.clip((noise(n, 2.2) - 0.83) * 9, 0, 1) * np.clip((noise(n, 50) - 0.45) * 3, 0, 1)  # small age spots, in clusters
tooth = emboss(0.6 * noise(n, 1.3) + 0.4 * noise(n, 4), 0.9)
t = np.clip(0.38 * mottle + 0.38 * stains + 0.12 * fibers + 0.06 * fibers2 + 0.5 * fox, 0, 1)
light = np.array([0xF8, 0xF0, 0xDC]) / 255
dark = np.array([0xD6, 0xBF, 0x93]) / 255
foxc = np.array([0xB8, 0x8F, 0x5E]) / 255
rgb = light + (dark - light) * t[..., None]
rgb = rgb + (foxc - rgb) * (0.55 * fox)[..., None]
rgb = rgb * (0.9 + 0.1 * tooth)[..., None] * speckles(n, 0.0008, 0.3)[..., None]
Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB").save(os.path.join(OUT, "parchment.jpg"), quality=88, optimize=True)

# Linen book cloth for the hardcover: an over-under weave with uneven threads.
n, p = 256, 4
yy, xx = np.mgrid[0:n, 0:n]
row_w = 0.75 + 0.25 * rng.random(n)  # each weft thread a slightly different thickness
col_w = 0.75 + 0.25 * rng.random(n)
warp = 0.5 + 0.5 * np.cos(2 * np.pi * (xx % p) / p) * col_w[xx]
weft = 0.5 + 0.5 * np.cos(2 * np.pi * (yy % p) / p) * row_w[yy]
over = ((xx // p) + (yy // p)) % 2 == 0
weave = np.where(over, warp, weft)
save_gray("linen.png", 0.8 + 0.2 * (0.75 * weave + 0.25 * noise(n, 1.0)))

# Grosgrain ribbon: fine horizontal ribs.
n = 96
yy, xx = np.mgrid[0:n, 0:n]
ribs = 0.5 + 0.5 * np.cos(2 * np.pi * yy / 3)
save_gray("grosgrain.png", 0.78 + 0.22 * (0.8 * ribs + 0.2 * noise(n, 0.8)))

# Laid paper for the bookplate: fine laid lines and wider-spaced chain lines.
n = 240
yy, xx = np.mgrid[0:n, 0:n]
laid = 0.5 + 0.5 * np.cos(2 * np.pi * yy / 3)
chain = np.exp(-(((xx % 24) - 12) ** 2) / 2.0)
save_gray("laid.png", (1 - 0.035 * laid - 0.05 * chain) * (0.95 + 0.05 * emboss(noise(n, 1.2), 0.8)))

# Brushed metal for the gilt frame and plaque: long horizontal streaks.
n = 256
save_gray("brushed.png", 0.78 + 0.22 * (0.7 * noise(n, 40, 0.6) + 0.3 * noise(n, 8, 0.5)))

# Masking tape: crinkled fibers.
n = 192
save_gray("tape.png", 0.82 + 0.18 * (0.6 * noise(n, 6, 0.8) + 0.4 * emboss(noise(n, 2.5), 0.9)))

for f in sorted(os.listdir(OUT)):
    print(f"{f:16} {os.path.getsize(os.path.join(OUT, f)) // 1024} KB")
