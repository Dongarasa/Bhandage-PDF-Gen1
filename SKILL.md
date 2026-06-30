---
name: pdf-gen
description: >
  Cuemath IMO Workbook PDF Generator. Converts source IMO PDF into the
  Updated Layout design — chapter color theming, Figma-matched templates,
  Cuemath branding. PIL + img2pdf stack at 300 DPI. Invoke with /my pdf-gen.
---

# PDF Generator Agent — Cuemath IMO Workbook

Converts Cuemath IMO source book pages into the **Updated Layout** design format,
one page at a time, using PIL (Pillow) + img2pdf at 300 DPI.

---

## Tech Stack

| Tool | Role |
|---|---|
| **PIL (Pillow)** | Canvas drawing at 300 DPI (2480 × 3508 px for A4) |
| **img2pdf** | PNG → exact 300 DPI PDF conversion |
| **PyMuPDF (fitz)** | Source PDF text extraction |
| **rsvg-convert** | SVG logo → transparent PNG (brew install librsvg) |

Key helper: `fig(p72) = int(p72 * 300/72)` — converts Figma 72-DPI px to 300-DPI px.

---

## Scripts

All scripts live in `personal/agents/pdf-gen/scripts/`.

| Script | Purpose |
|---|---|
| `imo_g3_base.py` | Shared base: canvas setup, fonts, colors, template headers, logo, footer, draw helpers |
| `generate_g3_page.py` | Page builder: reads content.json, calls base templates, renders intro/MCQ/CA pages |
| `extract_content.py` | Extracts text from source PDF into content.json |
| `draw_hex_q3.py` | Standalone PIL script — generates Q3 hex-overlap diagram PNG (see Hex Diagram section) |

---

## Workflow

### Step 1 — Extract content

```bash
python3 personal/agents/pdf-gen/scripts/extract_content.py \
  --input "<source_pdf_path>" \
  --output personal/workspace/pdf-gen/ch<N>/content.json \
  --chapter <N>
```

Source PDF: `~/Documents/Workbook/Source/Final_Update_IMO.LR.G3_Book.pdf`

---

### Step 2 — Generate pages (one at a time)

**`--page` is 1-based.** Always ask before generating a NEW page. After a fix, regenerate + open automatically without asking.

```bash
python3 personal/agents/pdf-gen/scripts/generate_g3_page.py \
  --content personal/workspace/pdf-gen/ch<N>/content.json \
  --page <1-based page number> \
  --output personal/workspace/pdf-gen/ch<N>/page-<NNN>.pdf
```

After generation, open immediately in Adobe Acrobat DC:
```bash
open -a "/Applications/Adobe Acrobat DC/Adobe Acrobat.app" personal/workspace/pdf-gen/ch<N>/page-<NNN>.pdf
```

Then ask: **"Theek hai? Ya kuch fix karna hai?"** — wait for approval before next page.

---

### Step 3 — Merge into final PDF

```bash
python3 -c "
from pypdf import PdfWriter, PdfReader
import glob
pages = sorted(glob.glob('personal/workspace/pdf-gen/ch<N>/page-*.pdf'))
w = PdfWriter()
for p in pages:
    w.append(PdfReader(p))
with open('personal/workspace/pdf-gen/ch<N>/chapter-<N>.pdf', 'wb') as f:
    w.write(f)
print('Done')
"
```

---

## Page Templates (Figma)

| Template | Figma Node | Header | When to use |
|---|---|---|---|
| **Temp1** | 232:4 | Full color bar (92px) + Chapter name + Grade pill | Chapter intro **page 1** |
| **Temp2** | 232:12 | Full color bar (92px) + "Ch N: ChName" + section title | MCQ/CA section **first page** |
| **Temp3** | 232:17 | L-shape bezier curve (top+left) + Logo top-right | Chapter intro **page 2** + MCQ **page 2** |
| **Temp4** | 232:21 | Thin 12px strip + Logo top-right | MCQ/CA **page 3 onwards** |

---

## Chapter Color System

