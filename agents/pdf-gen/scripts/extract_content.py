"""
extract_content.py — Extract structured content from Cuemath IMO source PDF.

Usage:
  python3 extract_content.py --input <pdf_path> --output <json_path> [--chapter all|1|2|3|ca1...]
"""

import argparse
import json
import re
import sys
import os
import pdfplumber

# ── Chapter map (page numbers are 1-indexed PDF pages) ──────────────────────
CHAPTER_MAP = {
    1:   {"name": "Patterns",                               "start_page": 7},
    2:   {"name": "Analogy and Classification",             "start_page": 21},
    3:   {"name": "Alphabet Test",                          "start_page": 33},
    "ca1": {"name": "Cumulative Assessment - I",            "start_page": 41},
    4:   {"name": "Coding and Decoding",                    "start_page": 47},
    5:   {"name": "Ranking Test",                           "start_page": 55},
    6:   {"name": "Grouping of Figure and Figure Matrix",   "start_page": 65},
    "ca2": {"name": "Cumulative Assessment - II",           "start_page": 79},
    7:   {"name": "Mirror Images",                          "start_page": 85},
    8:   {"name": "Geometrical Shapes",                     "start_page": 101},
    9:   {"name": "Embedded Figures",                       "start_page": 115},
    10:  {"name": "Days, Dates, and Possible Combinations", "start_page": 129},
    "ca3": {"name": "Cumulative Assessment - III",          "start_page": 143},
}

# ── Noise patterns to strip ───────────────────────────────────────────────────
NOISE = [
    re.compile(r"^©\s*Cue Learn Pvt\. Ltd\..*$"),
    re.compile(r"^Grade \d+: (Logical Reasoning|Mathematics)\s*$"),
    re.compile(r"^\d{1,3}\s*©\s*Cue Learn.*$"),
    re.compile(r"^\d{1,3}\s*$"),
    re.compile(r"^Grade$"),
    re.compile(r"^Chapter \d+: .+$"),   # running header
]

def is_noise(line):
    s = line.strip()
    for p in NOISE:
        if p.match(s):
            return True
    return False


def extract_pages(pdf_path, start_page, end_page):
    """Extract and clean text from a range of PDF pages using pdfplumber."""
    lines_out = []
    with pdfplumber.open(pdf_path) as pdf:
        for pnum in range(start_page - 1, min(end_page, len(pdf.pages))):
            page = pdf.pages[pnum]
            text = page.extract_text() or ""
            for line in text.split("\n"):
                if not is_noise(line):
                    lines_out.append(line)
            lines_out.append("")  # page separator
    return "\n".join(lines_out)


# ── Option parsing ────────────────────────────────────────────────────────────
def parse_options(block_text):
    """Extract A/B/C/D options from a question block (handles both layouts)."""
    options = {}

    # Pattern 1: "(A) text (B) text" on same line
    inline = re.findall(r"\(([A-D])\)\s+(.+?)(?=\s*\([A-D]\)|\s*$)", block_text)
    if inline:
        for letter, text in inline:
            options[letter] = text.strip()
        if len(options) >= 2:
            return options

    # Pattern 2: "(A) text" on separate lines (possibly with leading spaces)
    for line in block_text.split("\n"):
        for letter in "ABCD":
            m = re.match(rf"^\s*\({letter}\)\s+(.+)$", line.strip())
            if m:
                options[letter] = m.group(1).strip()

    return options


def detect_type(q_text):
    """Detect question type: letter_tile, image_based, or text_only."""
    # Letter tiles: spaced-out UPPERCASE letters (e.g. "G T O U H H T")
    if re.search(r"(?:^|\n)([A-Z] ){3,}[A-Z]", q_text):
        return "letter_tile"
    image_kws = [
        "figure", "shown below", "given below", "following figure",
        "observe", "arrangement", "sequence", "shapes", "analogy",
        "mirror", "embedded", "missing piece", "rotating pattern",
        "overlapping", "circular arrangement",
    ]
    for kw in image_kws:
        if kw.lower() in q_text.lower():
            return "image_based"
    return "text_only"


def parse_letter_tiles(text):
    """Extract individual letters from a letter-tile line."""
    for line in text.split("\n"):
        stripped = line.strip()
        # Match spaced letters: "G T O U H H T" or "N E A S T L P"
        m = re.match(r"^([A-Z] ){2,}[A-Z]$", stripped)
        if m:
            return stripped.replace(" ", "")  # return as string "GTOUHHT"
    return ""


