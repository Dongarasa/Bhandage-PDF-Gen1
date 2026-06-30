"""
draw_hex_q3.py — Draws the Q3 hex-overlap diagram exactly matching the original.
7 flat-top hexagons: 4 top row + 3 bottom row, ~40% horizontal overlap.
Output: PNG with transparent background.
"""

import math
from PIL import Image, ImageDraw

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H = 900, 700    # final size computed after geometry; canvas trimmed at save
img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ── Hex geometry ──────────────────────────────────────────────────────────────
r       = 115            # circumradius
w       = 2 * r          # hex width  (vertex-to-vertex, left-right)
h_half  = int(r * math.sqrt(3) / 2)   # = r*sin60 ≈ 100
LW      = 4                            # stroke width (px)
step_x  = r                           # step = r → lower-right of hex N meets lower-left of hex N+1, zero gap
step_y  = h_half * 2 - LW            # rows overlap by LW, closing any residual junction gap

# ── Row centers ───────────────────────────────────────────────────────────────
# Both rows left-aligned — no horizontal offset between rows
total_top_w = 2 * step_x + w           # = 2r + 2r = 4r
x0   = (W - total_top_w) // 2 + r     # center of first hex

cy_top = H // 2 - step_y // 2
cy_bot = H // 2 + step_y // 2

top_centers = [(x0 + i * step_x, cy_top) for i in range(3)]
bot_centers = [(x0 + i * step_x, cy_bot) for i in range(3)]   # same x0, no offset

# ── Color palette — Info (chapter 3) shades ───────────────────────────────────
LIGHT  = (222, 236, 255, 255)   # Info-200  #DEECFF
MID    = (156, 198, 255, 255)   # Info-400  #9CC6FF
DARK   = ( 84, 146, 241, 255)   # Info-600  #5492F1
STROKE = ( 52, 100, 177, 255)   # Info-800  #3464B1
# LW already defined above

# Shading pattern:
# Top  row (L→R): light, mid, dark
# Bottom row (L→R): dark, light, mid
top_colors = [LIGHT, MID, DARK]
bot_colors = [DARK,  LIGHT, MID]

all_hexes = list(zip(top_centers, top_colors)) + list(zip(bot_centers, bot_colors))

# ── Draw helper ───────────────────────────────────────────────────────────────
def hex_pts(cx, cy, r, h_half):
    """Flat-top hex vertices: right → bottom-right → bottom-left → left → top-left → top-right."""
    return [
        (cx + r,       cy),
        (cx + r // 2,  cy + h_half),
        (cx - r // 2,  cy + h_half),
        (cx - r,       cy),
        (cx - r // 2,  cy - h_half),
        (cx + r // 2,  cy - h_half),
    ]

# Draw each hex as fill+outline together, back-to-front.
# Later hexes cover earlier ones (including their outlines) in overlap areas.
for (cx, cy), color in all_hexes:
    pts = hex_pts(cx, cy, r, h_half)
    draw.polygon(pts, fill=color, outline=STROKE, width=LW)

# ── Trim whitespace + add consistent 20px padding ─────────────────────────────
bbox = img.getbbox()   # (left, top, right, bottom) of non-transparent pixels
PAD  = 20
crop = (bbox[0] - PAD, bbox[1] - PAD, bbox[2] + PAD, bbox[3] + PAD)
img  = img.crop(crop)

out = "personal/workspace/illustrate/props/hex-overlap-q3.png"
img.save(out)
print(f"Saved: {out}  ({img.width}×{img.height}px)")
