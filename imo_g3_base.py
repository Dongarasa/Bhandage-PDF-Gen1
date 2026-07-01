"""
imo_g3_base.py — Shared base module for IMO LR G3 PDF generator.

Stack: PIL (Pillow) + img2pdf at 300 DPI.
Usage:
    from imo_g3_base import *
    import imo_g3_base as _b

    setup(ch_num, ch_name, pg_num)  # must be first
    temp1_header()                  # or temp2/3/4
    y = CONTENT_TOP_T1
    ...
    finish("imo-g3-ch03-page-01", y)
"""

import os
import io
from PIL import Image, ImageDraw, ImageFont

# ─── Resolution ───────────────────────────────────────────────────────────────
DPI   = 300
SCALE = DPI / 72      # ≈ 4.1667

W = int(210 * DPI / 25.4)   # 2480 px  (A4 width)
H = int(297 * DPI / 25.4)   # 3508 px  (A4 height)

def px(pt):   return int(pt * SCALE)         # points → pixels
def mm(val):  return int(val * DPI / 25.4)   # mm → pixels
def fig(p72): return int(p72 * SCALE)        # Figma 72-DPI px → 300-DPI px

# ─── Colors (Cuemath design-system tokens) ────────────────────────────────────
BG_PAGE   = (250, 241, 230)   # gold-100   #FAF1E6
WHITE     = (255, 255, 255)
CHARCOAL  = (49,  49,  49)    # #313131
TEXT_DARK = (29,  28,  27)    # neutral-1100 #1D1C1B
WARM_GREY = (132, 128, 123)   # neutral-600  #84807B
MED_GREY  = (91,  88,  84)    # neutral-700  #5B5854

# Chapter color cycling — one Cuemath token per slot
CHAPTER_COLORS = {
    0: (244, 171,  82),   # gold-500    #F4AB52  Ch 1, 5, 9…
    1: (249, 114, 121),   # error-500   #F97279  Ch 2, 6, 10…
    2: (116, 172, 252),   # info-500    #74ACFC  Ch 3, 7, 11…
    3: (106, 200, 138),   # success-500 #6AC88A  Ch 4, 8, 12…
}
CHAPTER_BADGE_BG = {
    0: (250, 214, 172),   # gold-300    #FAD6AC
    1: (255, 184, 183),   # error-300   #FFB8B7
    2: (193, 220, 255),   # info-300    #C1DCFF
    3: (188, 234, 200),   # success-300 #BCEAC8
}
CHAPTER_PAGE_BG = {
    0: (250, 241, 230),   # gold-100    #FAF1E6
    1: (255, 233, 233),   # error-100   #FFE9E9
    2: (238, 246, 255),   # info-100    #EEF6FF
    3: (236, 249, 239),   # success-100 #ECF9EF
}
CHAPTER_TABLE_BG = {
    0: (250, 230, 208),   # gold-200    #FAE6D0
    1: (255, 214, 213),   # error-200   #FFD6D5
    2: (222, 236, 255),   # info-200    #DEECFF
    3: (218, 243, 224),   # success-200 #DAF3E0
}
CHAPTER_TABLE_BOR = {
    0: (206, 126,  18),   # gold-700    #CE7E12
    1: (200,  68,  79),   # error-700   #C8444F
    2: ( 64, 123, 214),   # info-700    #407BD6
    3: ( 40, 153,  90),   # success-700 #28995A
}

def chapter_color(n):     return CHAPTER_COLORS[(n - 1) % 4]
def chapter_badge_bg(n):  return CHAPTER_BADGE_BG[(n - 1) % 4]
def chapter_table_bg(n):  return CHAPTER_TABLE_BG[(n - 1) % 4]
def chapter_table_bor(n): return CHAPTER_TABLE_BOR[(n - 1) % 4]
def chapter_page_bg(n):  return CHAPTER_PAGE_BG[(n - 1) % 4]

