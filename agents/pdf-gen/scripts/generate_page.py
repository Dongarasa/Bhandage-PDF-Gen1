"""
generate_page.py — Generate a single page PDF from extracted chapter content.

Usage:
  python3 generate_page.py \
    --content <path/to/content.json> \
    --page <page_index>            (1-based)
    --output <path/to/page-001.pdf>

Page index tells which page of the chapter to render:
  1       = intro page
  2, 3... = MCQ pages
  last    = assessment/cumulative pages
"""

import argparse
import json
import math
import os
import sys

# Import shared drawing functions from generate_pdf
sys.path.insert(0, os.path.dirname(__file__))
from generate_pdf import (
    canvas, A4,
    W, H, MARGIN_L, MARGIN_R, MARGIN_TOP, MARGIN_BOTTOM, CONTENT_W,
    C_BG, C_TEXT, C_SECONDARY, C_WHITE, C_HEADER, C_ACCENT,
    C_BADGE_Q, C_BADGE_OPT_BOR, C_DIVIDER, C_TILE_BG, C_TILE_BOR, C_FOOTER,
    FS_CHAPTER_TITLE, FS_CHAPTER_SUB, FS_BODY, FS_FOOTER, FS_SECTION_HEAD,
    Q_BADGE_SIZE, OPT_BADGE_W, OPT_BADGE_H, TILE_SIZE, TILE_GAP,
    Q_SPACING, LINE_SPACING, OPT_SPACING,
    draw_page_background, draw_content_header, draw_footer,
    draw_chapter_intro_header, draw_rounded_rect, draw_circle,
    wrap_text, draw_wrapped_text, text_height,
    render_section_heading, render_directions, render_question,
    render_intro_section, PageState,
    F_BODY, F_BOLD, F_MEDIUM, F_DISPLAY,
    colors,
)

# Questions per MCQ page
Q_PER_PAGE = 8


def build_page_plan(chapter_data):
    """
    Returns a list of page descriptors, one per page to be generated.
    Each descriptor: {"type": "intro"|"mcq"|"assessment"|"cumulative", "questions": [...], "start_q": N}
    """
    pages = []

    ch_num = chapter_data["chapter_key"]
    ch_name = chapter_data["chapter_name"]

    for sec in chapter_data["sections"]:
        sec_type = sec["type"]

        if sec_type == "intro":
            pages.append({
                "type": "intro",
                "chapter_num": ch_num,
                "chapter_name": ch_name,
                "text": sec.get("text", ""),
                "questions": [],
            })

        elif sec_type in ("mcq", "assessment", "cumulative"):
            questions = sec.get("questions", [])
            # Split questions into pages of Q_PER_PAGE each
            for chunk_start in range(0, max(len(questions), 1), Q_PER_PAGE):
                chunk = questions[chunk_start: chunk_start + Q_PER_PAGE]
                pages.append({
                    "type": sec_type,
                    "chapter_num": ch_num,
                    "chapter_name": ch_name,
                    "questions": chunk,
                    "is_first_in_section": chunk_start == 0,
                    "section_title": {
                        "mcq": "Multiple Choice Questions",
                        "assessment": "Chapter Assessment",
                        "cumulative": ch_name,
                    }.get(sec_type, sec_type.title()),
                })

    return pages


def render_page(c, page_desc, page_num, total_pages, image_dir=None):
    """Render a single page onto canvas c."""
    sec_type = page_desc["type"]
    ch_num = page_desc["chapter_num"]
    ch_name = page_desc["chapter_name"]

    if ch_name.startswith("Cumulative"):
        section_label = "Grade 3: Cumulative Assessment"
    else:
        section_label = "Grade 3: Logical Reasoning"

    draw_page_background(c)

    if sec_type == "intro":
        state = PageState(c, f"Chapter {ch_num}: {ch_name}", section_label, page_num)
        draw_footer(c, page_num, section_label)
        render_intro_section(c, state, page_desc.get("text", ""), ch_num, ch_name)

    else:
        draw_content_header(c, f"Chapter {ch_num}: {ch_name}", section_label)
        draw_footer(c, page_num, section_label)
        state = PageState(c, f"Chapter {ch_num}: {ch_name}", section_label, page_num)

        # Section title banner (only on first page of section)
        if page_desc.get("is_first_in_section"):
            banner_h = 52
            banner_y = state.y - banner_h
            # Pink banner block
            c.setFillColor(C_HEADER)
            c.rect(0, banner_y, W * 0.55, banner_h, fill=1, stroke=0)
            # Chapter name (small)
            c.setFillColor(C_WHITE)
            c.setFont(F_BODY(), 8)
            c.drawString(MARGIN_L, banner_y + banner_h - 16, f"Chapter {ch_num}: {ch_name}")
            # Section title (large)
            c.setFont(F_DISPLAY(), 18)
            c.drawString(MARGIN_L, banner_y + 10, page_desc["section_title"])
            state.y = banner_y - 16

        # Render questions
        last_direction = ""
        for q in page_desc.get("questions", []):
            direction = q.get("direction", "")
            if direction and direction != last_direction:
                render_directions(c, state, direction)
                last_direction = direction
            render_question(c, state, q, image_dir)


def main():
    parser = argparse.ArgumentParser(description="Generate a single page from Cuemath IMO content")
    parser.add_argument("--content", required=True, help="Path to content.json")
    parser.add_argument("--page", required=True, type=int, help="Page index (1-based)")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--images", default=None, help="Directory with extracted images")
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
    pages = build_page_plan(chapter)

    total = len(pages)
    idx = args.page - 1  # convert to 0-based

    if idx < 0 or idx >= total:
        print(f"Error: page {args.page} out of range (1–{total})", file=sys.stderr)
        print(f"Available pages: {total}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    c = canvas.Canvas(args.output, pagesize=A4)
    render_page(c, pages[idx], args.page, total, args.images)
    c.save()

    print(f"Page {args.page}/{total} saved: {args.output}", file=sys.stderr)
    # Print total pages to stdout so agent can read it
    print(total)


if __name__ == "__main__":
    main()
