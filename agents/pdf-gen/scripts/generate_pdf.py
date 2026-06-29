"""
generate_pdf.py — Generate Cuemath Updated Layout PDF from extracted content.

Usage:
  python3 generate_pdf.py \
    --content personal/workspace/pdf-gen/extracted_content.json \
    --images  personal/workspace/pdf-gen/images/ \
    --output  personal/workspace/pdf-gen/output.pdf
"""

import argparse
import json
import math
import os
import glob
import re
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

# ── Font registration ──────────────────────────────────────────────────────────
_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
_FONT_DIR = os.path.normpath(_FONT_DIR)

_FONTS = {
    "Body":        ("UntitledSans-Regular",  "UntitledSans-Regular.otf"),
    "BodyBold":    ("UntitledSans-Bold",      "UntitledSans-Bold.otf"),
    "BodyMedium":  ("UntitledSans-Medium",    "UntitledSans-Medium.otf"),
    "Display":     ("UntitledSans-Black",     "UntitledSans-Black.otf"),
}

def _register_fonts():
    for alias, (name, filename) in _FONTS.items():
        path = os.path.join(_FONT_DIR, filename)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass  # fall back to Helvetica if registration fails

_register_fonts()

def _font(alias):
    """Return registered font name, or Helvetica fallback."""
    name = _FONTS.get(alias, ("Helvetica",))[0]
    try:
        pdfmetrics.getFont(name)
        return name
    except Exception:
        fallbacks = {"Body": "Helvetica", "BodyBold": "Helvetica-Bold",
                     "BodyMedium": "Helvetica", "Display": "Helvetica-Bold"}
        return fallbacks.get(alias, "Helvetica")

# Font name shortcuts
F_BODY    = lambda: _font("Body")
F_BOLD    = lambda: _font("BodyBold")
F_MEDIUM  = lambda: _font("BodyMedium")
F_DISPLAY = lambda: _font("Display")

# Logo SVG
_LOGO_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..",
    "context", "design-resources", "logos", "cuemath-wordmark-tagline.svg"
))

# ── Design tokens ─────────────────────────────────────────────────────────────
W, H = A4  # 595.28 x 841.89 pts

MARGIN_L = 40
MARGIN_R = 40
MARGIN_TOP = 72
MARGIN_BOTTOM = 48
CONTENT_W = W - MARGIN_L - MARGIN_R

# Colors
C_BG            = colors.HexColor("#FAF1E6")   # gold-100
C_HEADER        = colors.HexColor("#F97279")   # error-500
C_ACCENT        = colors.HexColor("#E5555E")   # error-600
C_BADGE_Q       = colors.HexColor("#FFD6D5")   # error-200 (light badge bg)
C_BADGE_OPT_BG  = colors.white
C_BADGE_OPT_BOR = colors.HexColor("#FFB8B7")   # error-300
C_DIVIDER       = colors.HexColor("#FFD6D5")   # error-200
C_TILE_BG       = colors.white
C_TILE_BOR      = colors.HexColor("#FFB8B7")   # error-300
C_TEXT          = colors.HexColor("#1D1C1B")   # neutral-1100
C_SECONDARY     = colors.HexColor("#5B5854")   # neutral-700
C_FOOTER        = colors.HexColor("#84807B")   # neutral-600
C_WHITE         = colors.white

# Font sizes
FS_CHAPTER_TITLE  = 24
FS_CHAPTER_SUB    = 11
FS_GRADE_BADGE    = 18
FS_SECTION_HEAD   = 10
FS_BODY           = 9.5
FS_OPTION         = 9.5
FS_DIRECTIONS     = 9.5
FS_TILE           = 10
FS_FOOTER         = 7.5
FS_LOGO           = 9
FS_LOGO_TAG       = 6.5
FS_Q_BADGE        = 8

