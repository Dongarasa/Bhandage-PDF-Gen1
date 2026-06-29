"""
generate_g3_page.py — Generate a single page PDF from extracted chapter content.
PIL + 300 DPI via imo_g3_base.

Usage:
  python3 generate_g3_page.py \
    --content  <path/to/content.json> \
    --page     <page_index>            (1-based) \
    --output   <path/to/page-001.pdf>

Page index:
  1       = chapter intro  (Temp1)
  2       = first MCQ page (Temp2 opener)
  3       = page 2 of MCQ  (Temp3)
  4+      = further MCQ    (Temp4)
  last    = assessment/cumulative pages (same template rules)
"""

import argparse
import json
import math
import os
import re
import sys

# ── Import shared base ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
import imo_g3_base as _b
from imo_g3_base import (
    fig, px, mm,
    W, H, LEFT, RIGHT_EDGE, CONTENT_W, CONTENT_BOT,
    MARGIN, Q_TEXT_X, Q_CONTENT_W, Q_BADGE_W,
    CONTENT_TOP_T1, CONTENT_TOP_T34,
    INTRO_L0, INTRO_L1, INTRO_L2,
    CHARCOAL, TEXT_DARK, WARM_GREY, MED_GREY, WHITE, BG_PAGE,
    setup, finish,
    temp1_header, temp2_header, temp3_header, temp4_header,
    draw_q, draw_wrapped, separator, directions_block,
    options_auto, options_2col, options_vertical, _options_row,
)
# F must always be accessed via _b.F — importing it directly gives a stale empty dict

Q_FIRST_PAGE  = 4  # questions on first MCQ page
Q_SECOND_PAGE = 5  # questions on second MCQ page
Q_PER_PAGE    = 7  # questions on subsequent MCQ pages

# ─── Page plan ────────────────────────────────────────────────────────────────

def build_page_plan(chapter_data):
    """
    Returns a list of page descriptors.
    Template selection (Temp1/2/3/4) is resolved later in render_page()
    based on absolute page position within the full chapter page sequence.
    """
    pages = []
    ch_num  = chapter_data["chapter_key"]
    ch_name = chapter_data["chapter_name"]

    for sec in chapter_data["sections"]:
        sec_type = sec["type"]

        if sec_type == "intro":
            # Split intro text at "Type III" boundary → 2 output pages
            # Page 1 (Temp1): content up to & including Type II block
            # Page 2 (Temp3): Type III onwards
            full_text = sec.get("text", "")
            split_marker = re.search(r'\nType III:', full_text)
            if split_marker:
                text_p1 = full_text[:split_marker.start()].strip()
                text_p2 = full_text[split_marker.start():].strip()
            else:
                text_p1 = full_text
                text_p2 = ""

            pages.append({
                "type": "intro", "intro_page": 1,
                "chapter_num": ch_num, "chapter_name": ch_name,
                "text": text_p1, "questions": [],
            })
            if text_p2:
                pages.append({
                    "type": "intro", "intro_page": 2,
                    "chapter_num": ch_num, "chapter_name": ch_name,
                    "text": text_p2, "questions": [],
                })

        elif sec_type in ("mcq", "assessment", "cumulative"):
            questions = sec.get("questions", [])
            chunks, pos, page_idx = [], 0, 0
            while pos < max(len(questions), 1):
                if page_idx == 0:   size = Q_FIRST_PAGE
                elif page_idx == 1: size = Q_SECOND_PAGE
                else:               size = Q_PER_PAGE
                chunks.append((pos, questions[pos: pos + size]))
                pos += size
                page_idx += 1
            for section_idx, (chunk_start, chunk) in enumerate(chunks):
                pages.append({
                    "type":             sec_type,
                    "chapter_num":      ch_num,
                    "chapter_name":     ch_name,
                    "questions":        chunk,
                    "section_index":    section_idx,
                    "is_first_in_section": section_idx == 0,
                    "section_title": {
                        "mcq":        "Multiple Choice Questions",
                        "assessment": "Chapter Assessment",
                        "cumulative": ch_name,
                    }.get(sec_type, sec_type.title()),
                })

    return pages