| Slot | Chapters | 500 (accent) | 100 (page bg) | 200 (table bg) | 700 (table border) |
|---|---|---|---|---|---|
| 0 | 1, 5, 9 | Gold `#F4AB52` | `#FAF1E6` | `#FAE6D0` | `#CE7E12` |
| 1 | 2, 6, 10 | Error `#F97279` | `#FFE9E9` | `#FFD6D5` | `#C8444F` |
| 2 | 3, 7, 11 | Info `#74ACFC` | `#EEF6FF` | `#DEECFF` | `#407BD6` |
| 3 | 4, 8, 12 | Success `#6AC88A` | `#ECF9EF` | `#DAF3E0` | `#28995A` |

Badge bg (300-shade): Gold `#FAD6AC`, Error `#FFB8B7`, Info `#C1DCFF`, Success `#BCEAC8`.

---

## Fonts

| Key | Font file | Size | Used for |
|---|---|---|---|
| `ch_num` | Athletics-Regular.otf | 14pt | Chapter number |
| `ch_title` | Athletics-Light.otf | 24pt | Chapter title |
| `ch_big` | Athletics-Black.otf | 32pt | Large decorative chapter number |
| `grade` | Athletics-Regular.otf | 12pt | Grade pill |
| `sec_head` | UntitledSans-Medium.otf | 14pt | Section headings |
| `medium` | UntitledSans-Medium.otf | 12pt | Labels, bold inline text |
| `body` | UntitledSans-Regular.otf | 12pt | Body text |
| `direction` | UntitledSans-Regular.otf | 12pt | Direction continuation (NOT Light) |
| `q_badge` | UntitledSans-Medium.otf | 12pt | Question number in badge |
| `q_text` | UntitledSans-Regular.otf | 12pt | Question main text |
| `opt_label` | UntitledSans-Medium.otf | 10pt | ABCD label inside checkbox |
| `opt_text` | UntitledSans-Regular.otf | 12pt | Option answer text |
| `footer` | UntitledSans-Regular.otf | 10pt | Footer text |

---

## Intro Page Layout

| Level | px | Used for |
|---|---|---|
| `INTRO_L0 = fig(40)` | 40px | Section headings, "Type X:" label |
| `INTRO_L1 = fig(87)` | 87px | Type description text, Answer label |
| `_ex_body_x` | dynamic | Body/Solution inside Example block |

- **`_ex_active` break condition**: empty line, `_STRUCT_RE` match, or `re.match(r'^[A-Z]{2,10}', nxt)`
- **Paragraph spacing**: `PARA_GAP = fig(8)` after every block
- **Answer**: always at `INTRO_L1` (not affected by `_ex_active`)

### Inline Styled Text (`**word**` marker)

To render a specific word in Medium weight inside any text, wrap it with `**...**` in content.json:

```
"Which word cannot be formed from letters of word **MOTHER**?"
```

- `_draw_wrapped_styled(y, text, color, x, max_w)` in `generate_g3_page.py` handles this for intro/example text
- `_draw_wrapped_caps_q(y, text, x, max_w)` in `imo_g3_base.py` handles this for MCQ question text

### Letter/Number Table (`_render_table`)

- **Letter row** (top): header cell = white, value cells = white
- **Number row** (bottom): header cell = `chapter_table_bg`, value cells = `chapter_table_bg` (filled)

### Standalone Letter Sequence (e.g. "ACEG")

Single box drawn at `_ex_body_x` — **white fill**, chapter border.

---

## MCQ Page Layout

### Pagination

```python
Q_FIRST_PAGE  = 4   # MCQ page 1 (Temp2)
Q_SECOND_PAGE = 5   # MCQ page 2 (Temp3)
Q_PER_PAGE    = 7   # MCQ page 3+ (Temp4)
```

### Directions Block

- `prefix` ("Directions (1-5):") → `F["medium"]`, CHARCOAL
- `rest` (continuation) → `F["direction"]` (Regular), TEXT_DARK
- Hyphenated line breaks (`let-\nters`) in direction text are stripped before rendering: `re.sub(r'-\n', '', direction)`

### Question Text (`draw_q`)

Uses `_draw_wrapped_caps_q` which renders:
- ALL_CAPS words (2+ chars, e.g. COMFORTABLE, INTERNATIONAL) → `F["medium"]`
- `**marked**` words → `F["medium"]`
- Everything else → `F["q_text"]` (Regular)