# ─── Layout Constants ─────────────────────────────────────────────────────────
MARGIN      = fig(40)       # 167 px — all sides
LEFT        = MARGIN
RIGHT_EDGE  = W - MARGIN
CONTENT_W   = RIGHT_EDGE - LEFT
CONTENT_BOT = H - MARGIN

TOP_BAR_H_T12 = fig(92)    # Temp1/2 full bar height
TOP_BAR_H_T3  = fig(92)    # Temp3 L-shape (tall part)
TOP_BAR_H_T4  = fig(12)    # Temp4 thin strip

CONTENT_TOP_T1  = fig(120)  # Temp1/2 content start Y
CONTENT_TOP_T34 = fig(96)   # Temp3/4 content start Y

Q_BADGE_W   = fig(28)       # 117 px
Q_TEXT_X    = fig(84)       # 350 px
Q_CONTENT_W = RIGHT_EDGE - Q_TEXT_X

# Intro indentation levels (Figma absolute left positions)
INTRO_L0 = fig(40)    # headings, Type I: label, Answer:
INTRO_L1 = fig(87)    # type description text
INTRO_L2 = fig(154)   # Example label, table, example options, Answer indent

GRADE_BADGE_W      = fig(66)   # pill width and height
GRADE_BADGE_RADIUS = fig(40)   # capsule radius

SEP_Y  = fig(68)              # horizontal rule Y for Temp3/4
LOGO_W = fig(80)              # logo render width  (Figma: 79.61px)
LOGO_X = W - fig(24) - LOGO_W # right margin 24px (Figma: right=24.39px)
LOGO_Y = fig(32)              # Figma: top=32px

# ─── Project root (absolute) ──────────────────────────────────────────────────
_SCRIPTS_DIR  = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPTS_DIR, "..", "..", "..", ".."))
_LOGO_PNG     = os.path.join(_SCRIPTS_DIR, "..", "assets",
                              "cuemath-wordmark-tagline.png")
_FONT_DIR     = os.path.expanduser("~/Library/Fonts")

# ─── Module globals (set by setup()) ─────────────────────────────────────────
canvas   = None
draw     = None
ch_color = None
CH_NUM   = None
CH_NAME  = None
PG_NUM   = None
F        = {}