# Spacing
Q_BADGE_SIZE  = 18
OPT_BADGE_W   = 14
OPT_BADGE_H   = 14
TILE_SIZE     = 20
TILE_GAP      = 4
Q_SPACING     = 12
LINE_SPACING  = 13
OPT_SPACING   = 11


# ── Helpers ───────────────────────────────────────────────────────────────────

def draw_rounded_rect(c, x, y, w, h, r, fill_color=None, stroke_color=None, stroke_width=0.5):
    p = c.beginPath()
    p.moveTo(x + r, y)
    p.lineTo(x + w - r, y)
    p.arcTo(x + w - r, y, x + w, y + r, 270, 90)
    p.lineTo(x + w, y + h - r)
    p.arcTo(x + w - r, y + h - r, x + w, y + h, 0, 90)
    p.lineTo(x + r, y + h)
    p.arcTo(x, y + h - r, x + r, y + h, 90, 90)
    p.lineTo(x, y + r)
    p.arcTo(x, y, x + r, y + r, 180, 90)
    p.close()

    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)

    if fill_color and stroke_color:
        c.drawPath(p, fill=1, stroke=1)
    elif fill_color:
        c.drawPath(p, fill=1, stroke=0)
    elif stroke_color:
        c.drawPath(p, fill=0, stroke=1)


def draw_circle(c, cx, cy, r, fill_color=None, stroke_color=None, stroke_width=1):
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    c.circle(cx, cy, r, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)