### Question Types

| Type | Tiles display | Number row | Tiles font |
|---|---|---|---|
| `letter_tile` | Individual boxes, white fill, same y as badge | Yes (filled bg row below) | — |
| `letter_tile_no_nums` | Individual boxes, white fill, same y as badge | No | — |
| `letter_plain` | Plain spaced text `"  ".join(tiles)` same y as badge | No | `F["medium"]` |
| `letter_plain_subtext` | Plain spaced text + subtext below | No | `F["medium"]` |
| `text_only` | No tiles; only question text + options | — | — |

**`letter_tile_no_nums` with subtext**: if `q.get("subtext")` is set, it renders below the tile row before options.

**`letter_plain` tiles use `F["medium"]`** (Medium weight), not `F["body"]`.

### Per-question Content Fields

| Field | Type | Effect |
|---|---|---|
| `options_layout` | `"2col"` / `"1row"` / `"auto"` | Override options layout (default: auto) |
| `tiles_gap` | int (Figma px) | Extra gap between tiles and options: `y += fig(tiles_gap)` |
| `subtext` | string | Text rendered below tiles, above options |

### ABCD Options

- `_OPT_BOX = fig(20)` — checkbox size
- `_OPT_NEUTRAL = (151, 147, 140)` — neutral-500 border + label color
- **2-col** (`options_2col`): `row_h = _OPT_BOX + fig(4)`
- **4-col** (`_options_row`): `row_h = _OPT_BOX + fig(10)`
- **auto** (`options_auto`): uses `_fits_row()` to choose 4-col or 2-col

### Separator

```python
y = separator(y, gap_before=fig(12), gap_after=fig(24))
# fill=(*CHARCOAL, 80), width=max(1, px(0.75))
```

---

## Content.json Structure

```json
{
  "chapters": [{
    "chapter_key": 3,
    "chapter_name": "Alphabet Test",
    "sections": [
      { "type": "intro", "text": "...", "source_pages": [32, 33] },
      { "type": "mcq", "questions": [...] },
      { "type": "assessment", "questions": [...] }
    ]
  }]
}
```

### Ch3 MCQ Question Type Map

| Q# | type | tiles | text | subtext |
|---|---|---|---|---|
| Q1–Q5 | `letter_tile` | letters | question text | — |
| Q6–Q7 | `letter_tile_no_nums` | letters | `""` | — |
| Q8–Q9 | `letter_plain` | letters | `""` | — |
| Q10–Q14 | `letter_plain` | letters | `""` | — |
| Q15–Q16 | `letter_plain` | letters | question text | — |
| Q17–Q20 | `letter_tile_no_nums` | letters | `""` | `"The word formed belongs to:"` |

### Ch3 CA (Cumulative Assessment) Question Type Map

CA is a separate section (`"type": "assessment"` or `"type": "ca"`) that comes after the regular Assessment. It uses `diagram_geo` for visual questions and `text_only` for others.

| Q# | type | notes |
|---|---|---|
| Q1 | `diagram_geo` | `kind: matrix_3x3`, `visual_opts` for ABCD shapes |
| Q2 | `diagram_geo` | `kind: rotate_seq`, `visual_opts_rotations` for ABCD |
| Q3 | `diagram_geo` | Custom PIL PNG (`hex-overlap-q3.png`), `max_width_figma: 120`, text options A=5,B=8,C=7,D=6 |

For Q3 diagram, use `"image"` field pointing to the generated PNG path, NOT a `kind`-based diagram:

```json
{
  "type": "diagram_geo",
  "text": "...",
  "diagram": {
    "image": "personal/workspace/illustrate/props/hex-overlap-q3.png",
    "max_width_figma": 120
  },
  "options": ["5", "8", "7", "6"]
}
```

### Ch3 Assessment Question Type Map