# ─── Font loading ─────────────────────────────────────────────────────────────
def _load_fonts():
    global F

    def fnt(name, size_pt):
        path = os.path.join(_FONT_DIR, name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Font not found: {path}")
        return ImageFont.truetype(path, px(size_pt))

    F = {
        "ch_num":    fnt("Athletics-Regular.otf",    14),
        "ch_title":  fnt("Athletics-Light.otf",      24),
        "ch_big":    fnt("Athletics-Black.otf",       32),
        "grade":     fnt("Athletics-Regular.otf",    12),
        "sec_head":  fnt("UntitledSans-Medium.otf",     14),
        "sub_head":  fnt("UntitledSans-Medium.otf",  12),
        "body":      fnt("UntitledSans-Regular.otf", 12),
        "q_badge":   fnt("UntitledSans-Regular.otf", 12),
        "q_text":    fnt("UntitledSans-Regular.otf", 12),
        "direction": fnt("UntitledSans-Regular.otf", 12),
        "opt_label": fnt("UntitledSans-Regular.otf", 12),
        "opt_text":  fnt("UntitledSans-Regular.otf", 12),
        "footer":    fnt("UntitledSans-Regular.otf", 10),
        "pagenum":   fnt("UntitledSans-Regular.otf", 11),
        "medium":    fnt("UntitledSans-Medium.otf",  12),
    }

# ─── Logo ─────────────────────────────────────────────────────────────────────
_logo_cache = None

def _get_logo():
    global _logo_cache
    if _logo_cache is not None:
        return _logo_cache
    try:
        path = os.path.normpath(_LOGO_PNG)
        raw  = Image.open(path).convert("RGBA")
        # Resize to target width preserving aspect ratio
        aspect = raw.height / raw.width
        target_h = int(LOGO_W * aspect)
        _logo_cache = raw.resize((LOGO_W, target_h), Image.LANCZOS)
    except Exception as e:
        print(f"[warn] Logo load failed ({e}), skipping.")
        _logo_cache = None
    return _logo_cache

def draw_logo(img):
    logo = _get_logo()
    if logo is None:
        return
    img.paste(logo, (LOGO_X, LOGO_Y), mask=logo.split()[3])

# ─── Setup / Finish ───────────────────────────────────────────────────────────
def setup(ch_num, ch_name, pg_num):
    """Initialise canvas. Must be called before any drawing."""
    global canvas, draw, ch_color, CH_NUM, CH_NAME, PG_NUM
    CH_NUM   = ch_num
    CH_NAME  = ch_name
    PG_NUM   = pg_num
    ch_color = chapter_color(ch_num)
    bg       = chapter_page_bg(ch_num)
    canvas   = Image.new("RGBA", (W, H), (*bg, 255))
    draw     = ImageDraw.Draw(canvas)
    _load_fonts()


def finish(filename, y=None, out_dir=None):
    """Draw footer + page number, export PNG → img2pdf → PDF. Returns pdf path."""
    import img2pdf

    if out_dir is None:
        out_dir = os.path.join(_PROJECT_ROOT, "personal/workspace/pdf-gen")
    os.makedirs(out_dir, exist_ok=True)

    _draw_footer()

    # Flatten RGBA → RGB on white
    bg = Image.new("RGB", canvas.size, (255, 255, 255))
    bg.paste(canvas, mask=canvas.split()[3])

    png_path = os.path.join(out_dir, f"{filename}.png")
    pdf_path = os.path.join(out_dir, f"{filename}.pdf")
    bg.save(png_path, dpi=(DPI, DPI))

    a4 = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
    with open(pdf_path, "wb") as f_out:
        f_out.write(img2pdf.convert(png_path, layout_fun=img2pdf.get_layout_fun(a4)))

    os.remove(png_path)
    print(pdf_path, flush=True)
    return pdf_path


def _draw_footer():
    footer_left = "© Cue Learn Pvt. Ltd." if PG_NUM % 2 == 1 else "Grade 3: Logical Reasoning"
    footer_y    = H - MARGIN + px(10)
    draw.text((LEFT,       footer_y), footer_left, font=F["footer"],  fill=(*MED_GREY, 255))
    draw.text((RIGHT_EDGE, footer_y), str(PG_NUM),  font=F["pagenum"], fill=(*CHARCOAL, 255), anchor="ra")

# ─── Template Headers ─────────────────────────────────────────────────────────

def temp1_header():
    """Chapter intro — full bar + grade pill badge."""
    badge_h = GRADE_BADGE_W  # square pill
    badge_x = W - fig(24) - GRADE_BADGE_W
    badge_y = (TOP_BAR_H_T12 - badge_h) // 2

    draw.rectangle([(0, 0), (W, TOP_BAR_H_T12)], fill=(*ch_color, 255))
    draw.text((LEFT, fig(24)), f"Chapter {CH_NUM}", font=F["ch_num"],   fill=(*CHARCOAL, 255))
    draw.text((LEFT, fig(44)), CH_NAME,             font=F["ch_title"], fill=(*CHARCOAL, 255))

    badge_bg = chapter_badge_bg(CH_NUM)
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + GRADE_BADGE_W, badge_y + badge_h],
        radius=GRADE_BADGE_RADIUS, fill=(*badge_bg, 255))
    cx = badge_x + GRADE_BADGE_W // 2
    draw.text((cx, badge_y + fig(18)), "Grade", font=F["grade"],   fill=(*CHARCOAL, 255), anchor="mm")
    draw.text((cx, badge_y + fig(44)), "3",     font=F["ch_big"],  fill=(*CHARCOAL, 255), anchor="mm")