def wrap_text(c, text, font, font_size, max_width):
    """Wrap text to lines fitting max_width. Returns list of lines."""
    c.setFont(font, font_size)
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if c.stringWidth(test, font, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def text_height(c, text, font, font_size, max_width, line_spacing=None):
    """Calculate height needed to render wrapped text."""
    if line_spacing is None:
        line_spacing = font_size + 2
    lines = wrap_text(c, text, font, font_size, max_width)
    return len(lines) * line_spacing


def draw_wrapped_text(c, text, x, y, font, font_size, max_width,
                      color=None, line_spacing=None, align="left"):
    """Draw wrapped text, return final y position (after last line)."""
    if line_spacing is None:
        line_spacing = font_size + 2.5
    if color:
        c.setFillColor(color)
    c.setFont(font, font_size)
    lines = wrap_text(c, text, font, font_size, max_width)
    for line in lines:
        if align == "center":
            lw = c.stringWidth(line, font, font_size)
            c.drawString(x + (max_width - lw) / 2, y, line)
        else:
            c.drawString(x, y, line)
        y -= line_spacing
    return y


# ── Page structure ─────────────────────────────────────────────────────────────

class PageState:
    def __init__(self, c, chapter_name, section_label, page_num):
        self.c = c
        self.chapter_name = chapter_name
        self.section_label = section_label
        self.page_num = page_num
        self.y = H - MARGIN_TOP  # current drawing y position

    def remaining(self):
        return self.y - MARGIN_BOTTOM

    def needs_break(self, required_height):
        return self.y - required_height < MARGIN_BOTTOM


def draw_page_background(c):
    c.setFillColor(C_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)


def draw_content_header(c, chapter_name, page_num):
    """Header for MCQ/assessment pages (not intro)."""
    # Accent stripe
    c.setFillColor(C_ACCENT)
    c.rect(0, H - 6, W, 6, fill=1, stroke=0)

    # Header bar
    header_h = 26
    c.setFillColor(C_WHITE)
    c.rect(0, H - 6 - header_h, W, header_h, fill=1, stroke=0)

    # Divider line
    c.setStrokeColor(C_DIVIDER)
    c.setLineWidth(0.5)
    c.line(MARGIN_L, H - 6 - header_h, W - MARGIN_R, H - 6 - header_h)

    # Chapter name left
    c.setFillColor(C_SECONDARY)
    c.setFont(F_BODY(), 8)
    c.drawString(MARGIN_L, H - 6 - header_h + 8, chapter_name)

    # Cuemath logo SVG right
    logo_h = header_h - 8
    logo_x = W - MARGIN_R
    logo_y = H - 6 - header_h + 4
    if os.path.exists(_LOGO_PATH):
        try:
            drawing = svg2rlg(_LOGO_PATH)
            if drawing:
                scale = logo_h / drawing.height
                logo_w = drawing.width * scale
                drawing.width = logo_w
                drawing.height = logo_h
                drawing.transform = (scale, 0, 0, scale, 0, 0)
                renderPDF.draw(drawing, c, logo_x - logo_w, logo_y)
            else:
                raise ValueError("svg2rlg returned None")
        except Exception:
            c.setFillColor(C_TEXT)
            c.setFont(F_BOLD(), FS_LOGO)
            c.drawString(logo_x - 60, logo_y + 8, "CUEMATH")
    else:
        c.setFillColor(C_TEXT)
        c.setFont(F_BOLD(), FS_LOGO)
        c.drawString(logo_x - 60, logo_y + 8, "CUEMATH")


def draw_footer(c, page_num, section_label):
    y_footer = MARGIN_BOTTOM - 24
    c.setFillColor(C_FOOTER)
    c.setFont(F_BODY(), FS_FOOTER)
    c.drawString(MARGIN_L, y_footer, "© Cue Learn Pvt. Ltd.")
    page_str = str(page_num)
    pw = c.stringWidth(page_str, F_BODY(), FS_FOOTER)
    c.drawString(W / 2 - pw / 2, y_footer, page_str)
    sw = c.stringWidth(section_label, F_BODY(), FS_FOOTER)
    c.drawString(W - MARGIN_R - sw, y_footer, section_label)


def draw_chapter_intro_header(c, chapter_num, chapter_title):
    """Large banner header for chapter intro page — matches Figma gold design."""
    banner_h = 92
    banner_y = H - banner_h

    # Gold background bar (full width)
    c.setFillColor(colors.HexColor("#F4AB52"))  # gold-500
    c.rect(0, banner_y, W, banner_h, fill=1, stroke=0)

    # Chapter number — 14pt Regular, dark text
    c.setFillColor(colors.HexColor("#313131"))
    c.setFont(F_BODY(), 14)
    c.drawString(MARGIN_L, H - 38, f"Chapter {chapter_num}")

    # Chapter name — 24pt, dark text
    c.setFont(F_BODY(), 24)
    c.drawString(MARGIN_L, H - 70, chapter_title)

    # Grade badge — pill shape, gold-300 bg, right side
    pill_w, pill_h = 56, 64
    pill_x = W - 24 - pill_w
    pill_y = banner_y + (banner_h - pill_h) / 2
    draw_rounded_rect(c, pill_x, pill_y, pill_w, pill_h, pill_w / 2,
                      fill_color=colors.HexColor("#FAD6AC"))  # gold-300

    # "Grade" label — 12pt Regular
    c.setFillColor(colors.HexColor("#313131"))
    c.setFont(F_BODY(), 12)
    grade_label = "Grade"
    gw = c.stringWidth(grade_label, F_BODY(), 12)
    c.drawString(pill_x + (pill_w - gw) / 2, pill_y + pill_h - 22, grade_label)

    # Grade number — 32pt Black
    c.setFont(F_DISPLAY(), 32)
    grade_num = "3"
    nw = c.stringWidth(grade_num, F_DISPLAY(), 32)
    c.drawString(pill_x + (pill_w - nw) / 2, pill_y + 8, grade_num)

    return banner_y - 20  # return starting y for content


def start_new_page(c, state):
    c.showPage()
    state.page_num += 1
    draw_page_background(c)
    draw_content_header(c, state.chapter_name, state.section_label)
    draw_footer(c, state.page_num, state.section_label)
    state.y = H - MARGIN_TOP


# ── Section renderers ─────────────────────────────────────────────────────────

def render_section_heading(c, state, text):
    needed = 20
    if state.needs_break(needed):
        start_new_page(c, state)
    c.setFillColor(C_TEXT)
    c.setFont(F_BOLD(), FS_SECTION_HEAD)
    c.drawString(MARGIN_L, state.y, text.upper())
    state.y -= 16


def render_directions(c, state, text):
    """Render a Directions (1–5): ... line."""
    if not text.strip():
        return
    # Normalize em-dash and hyphens in range like (1-5) or (1–5)
    text = re.sub(r"\((\d+)\s*[–-]\s*(\d+)\)", r"(\1-\2)", text)
    needed = text_height(c, text, F_BODY(), FS_DIRECTIONS, CONTENT_W) + 10
    if state.needs_break(needed):
        start_new_page(c, state)
    state.y -= 6
    # Bold the "Directions (n-m):" prefix
    prefix_match = re.match(r"(Directions?\s*\(\d+-\d+\)\s*:)\s*(.*)", text, re.DOTALL)
    if prefix_match:
        prefix = prefix_match.group(1)
        rest = prefix_match.group(2).strip()
        c.setFont(F_BODY(), FS_DIRECTIONS)
        c.setFillColor(C_TEXT)
        pw = c.stringWidth(prefix + " ", F_BODY(), FS_DIRECTIONS)
        c.drawString(MARGIN_L, state.y, prefix + " ")
        c.setFillColor(C_SECONDARY)
        full = prefix + " " + rest
        lines = wrap_text(c, full, F_BODY(), FS_DIRECTIONS, CONTENT_W)
        # Only draw the rest (skip first line which has bold prefix)
        if lines:
            first_line_rest = lines[0][len(prefix):].strip()
            c.drawString(MARGIN_L + pw, state.y, first_line_rest)
            state.y -= 13
        for line in lines[1:]:
            c.drawString(MARGIN_L, state.y, line)
            state.y -= 13
    else:
        state.y = draw_wrapped_text(
            c, text, MARGIN_L, state.y, F_BODY(), FS_DIRECTIONS,
            CONTENT_W, color=C_SECONDARY, line_spacing=13
        )
    state.y -= 8


def render_question(c, state, q, image_dir=None):
    """Render a single MCQ question block."""
    num = q.get("num", "?")
    q_text = q.get("text", "").strip()
    options = q.get("options", {})
    q_type = q.get("type", "text_only")
    tiles = q.get("tiles", [])
    direction = q.get("direction", "")

    # Estimate question height
    q_text_h = text_height(c, q_text, F_BODY(), FS_BODY, CONTENT_W - Q_BADGE_SIZE - 10)
    tile_h = (TILE_SIZE * 2 + 20) if tiles else 0
    image_h = 80 if q_type == "image_based" else 0
    options_h = (OPT_SPACING * 2) if len(options) <= 2 else (OPT_SPACING * 2 + 4)
    total_h = Q_BADGE_SIZE + q_text_h + tile_h + image_h + options_h + Q_SPACING + 12

    if state.needs_break(total_h):
        start_new_page(c, state)

    x = MARGIN_L
    y = state.y

    # Question number badge
    draw_rounded_rect(c, x, y - Q_BADGE_SIZE + 2, Q_BADGE_SIZE, Q_BADGE_SIZE, 3,
                      fill_color=C_BADGE_Q)
    c.setFillColor(C_TEXT)
    c.setFont(F_BOLD(), FS_Q_BADGE)
    bw = c.stringWidth(num, F_BOLD(), FS_Q_BADGE)
    c.drawString(x + (Q_BADGE_SIZE - bw) / 2, y - Q_BADGE_SIZE + 6, num)

    # Question text
    text_x = x + Q_BADGE_SIZE + 8
    text_w = CONTENT_W - Q_BADGE_SIZE - 8
    text_y = y

    # Bold part (if question text has Directions-style bold prefix)
    bold_match = None
    remaining_text = q_text

    if remaining_text:
        text_y = draw_wrapped_text(
            c, remaining_text, text_x, text_y, F_BODY(), FS_BODY,
            text_w, color=C_TEXT, line_spacing=LINE_SPACING
        )

    text_y -= 6

    # Letter tiles
    if tiles:
        tile_x = text_x
        tile_y = text_y
        for letter in tiles:
            draw_rounded_rect(c, tile_x, tile_y - TILE_SIZE, TILE_SIZE, TILE_SIZE, 2,
                              fill_color=C_TILE_BG, stroke_color=C_TILE_BOR, stroke_width=0.5)
            c.setFillColor(C_TEXT)
            c.setFont(F_BOLD(), FS_TILE)
            lw = c.stringWidth(letter, F_BOLD(), FS_TILE)
            c.drawString(tile_x + (TILE_SIZE - lw) / 2, tile_y - TILE_SIZE + 5, letter)
            tile_x += TILE_SIZE + TILE_GAP
        # Number row below letter tiles
        num_tile_y = tile_y - TILE_SIZE - 2
        tile_x = text_x
        for i in range(1, len(tiles) + 1):
            draw_rounded_rect(c, tile_x, num_tile_y - TILE_SIZE, TILE_SIZE, TILE_SIZE, 2,
                              fill_color=C_BG, stroke_color=C_TILE_BOR, stroke_width=0.5)
            c.setFillColor(C_BADGE_Q)
            c.setFont(F_BODY(), FS_TILE)
            nw = c.stringWidth(str(i), F_BODY(), FS_TILE)
            c.drawString(tile_x + (TILE_SIZE - nw) / 2, num_tile_y - TILE_SIZE + 5, str(i))
            tile_x += TILE_SIZE + TILE_GAP
        text_y = num_tile_y - TILE_SIZE - 6

    # Image placeholder
    if q_type == "image_based":
        img_y = text_y - 6
        img_h = 70
        # Try to find image file for this question
        img_file = find_image(image_dir, q.get("source_page"), num)
        if img_file:
            try:
                ir = ImageReader(img_file)
                iw, ih = ir.getSize()
                scale = min((CONTENT_W - 40) / iw, img_h / ih, 1)
                c.drawImage(img_file, text_x, img_y - ih * scale,
                            width=iw * scale, height=ih * scale)
                text_y = img_y - ih * scale - 6
            except Exception:
                text_y = draw_image_placeholder(c, text_x, img_y, CONTENT_W - 40, img_h,
                                                q.get("source_page"), num)
        else:
            text_y = draw_image_placeholder(c, text_x, img_y, CONTENT_W - 40, img_h,
                                            q.get("source_page"), num)

    # Options
    options_y = text_y - 4
    render_options(c, options, x, options_y, CONTENT_W)
    opt_h = (OPT_SPACING * 2) if len(options) <= 2 else (OPT_SPACING * 2 + 4)
    final_y = options_y - opt_h - 8

    # Divider
    c.setStrokeColor(C_DIVIDER)
    c.setLineWidth(0.5)
    c.line(MARGIN_L, final_y, W - MARGIN_R, final_y)

    state.y = final_y - Q_SPACING


def render_options(c, options, x, y, content_w):
    """Render A/B/C/D options in 2-column grid."""
    col_w = content_w / 2 - 4
    option_order = [("A", "B"), ("C", "D")]

    row_y = y
    for row in option_order:
        row_has_content = any(r in options for r in row)
        if not row_has_content:
            continue
        for i, letter in enumerate(row):
            if letter not in options:
                continue
            ox = x + i * (col_w + 8)
            # Option letter badge
            draw_rounded_rect(c, ox, row_y - OPT_BADGE_H + 2, OPT_BADGE_W, OPT_BADGE_H, 2,
                              fill_color=C_BADGE_OPT_BG, stroke_color=C_BADGE_OPT_BOR,
                              stroke_width=0.5)
            c.setFillColor(C_TEXT)
            c.setFont(F_BODY(), FS_OPTION)
            lw = c.stringWidth(letter, F_BODY(), FS_OPTION)
            c.drawString(ox + (OPT_BADGE_W - lw) / 2, row_y - OPT_BADGE_H + 5, letter)
            # Option text
            c.setFillColor(C_TEXT)
            c.setFont(F_BODY(), FS_OPTION)
            c.drawString(ox + OPT_BADGE_W + 4, row_y - OPT_BADGE_H + 5, options[letter][:40])
        row_y -= OPT_SPACING


def draw_image_placeholder(c, x, y, w, h, source_page, q_num):
    c.setFillColor(colors.HexColor("#F5F5F5"))
    c.setStrokeColor(colors.HexColor("#DDDDDD"))
    c.setLineWidth(0.5)
    c.rect(x, y - h, w, h, fill=1, stroke=1)
    c.setFillColor(C_SECONDARY)
    c.setFont(F_BODY(), 8)
    msg = f"[Figure — see source book, Q{q_num}]"
    mw = c.stringWidth(msg, F_BODY(), 8)
    c.drawString(x + (w - mw) / 2, y - h / 2 - 4, msg)
    return y - h - 6


def find_image(image_dir, source_page, q_num):
    """Try to find an extracted image for a given page/question."""
    if not image_dir or not source_page:
        return None
    patterns = [
        os.path.join(image_dir, f"page-{source_page:03d}-*.jpg"),
        os.path.join(image_dir, f"page-{source_page}-*.jpg"),
        os.path.join(image_dir, f"*-{q_num}.jpg"),
    ]
    for p in patterns:
        matches = glob.glob(p)
        if matches:
            return matches[0]
    return None


def render_intro_table(c, state, letters, numbers):
    """Render Letter/Number example table matching Figma design."""
    cell_w   = 32
    header_w = 64
    cell_h   = 28
    table_x  = MARGIN_L + 14

    for row_idx, (header, values) in enumerate([("Letter", letters), ("Number", numbers)]):
        row_y = state.y - row_idx * cell_h
        # Header cell — gold-200 bg, gold-700 border
        c.setFillColor(colors.HexColor("#FAE6D0"))
        c.setStrokeColor(colors.HexColor("#CE7E12"))
        c.setLineWidth(0.5)
        c.rect(table_x, row_y - cell_h, header_w, cell_h, fill=1, stroke=1)
        c.setFillColor(C_TEXT)
        c.setFont(F_BODY(), 12)
        hw = c.stringWidth(header, F_BODY(), 12)
        c.drawString(table_x + (header_w - hw) / 2, row_y - cell_h + 9, header)
        # Value cells — white bg, gold-700 border
        val_x = table_x + header_w
        for val in values:
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor("#CE7E12"))
            c.setLineWidth(0.5)
            c.rect(val_x, row_y - cell_h, cell_w, cell_h, fill=1, stroke=1)
            c.setFillColor(C_TEXT)
            c.setFont(F_BODY(), 12)
            vw = c.stringWidth(val, F_BODY(), 12)
            c.drawString(val_x + (cell_w - vw) / 2, row_y - cell_h + 9, val)
            val_x += cell_w

    state.y -= cell_h * 2 + 8