def clean_question_text(text, q_type, tiles_str):
    """Remove letter-tile lines and number-sequence lines from question text."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        s = line.strip()
        # Skip the tile letter line if we already captured it
        if q_type == "letter_tile" and re.match(r"^([A-Z] ){2,}[A-Z]$", s):
            continue
        # Skip number sequence lines "1 2 3 4 5 6 7"
        if re.match(r"^(\d\s+){2,}\d$", s):
            continue
        # Skip "(A) ... (B) ..." option lines
        if re.match(r"^\s*\([A-D]\)", s):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def parse_questions_block(text, section_type):
    """Parse Q1./Q2.../Q01 style questions from a text block."""
    questions = []

    # Split on "Qn." or "Qnn." at start of line
    parts = re.split(r"(?m)^Q(\d{1,2})\.\s*", text)
    if len(parts) < 3:
        return questions

    for i in range(1, len(parts) - 1, 2):
        num = parts[i].strip().zfill(2)
        content = parts[i + 1].strip()

        options = parse_options(content)
        tiles_str = parse_letter_tiles(content)
        q_type = detect_type(content) if tiles_str else detect_type(content)
        if tiles_str:
            q_type = "letter_tile"

        # Get direction for this question if embedded
        direction = ""
        dir_match = re.search(
            r"(Directions?\s*\(\d+[–\-]\d+\)\s*:.*?)(?=Q\d|\Z)",
            content, re.DOTALL
        )

        q_text = clean_question_text(content, q_type, tiles_str)

        questions.append({
            "num": num,
            "text": q_text,
            "type": q_type,
            "tiles": list(tiles_str) if tiles_str else [],
            "options": options,
            "answer": "",
            "direction": direction,
            "section": section_type,
            "source_page": None,
        })

    return questions


# ── Section splitting ─────────────────────────────────────────────────────────
SECTION_HEADS = {
    "mcq":        re.compile(r"^Multiple Choice Questions\s*$", re.IGNORECASE),
    "assessment": re.compile(r"^Chapter Assessment\s*$", re.IGNORECASE),
    "cumulative": re.compile(r"^Cumulative Assessment", re.IGNORECASE),
}

def split_into_sections(full_text):
    """Split full chapter text into named sections."""
    sections = []
    current_type = "intro"
    current_lines = []

    for line in full_text.split("\n"):
        matched_type = None
        for sec_type, pat in SECTION_HEADS.items():
            if pat.match(line.strip()):
                matched_type = sec_type
                break

        if matched_type:
            if current_lines:
                sections.append({"type": current_type, "content": "\n".join(current_lines)})
            current_type = matched_type
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({"type": current_type, "content": "\n".join(current_lines)})

    return sections


def split_directions(text):
    """Split MCQ text into direction-labeled blocks."""
    # Find all direction headers and their positions
    dir_pat = re.compile(
        r"(Directions?\s*\(\d+[–\-]\d+\)\s*:(?:[^\n]*)(?:\n(?!Q\d).*)*)",
        re.MULTILINE
    )
    blocks = []
    last_end = 0
    last_dir = ""

    for m in dir_pat.finditer(text):
        # Questions before this direction header (no specific direction)
        before = text[last_end:m.start()].strip()
        if before:
            blocks.append({"direction": last_dir, "content": before})
        last_dir = m.group(1).strip()
        last_end = m.end()

    # Remaining content after last direction
    remaining = text[last_end:].strip()
    if remaining:
        blocks.append({"direction": last_dir, "content": remaining})

    if not blocks:
        blocks = [{"direction": "", "content": text}]

    return blocks


def extract_chapter(pdf_path, chapter_key, chapter_info, next_page):
    """Extract and structure a chapter from the PDF."""
    start = chapter_info["start_page"]
    end = (next_page - 1) if next_page else start + 20

    print(f"  Pages {start}–{end}...", file=sys.stderr)
    full_text = extract_pages(pdf_path, start, end)

    sections_raw = split_into_sections(full_text)
    parsed_sections = []

    for sec in sections_raw:
        sec_type = sec["type"]
        content = sec["content"]

        if sec_type == "intro":
            parsed_sections.append({
                "type": "intro",
                "text": content.strip(),
                "questions": [],
            })
        else:
            # Split by direction headers, then parse questions in each block
            dir_blocks = split_directions(content)
            all_questions = []
            for block in dir_blocks:
                qs = parse_questions_block(block["content"], sec_type)
                for q in qs:
                    if not q["direction"]:
                        q["direction"] = block["direction"]
                all_questions.extend(qs)

            parsed_sections.append({
                "type": sec_type,
                "questions": all_questions,
            })

    return {
        "chapter_key": str(chapter_key),
        "chapter_name": chapter_info["name"],
        "start_page": start,
        "end_page": end,
        "sections": parsed_sections,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract Cuemath IMO book content")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--chapter", default="all")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    # Determine chapters to extract
    if args.chapter.lower() == "all":
        keys = list(CHAPTER_MAP.keys())
    else:
        keys = []
        for r in args.chapter.split(","):
            r = r.strip()
            try:
                keys.append(int(r))
            except ValueError:
                keys.append(r)

    # Sorted by start page for next-chapter detection
    all_keys_sorted = sorted(CHAPTER_MAP.keys(), key=lambda k: CHAPTER_MAP[k]["start_page"])

    result = {"book_title": "IMO Logical Reasoning Grade 3", "chapters": []}

    for key in keys:
        if key not in CHAPTER_MAP:
            print(f"Warning: '{key}' not in CHAPTER_MAP", file=sys.stderr)
            continue
        info = CHAPTER_MAP[key]
        try:
            idx = all_keys_sorted.index(key)
            next_key = all_keys_sorted[idx + 1] if idx + 1 < len(all_keys_sorted) else None
            next_page = CHAPTER_MAP[next_key]["start_page"] if next_key else None
        except (ValueError, KeyError):
            next_page = None

        print(f"Chapter {key}: {info['name']}", file=sys.stderr)
        ch_data = extract_chapter(args.input, key, info, next_page)
        result["chapters"].append(ch_data)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    total_q = sum(
        len(sec["questions"])
        for ch in result["chapters"]
        for sec in ch["sections"]
    )
    print(f"\n✓ {len(result['chapters'])} chapters, {total_q} questions → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