| Q# | type | notes |
|---|---|---|
| Q1–Q2 | `text_only` | plain question text |
| Q3 | `letter_tile` | tiles + options_layout=2col |
| Q4 | `text_only` | options_layout=2col |
| Q5 | `text_only` | EDUCATION embedded as `**EDUCATION**` in text |
| Q6 | `letter_tile` | tiles + question text |
| Q7 | `text_only` | plain |
| Q8 | `text_only` | KITCHEN embedded as `**KITCHEN**` in text |
| Q9 | `text_only` | plain |
| Q10–Q14 | `letter_plain` | word tiles (EXPERIMENTAL etc.), no text |
| Q15 | `letter_tile_no_nums` | tiles + text + subtext "The word formed belongs to:" |

---

## Geometric Shape Rendering System

### Shape Size Constant

```python
_SHAPE_SZ = fig(26)   # canonical shape size — used in matrix, shapes_row, and options
```

All diagram/option shapes use this single constant — no per-function scaling.

### Chapter-Dynamic Colors

Shapes use chapter brand colors instead of hardcoded neutrals:

```python
def _draw_geo_shape(cx, cy, size, shape, dark=False):
    fill   = _b.chapter_color(_b.CH_NUM)    if dark else _b.chapter_table_bg(_b.CH_NUM)
    stroke = _b.chapter_table_bor(_b.CH_NUM)
```

- `dark=True` → Info-500 fill (accent color, e.g. `#74ACFC` for Ch3)
- `dark=False` → Info-200 fill (light bg, e.g. `#DEECFF` for Ch3)
- Stroke always Info-700 (e.g. `#407BD6` for Ch3)
- In diagrams: shapes are always `dark=True`
- In options: shapes are always `dark=True`

### "?" Cell Font

In all diagram types (`_diagram_matrix_3x3`, `_diagram_rotate_seq`), the "?" uses `sec_head` font (14pt Medium):

```python
_b.draw.text((cx, cy), "?", font=_b.F["sec_head"], fill=(*CHARCOAL,255), anchor="mm")
```

### `_options_geo_rotations` — Bare Triangle (No Box)

Options for rotation-sequence diagrams show a bare triangle only (no square box), matching diagram triangle size:

```python
def _options_geo_rotations(y, rotations):
    r2      = int(fig(48) * 0.30)   # matches diagram triangle circumradius
    tri_dia = r2 * 2
    group_w = box_sz + lbl_gap + tri_dia
    # ...
    _b.draw.polygon(pts, fill=(*_b.chapter_color(_b.CH_NUM),255))
```

Options are centered in each column: `ox = LEFT + i * col_w + (col_w - group_w) // 2`

### `render_question()` — `diagram_geo` Branch

The `diagram_geo` branch must return early after rendering to prevent the common options block from double-rendering:

```python
elif qtype == "diagram_geo":
    diag = q.get("diagram", {})
    if diag:
        y = _render_diagram(y, diag)
        if diag.get("kind") == "shape_pattern_opts":
            return y
    if opts:
        if diag.get("visual_opts"):
            y = _options_geo_shapes(y, diag["visual_opts"])
            return y
        if diag.get("visual_opts_rotations"):
            y = _options_geo_rotations(y, diag["visual_opts_rotations"])
            return y
        y = options_auto(y, opts)
        return y   # ← critical: prevents double-render from common options block
```

---

## Hex Overlap Diagram (`draw_hex_q3.py`)

Standalone PIL script for Q3's 3+3 flat-top hexagon grid. Run directly:

```bash
python3 personal/agents/pdf-gen/scripts/draw_hex_q3.py
# Output: personal/workspace/illustrate/props/hex-overlap-q3.png
```

### Key Geometry

```python
r       = 115            # circumradius
LW      = 4              # stroke width — define BEFORE step calculations
h_half  = int(r * math.sqrt(3) / 2)
step_x  = r              # makes lower-right of hex N touch lower-left of hex N+1 (zero gap)
step_y  = h_half*2 - LW  # rows overlap by LW — closes residual junction gap
```

- Both rows left-aligned (same `x0`, no horizontal offset between rows)
- Draw fill + outline together, back-to-front — later hexes cover earlier ones cleanly

### Color Pattern

| Position | Shade |
|---|---|
| Top-row L | Info-200 `#DEECFF` |
| Top-row M | Info-400 `#9CC6FF` |
| Top-row R | Info-600 `#5492F1` |
| Bot-row L | Info-600 `#5492F1` |
| Bot-row M | Info-200 `#DEECFF` |
| Bot-row R | Info-400 `#9CC6FF` |
| Stroke | Info-800 `#3464B1` |