# ─── Intro section renderer ───────────────────────────────────────────────────
# Matches Figma node 232:4 exactly.
#
# Indentation levels (Figma px → 300 DPI):
#   INTRO_L0 = fig(40)  — headings, "Type X:" row, top-level Answer:
#   INTRO_L1 = fig(87)  — type description text
#   INTRO_L2 = fig(154) — Example label, table, example options, indented Answer:
#
# Typography:
#   Section heading : UntitledSans Medium 14pt UPPERCASE   (F["sec_head"])
#   Type label+title: UntitledSans Medium 12pt             (F["medium"])
#   Body / description: UntitledSans Regular 12pt 1.6 lh  (F["body"])
#   Example label   : UntitledSans Medium 12pt             (F["medium"])
# ─────────────────────────────────────────────────────────────────────────────

PARA_GAP = fig(8)

_STRUCT_RE = re.compile(
    r'^(Introduction$|Types of |Type [IVX]+:|Example \d+:?|'
    r'Answer:|Solution:|Jumbled letters:|Correct word|y |\(A\)|Letter |Number )')


def _lh(font_key):
    return _b.draw.textbbox((0, 0), "Ag", font=_b.F[font_key])[3]


def _draw_text(x, y, text, font_key, color):
    _b.draw.text((x, y), text, font=_b.F[font_key], fill=(*color, 255))


def _draw_inline(y, x_label, label_key, text, body_key, color=None):
    """Label (Medium) + text (Regular) on same line at x_label. Returns new y."""
    if color is None:
        color = TEXT_DARK
    lw  = _b.draw.textbbox((0, 0), label, font=_b.F[label_key])[2] if False else \
          _b.draw.textlength(label, font=_b.F[label_key])
    # — actual call below —
    pass


def _inline_label_text(y, x, label, text, avail_w):
    """
    Draw  [label][gap][text]  starting at x.
    If text overflows avail_w, wrap remainder on next line at x + label_width + gap.
    Returns new y.
    """
    lw  = _b.draw.textlength(label, font=_b.F["medium"])
    gap = fig(6)
    tx  = x + lw + gap
    tw  = avail_w - lw - gap

    _b.draw.text((x, y), label, font=_b.F["medium"], fill=(*CHARCOAL, 255))

    lh = _lh("medium")
    y = _draw_wrapped_styled(y, text, TEXT_DARK, x=tx, max_w=tw, line_gap=fig(4))
    return y + fig(4)


def _draw_wrapped_styled(y, text, color, x, max_w, line_gap=None):
    """Like draw_wrapped but **word** tokens render in medium font, rest in body.
    Strips ** markers before drawing."""
    if color is None:
        color = TEXT_DARK
    if line_gap is None:
        line_gap = fig(5)
    lh = _lh("body")

    # Tokenise: each token is (display_text, font_key)
    tokens = []
    for part in re.split(r'(\*\*[^*]+\*\*)', text):
        if part.startswith('**') and part.endswith('**'):
            tokens.append((part[2:-2], "medium"))
        elif part:
            for w in part.split():
                tokens.append((w, "body"))

    def _tok_w(tok, is_last):
        raw = tok[0] if is_last else tok[0] + " "
        return int(_b.draw.textlength(raw, font=_b.F[tok[1]]))

    line, cx = [], x
    for ti, tok in enumerate(tokens):
        w = _tok_w(tok, ti == len(tokens) - 1)
        if cx + w > x + max_w and line:
            # flush line
            dx = x
            for li, lt in enumerate(line):
                s = lt[0] if li == len(line) - 1 else lt[0] + " "
                _b.draw.text((dx, y), s, font=_b.F[lt[1]], fill=(*color, 255))
                dx += int(_b.draw.textlength(s, font=_b.F[lt[1]]))
            y += lh + line_gap
            line, cx = [], x
        line.append(tok)
        cx += w
    if line:
        dx = x
        for li, lt in enumerate(line):
            s = lt[0] if li == len(line) - 1 else lt[0] + " "
            _b.draw.text((dx, y), s, font=_b.F[lt[1]], fill=(*color, 255))
            dx += int(_b.draw.textlength(s, font=_b.F[lt[1]]))
        y += lh
    return y