def render_intro_section(c, state, section_text, chapter_num, chapter_name):
    """Render the Introduction section matching Figma layout."""
    start_y = draw_chapter_intro_header(c, chapter_num, chapter_name)
    state.y = start_y

    LINE_H = 19   # 12px × 1.6
    INDENT = 14

    lines = [l.rstrip() for l in section_text.split("\n")]
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        if not stripped:
            state.y -= 6
            i += 1
            continue

        # Normalise heading aliases
        if stripped.lower() == "introduction":
            stripped = "INTRODUCTION"
        if re.match(r"^types of", stripped, re.I):
            stripped = "TYPES OF ALPHABET TEST"

        # UPPERCASE section headings (INTRODUCTION, TYPES OF …)
        if stripped.isupper() and len(stripped) > 3:
            state.y -= 4
            c.setFillColor(C_TEXT)
            c.setFont(F_MEDIUM(), 14)
            c.drawString(MARGIN_L, state.y, stripped)
            state.y -= LINE_H + 4
            i += 1
            continue

        # Bullet points (y prefix from PDF extraction)
        if stripped.startswith("y "):
            bullet_text = stripped[2:].strip()
            c.setFillColor(C_TEXT)
            c.setFont(F_BODY(), 12)
            c.drawString(MARGIN_L + 4, state.y, "•")
            draw_wrapped_text(c, bullet_text, MARGIN_L + 14, state.y,
                              F_BODY(), 12, CONTENT_W - 14, color=C_TEXT, line_spacing=LINE_H)
            state.y -= LINE_H
            i += 1
            continue

        # Type I:, Type II: … — label bold + description medium
        type_match = re.match(r"^(Type [IVX]+:)\s*(.*)", stripped)
        if type_match:
            label = type_match.group(1)
            desc  = type_match.group(2)
            c.setFillColor(C_TEXT)
            c.setFont(F_MEDIUM(), 12)
            lw = c.stringWidth(label + "  ", F_MEDIUM(), 12)
            c.drawString(MARGIN_L, state.y, label)
            c.drawString(MARGIN_L + lw, state.y, desc)
            state.y -= LINE_H + 2
            i += 1
            continue

        # Example N: — label medium + rest regular (may wrap across lines)
        ex_match = re.match(r"^(Example \d+:)\s*(.*)", stripped)
        if ex_match:
            ex_label = ex_match.group(1)
            ex_rest  = ex_match.group(2)
            i += 1
            # accumulate continuation lines
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt or re.match(r"^(Example|Letter|Number|\(A\)|Answer:|Type [IVX]|Jumbled|Correct)", nxt):
                    break
                ex_rest += " " + nxt
                i += 1
            ex_rest = re.sub(r"corre-\s*sponding", "corresponding", ex_rest)
            c.setFillColor(C_TEXT)
            c.setFont(F_MEDIUM(), 12)
            lw = c.stringWidth(ex_label + "  ", F_MEDIUM(), 12)
            c.drawString(MARGIN_L + INDENT, state.y, ex_label)
            c.setFont(F_BODY(), 12)
            wrap_w = CONTENT_W - INDENT - lw
            lines_out = wrap_text(c, ex_rest, F_BODY(), 12, wrap_w)
            for li, ln in enumerate(lines_out):
                x = MARGIN_L + INDENT + lw if li == 0 else MARGIN_L + INDENT
                c.drawString(x, state.y, ln)
                if li < len(lines_out) - 1:
                    state.y -= LINE_H
            state.y -= LINE_H + 2
            continue

        # Letter/Number table
        if stripped.startswith("Letter "):
            letters = stripped.replace("Letter", "").split()
            if i + 1 < len(lines) and lines[i+1].strip().startswith("Number"):
                numbers = lines[i+1].strip().replace("Number", "").split()
                i += 2
                render_intro_table(c, state, letters, numbers)
                continue

        # Jumbled letters / Correct word
        if re.match(r"^(Jumbled|Correct word)", stripped):
            c.setFillColor(C_TEXT)
            c.setFont(F_BODY(), 12)
            c.drawString(MARGIN_L + INDENT, state.y, stripped)
            state.y -= LINE_H
            i += 1
            continue

        # Options (A)(B)(C)(D)
        if stripped.startswith("(A)"):
            opts = re.findall(r"\([A-D]\)[^(]+", stripped)
            c.setFont(F_BODY(), 12)
            c.setFillColor(C_TEXT)
            opt_x = MARGIN_L + INDENT
            col_w = CONTENT_W / 4
            for opt in opts:
                c.drawString(opt_x, state.y, opt.strip())
                opt_x += col_w
            state.y -= LINE_H
            i += 1
            continue

        # Answer:
        if stripped.startswith("Answer:"):
            c.setFillColor(C_TEXT)
            c.setFont(F_MEDIUM(), 12)
            ans_lw = c.stringWidth("Answer:  ", F_MEDIUM(), 12)
            c.drawString(MARGIN_L + INDENT, state.y, "Answer:")
            c.setFont(F_BODY(), 12)
            c.drawString(MARGIN_L + INDENT + ans_lw, state.y, stripped[7:].strip())
            state.y -= LINE_H + 6
            i += 1
            continue

        # Default body text
        c.setFillColor(C_TEXT)
        c.setFont(F_BODY(), 12)
        state.y = draw_wrapped_text(c, stripped, MARGIN_L, state.y,
                                     F_BODY(), 12, CONTENT_W, color=C_TEXT, line_spacing=LINE_H)
        state.y -= 4
        i += 1