def temp2_header(section_label):
    """MCQ / CA opener — full bar, section label inside."""
    draw.rectangle([(0, 0), (W, TOP_BAR_H_T12)], fill=(*ch_color, 255))
    draw.text((LEFT, fig(24)), f"Chapter {CH_NUM}: {CH_NAME}", font=F["ch_num"],   fill=(*CHARCOAL, 255))
    draw.text((LEFT, fig(44)), section_label,                   font=F["ch_title"], fill=(*CHARCOAL, 255))


def _cubic_bezier(p0, p1, p2, p3, steps=24):
    """Approximate a cubic bezier with `steps` line segments. Returns list of (x,y) ints."""
    pts = []
    for i in range(steps + 1):
        t  = i / steps
        u  = 1 - t
        x  = u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0]
        y  = u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1]
        pts.append((int(round(x)), int(round(y))))
    return pts


def temp3_header():
    """
    L-shaped accent drawn with PIL polygon (bezier approximation).
    Matches Figma SVG path:
      M0 0 L595 0 L595 12 L40 12
      C28.95 12 20 20.95 20 32  L20 72
      C20 83.05 11.05 92 0 92 Z
    All coordinates scaled fig() to 300 DPI.
    """
    # Key points (Figma px → 300 DPI via fig())
    poly = []
    poly += [(0, 0), (W, 0), (W, fig(12)), (fig(40), fig(12))]
    # Inner curve: top-right of left strip
    poly += _cubic_bezier(
        (fig(40), fig(12)),
        (fig(29), fig(12)),
        (fig(20), fig(21)),
        (fig(20), fig(32)),
    )
    poly += [(fig(20), fig(72))]
    # Outer curve: bottom of left strip
    poly += _cubic_bezier(
        (fig(20), fig(72)),
        (fig(20), fig(83)),
        (fig(11), fig(92)),
        (0,       fig(92)),
    )
    draw.polygon(poly, fill=(*ch_color, 255))
    draw_logo(canvas)
    draw.line([(fig(40), SEP_Y), (W - fig(16), SEP_Y)], fill=(*CHARCOAL, 50), width=max(1, px(1)))


def temp4_header():
    """Thin strip (12 pt) + logo + separator."""
    draw.rectangle([(0, 0), (W, TOP_BAR_H_T4)], fill=(*ch_color, 255))
    draw_logo(canvas)
    draw.line([(fig(40), SEP_Y), (W - fig(16), SEP_Y)], fill=(*CHARCOAL, 50), width=max(1, px(1)))

# ─── Text utilities ───────────────────────────────────────────────────────────

def _line_h(font):
    """Height of one line of text."""
    return draw.textbbox((0, 0), "Ag", font=font)[3]


def draw_wrapped(y, text, font, color, x=None, max_w=None, line_gap=None):
    """Wrap and draw text. Returns y after last line."""
    if x      is None: x      = LEFT
    if max_w  is None: max_w  = CONTENT_W
    if line_gap is None: line_gap = fig(5)

    words = text.split()
    lines, line = [], ""
    for w in words:
        candidate = (line + " " + w).strip()
        if draw.textlength(candidate, font=font) <= max_w:
            line = candidate
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)

    lh = _line_h(font)
    for ln in lines:
        draw.text((x, y), ln, font=font, fill=(*color, 255))
        y += lh + line_gap
    return y

# ─── Theory helpers (Temp1 intro content) ─────────────────────────────────────

def sec_heading(y, text):
    draw.text((LEFT, y), text.upper(), font=F["sec_head"], fill=(*CHARCOAL, 255))
    return y + _line_h(F["sec_head"]) + fig(8)


def sub_item(y, text):
    return draw_wrapped(y, text, F["sub_head"], CHARCOAL, line_gap=fig(4))


def body_text(y, text):
    return draw_wrapped(y, text, F["body"], TEXT_DARK, line_gap=fig(4))