### Auto-Trim

```python
bbox = img.getbbox()
PAD  = 20
crop = (bbox[0]-PAD, bbox[1]-PAD, bbox[2]+PAD, bbox[3]+PAD)
img  = img.crop(crop)
```

### Content.json Reference (`max_width_figma`)

For Q3, set `max_width_figma: 120` — the cropped PNG (~501×433px) renders at the right size in the PDF column.

---

## Cumulative Assessment (CA) Pages

CA sections follow the same template rules as MCQ, but use `"type": "assessment"` in content.json.

### Question Type: `diagram_geo`

Used for geometric/visual reasoning questions. Fields:

```json
{
  "type": "diagram_geo",
  "text": "Question text here",
  "diagram": {
    "kind": "matrix_3x3",
    "cells": ["circle","square","triangle","square","triangle","circle","triangle","circle","?"],
    "visual_opts": ["circle","square","triangle","pentagon"]
  },
  "options": ["A","B","C","D"]
}
```

Supported diagram `kind` values:

| kind | What it draws |
|---|---|
| `matrix_3x3` | 3×3 grid — shapes + "?" cell |
| `rotate_seq` | Row of squares with rotating triangle inside, last is "?" |
| `shape_pattern_opts` | Row of 4 shapes (no separate options) |
| `shapes_row` | Horizontal row of shapes (used in question body) |

`visual_opts` → shape labels for ABCD (`_options_geo_shapes`)
`visual_opts_rotations` → rotation angles in degrees for ABCD (`_options_geo_rotations`)

If neither is present, falls back to `options_auto(y, opts)` (text options).

---

## Known System Constraints

- **cairosvg**: fails (`OSError: cairo native library not found` due to SIP). Do not use.
- **SVG → PNG**: use `rsvg-convert -z 4 --background-color none` (requires `brew install librsvg`).
- **F dict import**: always access via `_b.F["key"]` in `generate_g3_page.py` — never import `F` directly.
- **PDF caching in Preview**: macOS Preview caches PDFs. Always open with **Adobe Acrobat DC**.
- **Word breaks in source text**: strip hyphenated line breaks with `re.sub(r'-\n', '', text)` before rendering.

---

## Output Structure (Ch3)

```
personal/workspace/pdf-gen/ch3/
├── content.json
├── page-001.pdf     ← Temp1 (intro pg 1)
├── page-002.pdf     ← Temp3 (intro pg 2)
├── page-003.pdf     ← Temp2 (MCQ Q1–Q4)
├── page-004.pdf     ← Temp3 (MCQ Q5–Q9)
├── page-005.pdf     ← Temp4 (MCQ Q10–Q16)
├── page-006.pdf     ← Temp4 (MCQ Q17–Q20)
├── page-007.pdf     ← Temp2 (Assessment Q1–Q4)
├── page-008.pdf     ← Temp3 (Assessment Q5–Q9)
├── page-009.pdf     ← Temp4 (Assessment Q10–Q15)
├── page-010.pdf     ← Temp2 (CA first page — Q1–Q3)  ✓ DONE
├── page-011.pdf     ← Temp3 (CA pg 2)
├── ...
└── chapter-3.pdf   ← merged final
```

**Assets used by CA pages:**

```
personal/workspace/illustrate/props/
└── hex-overlap-q3.png   ← generated by draw_hex_q3.py (501×433px)
```

---

## Chapter Map (IMO LR G3)

| Key | Chapter | Source PDF pages |
|---|---|---|
| 3 | Alphabet Test | 27–42 |
| 4 | Number Coding | 43+ |

---

## Handling Feedback

- **Layout** (spacing, overflow) → adjust constants in `generate_g3_page.py`
- **Content** (wrong text, wrong type) → fix `content.json`
- **Style** (color, font, alignment) → `generate_g3_page.py` or `imo_g3_base.py`
- **Template** (wrong header) → fix `render_page()` in `generate_g3_page.py`

Always regenerate the same page after a fix. Do not move to next page until user confirms.