def _parse_table_line(line):
    m = re.match(r'^(Letter|Number|Jumbled letters)\s*:?\s*(.+)$', line.strip())
    if not m:
        return None
    return m.group(1), m.group(2).split()


def _render_char_boxes(y, chars, x=None, filled=False):
    """Render characters as individual cells. filled=True uses chapter table bg (like header cells)."""
    cell_w  = fig(32)
    cell_h  = fig(28)
    tx      = x if x is not None else INTRO_L1
    bor_col = _b.chapter_table_bor(_b.CH_NUM)
    fill_c  = _b.chapter_table_bg(_b.CH_NUM) if filled else WHITE

    for i, ch in enumerate(chars):
        bx = tx + i * cell_w
        _b.draw.rectangle([bx, y, bx + cell_w, y + cell_h],
                          fill=(*fill_c, 255), outline=(*bor_col, 255), width=max(1, px(0.5)))
        _b.draw.text((bx + cell_w // 2, y + cell_h // 2), ch,
                     font=_b.F["body"], fill=(*TEXT_DARK, 255), anchor="mm")
    return y + cell_h + fig(8)


def _render_table(y, letters, numbers, x=None):
    """Letter/Number grid. x defaults to INTRO_L1."""
    cell_w = fig(32)
    hdr_w  = fig(64)
    cell_h = fig(28)
    tx     = x if x is not None else INTRO_L1

    hdr_bg  = _b.chapter_table_bg(_b.CH_NUM)
    bor_col = _b.chapter_table_bor(_b.CH_NUM)

    for row_idx, (hdr, values) in enumerate([("Letter", letters), ("Number", numbers)]):
        ry = y + row_idx * cell_h
        # Header cell — Letter row: white; Number row: filled bg
        hdr_fill = hdr_bg if row_idx == 1 else WHITE
        _b.draw.rectangle([tx, ry, tx + hdr_w, ry + cell_h],
                          fill=(*hdr_fill, 255), outline=(*bor_col, 255), width=max(1, px(0.5)))
        _b.draw.text((tx + hdr_w // 2, ry + cell_h // 2), hdr,
                     font=_b.F["body"], fill=(*CHARCOAL, 255), anchor="mm")
        # Value cells — Letter row: white fill; Number row: filled bg
        val_fill = hdr_bg if row_idx == 1 else WHITE
        for ci, val in enumerate(values):
            bx = tx + hdr_w + ci * cell_w
            _b.draw.rectangle([bx, ry, bx + cell_w, ry + cell_h],
                              fill=(*val_fill, 255), outline=(*bor_col, 255), width=max(1, px(0.5)))
            _b.draw.text((bx + cell_w // 2, ry + cell_h // 2), val,
                         font=_b.F["body"], fill=(*TEXT_DARK, 255), anchor="mm")

    return y + cell_h * 2 + fig(10)


def _render_example_options(y, opts, x=None):
    """
    4 options in a single row with small checkbox squares.
    Matches Figma: □ A  text  □ B  text  □ C  text  □ D  text
    """
    start_x   = x if x is not None else INTRO_L1
    labels    = ["A", "B", "C", "D"]
    box_sz    = fig(20)
    lbl_gap   = fig(6)
    col_w     = (RIGHT_EDGE - start_x) // 4
    lh        = _lh("body")
    row_h     = max(box_sz, lh)

    radius = fig(2)   # 2px rounded corner (Figma spec)

    for i, (lbl, opt) in enumerate(zip(labels, opts)):
        ox = start_x + i * col_w
        cy = y + box_sz // 2
        # Rounded box — neutral-500 border, white fill, label centered inside
        _b.draw.rounded_rectangle([ox, y, ox + box_sz, y + box_sz],
                                  radius=radius,
                                  fill=(*WHITE, 255),
                                  outline=(151, 147, 140, 255),   # neutral-500 #97938C
                                  width=max(1, px(0.5)))
        _b.draw.text((ox + box_sz // 2, cy), lbl,
                     font=_b.F["body"], fill=(151, 147, 140, 255), anchor="mm")
        # Option text after box
        _b.draw.text((ox + box_sz + fig(6), cy), opt,
                     font=_b.F["body"], fill=(*TEXT_DARK, 255), anchor="lm")

    return y + row_h + fig(10)


def _intro_sec_heading(y, text):
    """UntitledSans Medium 14pt UPPERCASE at INTRO_L0."""
    _b.draw.text((INTRO_L0, y), text.upper(), font=_b.F["sec_head"], fill=(*CHARCOAL, 255))
    return y + _lh("sec_head") + fig(12)


def _intro_divider(y):
    """Thin horizontal rule between Type blocks."""
    _b.draw.line([(INTRO_L0, y), (RIGHT_EDGE, y)],
                 fill=(*CHARCOAL, 80), width=max(1, px(0.75)))
    return y + fig(24)


def render_intro(y, text, ch_num, ch_name):
    """
    Render structured intro text matching Figma node 232:4.
    Returns final y.
    """
    lines        = text.splitlines()
    i            = 0
    bullet_count = 0
    type_count   = 0   # to insert divider before 2nd+ Type block
    _ex_body_x   = INTRO_L1  # x where Example text body starts (updated per Example line)
    _ex_active   = False      # True after an Example line — body text aligns at _ex_body_x

    while i < len(lines):
        raw  = lines[i].rstrip()
        line = raw.strip()
        # Fix soft-hyphens / hard hyphens at word breaks
        line = line.replace("­", "").replace("-\n", "")

        if not line:
            y += fig(8)
            i += 1
            continue

        # ── Section headings ──────────────────────────────────────────────────
        if line in ("Introduction", "Types of Alphabet Test") or \
                re.match(r'^Types of Alphabet', line):
            # Extra gap before "Types of..." heading
            if "Types" in line:
                y += fig(8)
            y = _intro_sec_heading(y, line)
            i += 1
            continue

        # ── Type I/II/III/IV row ───────────────────────────────────────────────
        m = re.match(r'^(Type [IVX]+):\s*(.*)', line)
        if m:
            # Divider before 2nd+ type block
            if type_count > 0:
                y += fig(12)
                y = _intro_divider(y)
            type_count += 1

            type_label = m.group(1) + ":"
            type_title = m.group(2).strip()
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or _STRUCT_RE.match(nxt):
                    break
                if not re.match(r'^(Use |Check |Arrange |Find )', nxt):
                    type_title += " " + nxt
                    j += 1
                else:
                    break
            _ex_active = False
            # Both label and title in same "medium" font (Figma spec)
            full_line = type_label + " " + type_title
            y = draw_wrapped(y, full_line, _b.F["medium"], CHARCOAL,
                             x=INTRO_L0, max_w=RIGHT_EDGE - INTRO_L0, line_gap=fig(5))
            y += PARA_GAP
            i = j
            continue

        # ── Type description (indented to L1) ────────────────────────────────
        # Lines like "Use the given numbers...", "Check if an option word..."
        if re.match(r'^(Use |Check |Arrange |Find )', line):
            desc = line
            j    = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or _STRUCT_RE.match(nxt):
                    break
                if desc.endswith("-"):
                    desc = desc[:-1] + nxt
                else:
                    desc += " " + nxt
                j += 1
            y = draw_wrapped(y, desc, _b.F["body"], TEXT_DARK,
                             x=INTRO_L1, max_w=RIGHT_EDGE - INTRO_L1, line_gap=fig(5))
            y += PARA_GAP
            i = j
            continue

        # ── Example N: block ──────────────────────────────────────────────────
        m = re.match(r'^(Example \d+):?\s*(.*)', line)
        if m:
            ex_label = m.group(1) + ":"
            ex_text  = m.group(2).strip()
            # Compute where text body starts (label width + gap), for table alignment
            _ex_body_x = INTRO_L1 + int(_b.draw.textlength(ex_label, font=_b.F["medium"])) + fig(6)
            j        = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or _STRUCT_RE.match(nxt) or re.match(r'^[A-Z]{2,10}$', nxt):
                    break
                if ex_text.endswith("-"):
                    ex_text = ex_text[:-1] + nxt
                else:
                    ex_text += " " + nxt
                j += 1
            avail = RIGHT_EDGE - INTRO_L1
            y = _inline_label_text(y, INTRO_L1, ex_label, ex_text, avail)
            y += PARA_GAP
            _ex_active = True
            i = j
            continue

        # ── Letter / Number table ─────────────────────────────────────────────
        tbl = _parse_table_line(line)
        if tbl:
            hdr1, vals1 = tbl
            next_tbl    = None
            if i + 1 < len(lines):
                next_tbl = _parse_table_line(lines[i + 1].strip())
            if next_tbl:
                hdr2, vals2 = next_tbl
                letters = vals1 if hdr1 == "Letter" else vals2
                numbers = vals1 if hdr1 == "Number" else vals2
                y = _render_table(y, letters, numbers, x=_ex_body_x)
                i += 2
            else:
                # "Jumbled letters: E T A B L" → label + individual char boxes on same line
                label = hdr1 + ":"   # "Jumbled letters:"
                lw    = int(_b.draw.textlength(label, font=_b.F["medium"]))
                cy    = y + fig(28) // 2
                _b.draw.text((_ex_body_x, cy), label,
                             font=_b.F["medium"], fill=(*CHARCOAL, 255), anchor="lm")
                chars_x = _ex_body_x + lw + fig(10)
                chars   = vals1
                y = _render_char_boxes(y, chars, x=chars_x)
                i += 1
            continue

        # ── "Correct word = T A B L E" line ──────────────────────────────────
        if line.startswith("Correct word"):
            m_cw = re.match(r'^Correct word\s*=\s*(.+)$', line)
            if m_cw:
                label = "Correct word ="
                lw    = int(_b.draw.textlength(label, font=_b.F["medium"]))
                cy    = y + fig(28) // 2
                _b.draw.text((_ex_body_x, cy), label,
                             font=_b.F["medium"], fill=(*CHARCOAL, 255), anchor="lm")
                chars_x = _ex_body_x + lw + fig(10)
                chars   = m_cw.group(1).split()
                y = _render_char_boxes(y, chars, x=chars_x, filled=True)
            else:
                y = draw_wrapped(y, line, _b.F["body"], TEXT_DARK,
                                 x=INTRO_L1, max_w=RIGHT_EDGE - INTRO_L1, line_gap=fig(4))
            i += 1
            continue

        # ── Options inline: (A) 4,1,3,2  (B) ...  (C) ...  (D) ... ──────────
        if line.startswith("(A)"):
            opts = re.findall(r'\([ABCD]\)\s*([^(]+?)(?=\s*\([ABCD]\)|$)', line)
            opts = [o.strip() for o in opts]
            if len(opts) == 4:
                y = _render_example_options(y, opts, x=_ex_body_x)
                i += 1
                continue

        # ── Standalone letter sequence e.g. "ACEG" → single filled box ─────────
        if re.match(r'^[A-Z]{2,10}$', line):
            cell_h  = fig(28)
            bor_col = _b.chapter_table_bor(_b.CH_NUM)
            fill_c  = WHITE
            tw      = int(_b.draw.textlength(line, font=_b.F["body"]))
            pad     = fig(12)
            box_w   = tw + pad * 2
            bx      = _ex_body_x
            _b.draw.rectangle([bx, y, bx + box_w, y + cell_h],
                              fill=(*fill_c, 255), outline=(*bor_col, 255), width=max(1, px(0.5)))
            _b.draw.text((bx + box_w // 2, y + cell_h // 2), line,
                         font=_b.F["body"], fill=(*TEXT_DARK, 255), anchor="mm")
            y += cell_h + fig(8)
            i += 1
            continue

        # ── Answer: line (at L2) ──────────────────────────────────────────────
        m = re.match(r'^Answer:\s*(.*)', line)
        if m:
            avail = RIGHT_EDGE - INTRO_L1
            y = _inline_label_text(y, INTRO_L1, "Answer:", m.group(1).strip(), avail)
            y += PARA_GAP
            i += 1
            continue

        # ── Solution: block (at L2) ───────────────────────────────────────────
        m = re.match(r'^Solution:\s*(.*)', line)
        if m:
            sol_lines = [m.group(1).strip()]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or re.match(r'^Answer:', nxt):
                    break
                sol_lines.append(nxt)
                j += 1
            sol_x = _ex_body_x if _ex_active else INTRO_L1
            avail = RIGHT_EDGE - sol_x
            # First line inline with "Solution:" label
            y = _inline_label_text(y, sol_x, "Solution:", sol_lines[0], avail)
            # Remaining lines as separate paragraphs at sol_x
            for sol_cont in sol_lines[1:]:
                y += fig(4)
                y = draw_wrapped(y, sol_cont, _b.F["body"], TEXT_DARK,
                                 x=sol_x, max_w=avail, line_gap=fig(5))
            y += PARA_GAP
            i = j
            continue

        # ── Bullet: "y Item text" ─────────────────────────────────────────────
        if line.startswith("y "):
            btext = line[2:].strip()
            bullet_count += 1
            cy = y + _lh("body") // 2
            r  = fig(3)
            _b.draw.ellipse([INTRO_L0 + fig(2), cy - r, INTRO_L0 + fig(2) + r * 2, cy + r],
                            fill=(*CHARCOAL, 255))
            y = draw_wrapped(y, btext, _b.F["body"], TEXT_DARK,
                             x=INTRO_L0 + fig(18),
                             max_w=RIGHT_EDGE - INTRO_L0 - fig(18),
                             line_gap=fig(5))
            # Double spacing after the 4th bullet
            if bullet_count == 4:
                y += fig(20)
            i += 1
            continue

        # ── Divider marker between Type blocks ───────────────────────────────
        # Rendered after Answer/Solution when we detect the next Type coming
        # (handled automatically by the Type block — just skip raw blank lines here)

        # ── Default body text ─────────────────────────────────────────────────
        combined = line
        j        = i + 1
        while j < len(lines):
            nxt = lines[j].strip()
            if not nxt or _STRUCT_RE.match(nxt) or re.match(r'^[A-Z]{2,10}$', nxt):
                break
            if combined.endswith("-"):
                combined = combined[:-1] + nxt
            else:
                combined += " " + nxt
            j += 1
        body_x   = _ex_body_x if _ex_active else INTRO_L0
        y = draw_wrapped(y, combined, _b.F["body"], TEXT_DARK,
                         x=body_x, max_w=RIGHT_EDGE - body_x, line_gap=fig(5))
        y += PARA_GAP
        i = j
        continue

    return y

# ─── Letter tile renderer ─────────────────────────────────────────────────────

def render_letter_tiles(y, tiles, x=None, show_nums=True):
    """Draw Letter row (+ optional Number row) as individual boxes, matching page 1 table style."""
    n       = len(tiles)
    cell_w  = fig(32)
    cell_h  = fig(28)
    tx      = x if x is not None else LEFT
    hdr_bg  = _b.chapter_table_bg(_b.CH_NUM)
    bor_col = _b.chapter_table_bor(_b.CH_NUM)

    rows = [(tiles, False)]
    if show_nums:
        rows.append(([str(i+1) for i in range(n)], True))

    for row_idx, (values, filled) in enumerate(rows):
        ry = y + row_idx * cell_h
        fill_c = hdr_bg if filled else WHITE
        for ci, val in enumerate(values):
            bx = tx + ci * cell_w
            _b.draw.rectangle([bx, ry, bx + cell_w, ry + cell_h],
                              fill=(*fill_c, 255), outline=(*bor_col, 255), width=max(1, px(0.5)))
            _b.draw.text((bx + cell_w // 2, ry + cell_h // 2), val,
                         font=_b.F["body"], fill=(*TEXT_DARK, 255), anchor="mm")

    rows_drawn = 2 if show_nums else 1
    return y + rows_drawn * cell_h + fig(8)

# ─── Question renderer ────────────────────────────────────────────────────────

def render_question(y, q):
    """Render a single question. Returns new y."""
    num  = int(q.get("num", "1"))
    text = q.get("text", "").strip()
    opts_dict = q.get("options", {})
    opts = [opts_dict.get(k, "") for k in ("A", "B", "C", "D") if k in opts_dict]
    qtype = q.get("type", "text_only")

    # Question text (skip if empty for tile-only questions)
    if text:
        y = draw_q(y, num, text)
        y += fig(6)
    else:
        # Draw badge top-aligned with tiles
        badge_h = _b._line_h(_b.F["q_text"]) + fig(6)
        bg  = _b.chapter_badge_bg(_b.CH_NUM)
        bor = _b.chapter_color(_b.CH_NUM)
        _b.draw.rounded_rectangle(
            [LEFT, y, LEFT + Q_BADGE_W, y + badge_h],
            radius=px(4), fill=(*bg, 255), outline=(*bor, 255), width=max(1, px(0.5)))
        _b.draw.text((LEFT + Q_BADGE_W // 2, y + badge_h // 2),
                     f"{num:02d}.", font=_b.F["q_badge"], fill=(*CHARCOAL, 255), anchor="mm")
        # Do NOT advance y — tiles start at same y as badge

    # Letter tiles — start at Q_TEXT_X (same line as badge)
    if qtype == "letter_tile" and q.get("tiles"):
        y = render_letter_tiles(y, q["tiles"], x=Q_TEXT_X, show_nums=True)
    elif qtype == "letter_tile_no_nums" and q.get("tiles"):
        y = render_letter_tiles(y, q["tiles"], x=Q_TEXT_X, show_nums=False)
        if q.get("subtext"):
            y = draw_wrapped(y, q["subtext"], _b.F["body"], TEXT_DARK,
                             x=Q_TEXT_X, max_w=RIGHT_EDGE - Q_TEXT_X, line_gap=fig(4))
            y += fig(4)
    elif qtype in ("letter_plain", "letter_plain_subtext") and q.get("tiles"):
        text_str = "  ".join(q["tiles"])
        lh = _lh("medium")
        badge_h = lh + fig(6)
        cy = y + badge_h // 2
        _b.draw.text((Q_TEXT_X, cy), text_str, font=_b.F["medium"], fill=(*TEXT_DARK, 255), anchor="lm")
        y += badge_h + fig(4)
        if qtype == "letter_plain_subtext" and q.get("subtext"):
            y = draw_wrapped(y, q["subtext"], _b.F["body"], TEXT_DARK,
                             x=Q_TEXT_X, max_w=RIGHT_EDGE - Q_TEXT_X, line_gap=fig(4))
            y += fig(4)

    # Extra gap after tiles (per-question override)
    if q.get("tiles_gap") and q.get("tiles"):
        y += fig(q["tiles_gap"])

    # Options
    if opts:
        layout = q.get("options_layout", "auto")
        if layout == "2col":
            y = options_2col(y, opts)
        elif layout == "1row":
            y = _options_row(y, opts)
        else:
            y = options_auto(y, opts)

    return y

# ─── Page renderer ────────────────────────────────────────────────────────────

def render_page(page_desc, page_num, total_pages):
    """
    Set up canvas, draw template + content.
    page_num is 1-based within the full chapter.
    """
    sec_type = page_desc["type"]
    ch_num   = int(page_desc["chapter_num"])
    ch_name  = page_desc["chapter_name"]

    section_label = (
        "Grade 3: Cumulative Assessment"
        if ch_name.startswith("Cumulative")
        else "Grade 3: Logical Reasoning"
    )

    setup(ch_num, ch_name, page_num)

    if sec_type == "intro":
        intro_pg = page_desc.get("intro_page", 1)
        if intro_pg == 1:
            temp1_header()
            y = CONTENT_TOP_T1
        else:
            temp3_header()
            y = CONTENT_TOP_T34

        y = render_intro(y, page_desc.get("text", ""), ch_num, ch_name)

    else:
        # Determine template from position within section
        sec_idx = page_desc.get("section_index", 0)  # 0-based within section

        if page_desc.get("is_first_in_section"):
            temp2_header(page_desc["section_title"])
            y = CONTENT_TOP_T1
        elif sec_idx == 1:
            temp3_header()
            y = CONTENT_TOP_T34
        else:
            temp4_header()
            y = CONTENT_TOP_T34

        # Render questions
        last_direction = ""
        for q in page_desc.get("questions", []):
            direction = q.get("direction", "").strip()
            direction = re.sub(r'-\n', '', direction)       # join hyphenated line breaks
            direction = re.sub(r'\s+', ' ', direction.replace("\n", " "))
            if direction and direction != last_direction:
                # Bold "Directions (N-M):" prefix + light rest
                m = re.match(r'^(Directions\s*\([^)]+\):?)\s*(.*)', direction, re.DOTALL)
                if m:
                    y = directions_block(y, m.group(1), m.group(2).strip())
                else:
                    y = draw_wrapped(y, direction, _b.F["direction"], TEXT_DARK, line_gap=fig(4))
                y += fig(6)
                last_direction = direction

            y = render_question(y, q)
            y = separator(y, gap_before=fig(12), gap_after=fig(24))

            # Overflow guard — stop if past safe bottom
            if y > CONTENT_BOT - fig(30):
                break

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate a single page (PIL 300 DPI)")
    parser.add_argument("--content", required=True,  help="Path to content.json")
    parser.add_argument("--page",    required=True, type=int, help="Page index (1-based)")
    parser.add_argument("--output",  required=True,  help="Output PDF path")
    args = parser.parse_args()

    if not os.path.exists(args.content):
        print(f"Error: {args.content} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.content, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data["chapters"]:
        print("Error: no chapters in content.json", file=sys.stderr)
        sys.exit(1)

    chapter = data["chapters"][0]
    pages   = build_page_plan(chapter)
    total   = len(pages)
    idx     = args.page - 1

    if idx < 0 or idx >= total:
        print(f"Error: page {args.page} out of range (1–{total})", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    render_page(pages[idx], args.page, total)

    out_dir  = os.path.dirname(os.path.abspath(args.output))
    basename = os.path.splitext(os.path.basename(args.output))[0]
    finish(basename, out_dir=out_dir)

    # Print total to stdout so agent can read it
    print(total, flush=True)


if __name__ == "__main__":
    main()