def bullet(y, text):
    cy = y + _line_h(F["body"]) // 2
    r  = fig(3)
    draw.ellipse([LEFT, cy - r, LEFT + r * 2, cy + r], fill=(*CHARCOAL, 255))
    return draw_wrapped(y, text, F["body"], TEXT_DARK, x=LEFT + fig(12),
                        max_w=CONTENT_W - fig(12), line_gap=fig(4))


def directions_block(y, prefix, rest):
    """Medium prefix + Regular continuation, properly word-wrapped."""
    pfx_bb = draw.textbbox((LEFT, y), prefix, font=F["medium"])
    draw.text((LEFT, y), prefix, font=F["medium"], fill=(*CHARCOAL, 255))
    rest_x = pfx_bb[2] + fig(4)
    rest_w = RIGHT_EDGE - rest_x
    lh     = _line_h(F["direction"])

    # Word-wrap rest: first line starts at rest_x, continuation lines at LEFT
    words        = rest.split()
    first_line   = ""
    remaining    = []
    for idx, w in enumerate(words):
        candidate = (first_line + " " + w).strip()
        if draw.textlength(candidate, font=F["direction"]) <= rest_w:
            first_line = candidate
        else:
            remaining = words[idx:]
            break

    draw.text((rest_x, y), first_line, font=F["direction"], fill=(*TEXT_DARK, 255))
    y += lh + fig(4)

    if remaining:
        y = draw_wrapped(y, " ".join(remaining), F["direction"], TEXT_DARK,
                         x=LEFT, max_w=RIGHT_EDGE - LEFT, line_gap=fig(4))

    return y + fig(8)

def _draw_wrapped_caps_q(y, text, x, max_w, line_gap=None):
    """draw_wrapped for question text: ALL_CAPS words and **marked** words use medium weight."""
    import re as _re
    if line_gap is None:
        line_gap = fig(4)
    lh = _line_h(F["q_text"])

    # Tokenise: split on **...** markers; \n becomes a forced line-break sentinel
    _NEWLINE = ("\n", "__newline__")
    tokens = []
    for part in _re.split(r'(\*\*[^*]+\*\*)', text):
        if part.startswith('**') and part.endswith('**'):
            tokens.append((part[2:-2], "medium"))
        elif part:
            segments = part.split('\n')
            for si, segment in enumerate(segments):
                words = segment.split()
                for w in words:
                    fk = "medium" if _re.match(r'^[A-Z]{2,}[?!.,;:\'\"]*$', w) else "q_text"
                    tokens.append((w, fk))
                # only insert newline sentinel between segments (not after last)
                if si < len(segments) - 1 and (words or tokens):
                    tokens.append(_NEWLINE)
    # strip trailing newline sentinel
    while tokens and tokens[-1] == _NEWLINE:
        tokens.pop()
    # collapse consecutive newline sentinels into one
    deduped = []
    for tok in tokens:
        if tok == _NEWLINE and deduped and deduped[-1] == _NEWLINE:
            continue
        deduped.append(tok)
    tokens = deduped

    def _tok_w(tok, last):
        s = tok[0] if last else tok[0] + " "
        return int(draw.textlength(s, font=F[tok[1]]))

    def _flush(ts, fy):
        dx = x
        for li, t in enumerate(ts):
            s = t[0] if li == len(ts) - 1 else t[0] + " "
            draw.text((dx, fy), s, font=F[t[1]], fill=(*TEXT_DARK, 255))
            dx += int(draw.textlength(s, font=F[t[1]]))
        return fy + lh + line_gap

    line, cx = [], x
    for ti, tok in enumerate(tokens):
        if tok == _NEWLINE:
            # forced line break — flush current line and start fresh
            if line:
                y = _flush(line, y)
                line, cx = [], x
            else:
                y += lh + line_gap
            continue
        w = _tok_w(tok, ti == len(tokens) - 1)
        if cx + w > x + max_w and line:
            y = _flush(line, y)
            line, cx = [], x
        line.append(tok)
        cx += w
    if line:
        _flush(line, y)
        y += lh
    return y