# ── Main orchestrator ─────────────────────────────────────────────────────────

def generate_pdf(content_path, image_dir, output_path):
    with open(content_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle(data.get("book_title", "Cuemath IMO Book"))

    page_counter = [1]  # mutable so nested functions can update

    for chapter in data["chapters"]:
        ch_key = chapter["chapter_key"]
        ch_name = chapter["chapter_name"]
        ch_num = ch_key if ch_key.startswith("ca") else ch_key

        # Determine section label
        if ch_key.startswith("ca"):
            section_label = f"Grade 3: Cumulative Assessment"
        else:
            section_label = f"Grade 3: Logical Reasoning"

        # Start chapter
        draw_page_background(c)

        state = PageState(c, f"Chapter {ch_num}: {ch_name}", section_label, page_counter[0])
        draw_footer(c, page_counter[0], section_label)

        for section in chapter["sections"]:
            sec_type = section["type"]

            if sec_type == "intro":
                render_intro_section(c, state, section.get("text", ""), ch_num, ch_name)

            elif sec_type in ("mcq", "assessment", "cumulative"):
                # Section title
                if sec_type == "assessment":
                    sec_title = "Chapter Assessment"
                elif sec_type == "cumulative":
                    sec_title = chapter["chapter_name"]
                else:
                    sec_title = "Multiple Choice Questions"

                # Start new page for each major section
                c.showPage()
                page_counter[0] += 1
                draw_page_background(c)
                draw_content_header(c, f"Chapter {ch_num}: {ch_name}", section_label)
                draw_footer(c, page_counter[0], section_label)
                state = PageState(c, f"Chapter {ch_num}: {ch_name}", section_label, page_counter[0])

                # Render MCQ header
                state.y -= 10
                c.setFillColor(C_TEXT)
                c.setFont(F_BOLD(), 16)
                c.drawString(MARGIN_L, state.y, sec_title)
                state.y -= 20

                # Track current direction
                last_direction = ""
                for q in section.get("questions", []):
                    direction = q.get("direction", "")
                    if direction and direction != last_direction:
                        render_directions(c, state, direction)
                        last_direction = direction
                    render_question(c, state, q, image_dir)

        # End of chapter — finalize page
        c.showPage()
        page_counter[0] += 1

    # Remove the trailing blank page
    c.save()
    print(f"PDF saved: {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Generate Cuemath Updated Layout PDF")
    parser.add_argument("--content", required=True, help="Path to extracted_content.json")
    parser.add_argument("--images", default=None, help="Directory with extracted images")
    parser.add_argument("--output", required=True, help="Output PDF path")
    args = parser.parse_args()

    if not os.path.exists(args.content):
        print(f"Error: content file not found: {args.content}", file=sys.stderr)
        sys.exit(1)

    generate_pdf(args.content, args.images, args.output)


if __name__ == "__main__":
    main()