# ─── Question badge + text ────────────────────────────────────────────────────

def draw_q(y, num, text):
    """Chapter-color light badge + question text. Returns new y."""
    badge_h  = _line_h(F["q_text"]) + fig(6)
    text_end = _draw_wrapped_caps_q(y, text, x=Q_TEXT_X, max_w=Q_CONTENT_W, line_gap=fig(4))
    bg  = chapter_badge_bg(CH_NUM)
    bor = chapter_color(CH_NUM)
    draw.rounded_rectangle(
        [LEFT, y, LEFT + Q_BADGE_W, y + badge_h],
        radius=px(4), fill=(*bg, 255), outline=(*bor, 255), width=max(1, px(0.5)))
    draw.text((LEFT + Q_BADGE_W // 2, y + badge_h // 2),
              f"{num:02d}.", font=F["q_badge"], fill=(*CHARCOAL, 255), anchor="mm")
    return max(text_end, y + badge_h + fig(4))

# ─── Options ──────────────────────────────────────────────────────────────────

def _opt_lbl_w():
    return draw.textbbox((0, 0), "A)", font=F["opt_label"])[2]


_OPT_BOX = fig(20)   # checkbox square size
_OPT_NEUTRAL = (151, 147, 140)  # neutral-500 #97938C

def _draw_single_opt(x, y, label, text):
    """Rounded checkbox box with label inside + option text after."""
    lbl = label.rstrip(")")   # "A)" → "A"
    cy  = y + _OPT_BOX // 2
    draw.rounded_rectangle([x, y, x + _OPT_BOX, y + _OPT_BOX],
                            radius=fig(2),
                            fill=(*WHITE, 255),
                            outline=(*_OPT_NEUTRAL, 255),
                            width=max(1, px(0.5)))
    draw.text((x + _OPT_BOX // 2, cy), lbl,
              font=F["opt_label"], fill=(*_OPT_NEUTRAL, 255), anchor="mm")
    draw.text((x + _OPT_BOX + fig(6), cy), text,
              font=F["opt_text"], fill=(*TEXT_DARK, 255), anchor="lm")


def _fits_row(opts):
    col_w = Q_CONTENT_W // 4
    return all(draw.textlength(o, font=F["opt_text"]) <= col_w - _OPT_BOX - fig(6) - fig(8) for o in opts)


def options_auto(y, opts):
    if _fits_row(opts):
        return _options_row(y, opts)
    return options_2col(y, opts)


def options_2col(y, opts):
    col_w  = Q_CONTENT_W // 2
    row_h  = _OPT_BOX + fig(4)
    labels = ["A)", "B)", "C)", "D)"]
    for i, (lbl, opt) in enumerate(zip(labels, opts)):
        _draw_single_opt(Q_TEXT_X + (i % 2) * col_w, y + (i // 2) * row_h, lbl, opt)
    return y + 2 * row_h


def options_vertical(y, opts):
    row_h  = _OPT_BOX + fig(8)
    labels = ["A)", "B)", "C)", "D)"]
    for lbl, opt in zip(labels, opts):
        _draw_single_opt(Q_TEXT_X, y, lbl, opt)
        y += row_h
    return y


def _options_row(y, opts):
    col_w  = Q_CONTENT_W // 4
    row_h  = _OPT_BOX + fig(10)
    labels = ["A)", "B)", "C)", "D)"]
    for i, (lbl, opt) in enumerate(zip(labels, opts)):
        _draw_single_opt(Q_TEXT_X + i * col_w, y, lbl, opt)
    return y + row_h

# ─── Separator ────────────────────────────────────────────────────────────────

def separator(y, gap_before=None, gap_after=None):
    if gap_before is None: gap_before = fig(12)
    if gap_after  is None: gap_after  = fig(12)
    sy = y + gap_before
    draw.line([(LEFT, sy), (RIGHT_EDGE, sy)], fill=(*CHARCOAL, 80), width=max(1, px(0.75)))
    return sy + gap_after
