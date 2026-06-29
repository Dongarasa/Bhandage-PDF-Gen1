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
| `generate_g3_page.py` | Page builder: reads content.json, calls base templates, renders intro/MCQ pages |
| `extract_content.py` | Extracts text from source PDF into content.json |

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

**Always ask the user before generating any NEW page.** After a fix on the current page, regenerate + open automatically without asking.

```bash
python3 personal/agents/pdf-gen/scripts/generate_g3_page.py \
  --content personal/workspace/pdf-gen/ch<N>/content.json \
  --page <page_index> \
  --output personal/workspace/pdf-gen/ch<N>/page-<NNN>.pdf
```

After generation, open immediately in Adobe Acrobat DC:
```bash
open -a "/Applications/Adobe Acrobat DC/Adobe Acrobat.app" personal/workspace/pdf-gen/ch<N>/page-<NNN>.pdf
```

**Auto-open rule**: After any fix, always regenerate + open the same page without asking. Only ask before moving to a NEW page.

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

Four templates from Figma file `EChVfa2DRvYK24AZbrSe9E`:

| Template | Figma Node | Header | When to use |
|---|---|---|---|
| **Temp1** | 232:4 | Full color bar (92px) + Chapter name + Grade pill (no logo) | Chapter intro **page 1** |
| **Temp2** | 232:12 | Full color bar (92px) + "Ch N: ChName" + section title (no logo) | MCQ/CA section **first page** |
| **Temp3** | 232:17 | L-shape bezier curve (top+left) + Logo top-right | Chapter intro **page 2** + MCQ **page 2** |
| **Temp4** | 232:21 | Thin 12px strip + Logo top-right | MCQ/CA **page 3 onwards** |

**Logo specs (Temp3 & Temp4):** `right: fig(24)`, `top: fig(32)`, `width: fig(80)` — transparent PNG from `personal/agents/pdf-gen/assets/cuemath-wordmark-tagline.png`.

**Temp3 L-shape bezier** (PIL polygon, no cairosvg):
```
M0 0 → L595 0 → L595 12 → L40 12
→ cubic(40,12)(29,12)(20,21)(20,32) → L20 72
→ cubic(20,72)(20,83)(11,92)(0,92) → Z
```
All coords scaled via `fig()`.

---

## Chapter Color System

Cycles mod 4 by chapter number. All values from Cuemath design-system tokens:

| Slot | Chapters | 500 (accent) | 100 (page bg) | 200 (table bg) | 700 (table border) |
|---|---|---|---|---|---|
| 0 | 1, 5, 9 | Gold `#F4AB52` | `#FAF1E6` | `#FAE6D0` | `#CE7E12` |
| 1 | 2, 6, 10 | Error `#F97279` | `#FFE9E9` | `#FFD6D5` | `#C8444F` |
| 2 | 3, 7, 11 | Info `#74ACFC` | `#EEF6FF` | `#DEECFF` | `#407BD6` |
| 3 | 4, 8, 12 | Success `#6AC88A` | `#ECF9EF` | `#DAF3E0` | `#28995A` |

**Badge bg** uses 300-shade: Gold `#FAD6AC`, Error `#FFB8B7`, Info `#C1DCFF`, Success `#BCEAC8`.

Helpers in `imo_g3_base.py`:
- `chapter_color(ch)` → 500 accent (border/outline)
- `chapter_badge_bg(ch)` → 300-shade light fill (badge background)
- `chapter_table_bg(ch)` → 200-shade (filled rows in letter tiles)
- `chapter_table_bor(ch)` → 700-shade (tile borders)

---

## Fonts

Stored in `~/Library/Fonts/`:

| Key | Font file | Size | Used for |
|---|---|---|---|
| `ch_num` | Athletics-Regular.otf | 14pt | Chapter number |
| `ch_title` | Athletics-Light.otf | 24pt | Chapter title |
| `ch_big` | Athletics-Black.otf | 32pt | Large decorative chapter number |
| `grade` | Athletics-Regular.otf | 12pt | Grade pill |
| `sec_head` | UntitledSans-Medium.otf | 14pt | Section headings |
| `medium` | UntitledSans-Medium.otf | 12pt | "Directions (N-N):" prefix label |
| `body` | UntitledSans-Regular.otf | 12pt | Body text, tiles text |
| `direction` | UntitledSans-Regular.otf | 12pt | Direction continuation text (NOT Light — Regular) |
| `q_badge` | UntitledSans-Medium.otf | 12pt | Question number in badge |
| `q_text` | UntitledSans-Regular.otf | 12pt | Question main text |
| `opt_label` | UntitledSans-Medium.otf | 10pt | ABCD label inside checkbox |
| `opt_text` | UntitledSans-Regular.otf | 12pt | Option answer text |
| `footer` | UntitledSans-Regular.otf | 10pt | Footer text |

---

## Intro Page Layout

Indentation levels (Figma 72-DPI px → `fig()`):

| Level | px | Used for |
|---|---|---|
| `INTRO_L0 = fig(40)` | 40px | Section headings, "Type X:" label, bullets |
| `INTRO_L1 = fig(87)` | 87px | Type description text, Answer label |
| `_ex_body_x` | dynamic | Body/Solution text when inside Example block |

- **Example label + text body**: both at `INTRO_L1`; `_ex_body_x = INTRO_L1 + label_width + fig(6)`
- **Letter/Number table**: starts at `_ex_body_x`
- **ABCD options**: starts at `_ex_body_x`
- **Body text after an Example block** (`_ex_active = True`): drawn at `_ex_body_x`
- **Solution**: label + first line via `_inline_label_text` at `_ex_body_x`; continuation lines at `_ex_body_x`
- **Answer**: always at `INTRO_L1` (not affected by `_ex_active`)
- **`_ex_active` flag**: set `True` after Example renders; reset `False` on new Type block

**`_ex_active` break condition in body text loop** — break when next line is:
- Empty string
- Matches `_STRUCT_RE` (Type/Section/Example/etc.)
- Matches `re.match(r'^[A-Z]{2,10}', nxt)` — standalone UPPERCASE sequences (e.g. "ACEG")

**Paragraph spacing**: `PARA_GAP = fig(8)` added after every block.

Typography:
- Section headings: UntitledSans Medium 14pt UPPERCASE
- "Type I: Title": UntitledSans Medium 12pt at `INTRO_L0`
- Description text: UntitledSans Regular 12pt at `INTRO_L1`
- Example/Answer/Solution labels: UntitledSans Medium 12pt

---

## MCQ Page Layout

### Layout Constants

```python
LEFT        = fig(40)
RIGHT_EDGE  = fig(555)
Q_BADGE_W   = fig(36)
Q_TEXT_X    = LEFT + Q_BADGE_W + fig(8)
Q_CONTENT_W = RIGHT_EDGE - Q_TEXT_X
```

### Pagination

```python
Q_FIRST_PAGE  = 4   # questions on MCQ page 1 (Temp2)
Q_SECOND_PAGE = 5   # questions on MCQ page 2 (Temp3)
Q_PER_PAGE    = 7   # questions on MCQ page 3+ (Temp4)
```

Page assignment logic:
```python
chunks, pos, page_idx = [], 0, 0
while pos < max(len(questions), 1):
    if page_idx == 0:   size = Q_FIRST_PAGE
    elif page_idx == 1: size = Q_SECOND_PAGE
    else:               size = Q_PER_PAGE
    chunks.append((pos, questions[pos: pos + size]))
    pos += size
    page_idx += 1
```

### Directions Block

`directions_block(y, prefix, rest)` in `imo_g3_base.py`:

- `prefix` (e.g. `"Directions (1-5):"`) → `F["medium"]` (UntitledSans Medium), CHARCOAL color
- `rest` (continuation text) → `F["direction"]` (UntitledSans Regular), TEXT_DARK color
- First line of `rest` fits beside prefix on the same line; remaining words word-wrap from LEFT
- Word-wrap uses `draw.textlength()` to fill each line properly

### Question Badge

```python
badge_h = _line_h(F["q_text"]) + fig(6)
bg  = chapter_badge_bg(CH_NUM)   # 300-shade light fill
bor = chapter_color(CH_NUM)       # 500 accent border
draw.rounded_rectangle(
    [LEFT, y, LEFT + Q_BADGE_W, y + badge_h],
    radius=px(4), fill=(*bg, 255), outline=(*bor, 255), width=max(1, px(0.5)))
draw.text((LEFT + Q_BADGE_W // 2, y + badge_h // 2),
          f"{num:02d}.", font=F["q_badge"], fill=(*CHARCOAL, 255), anchor="mm")
```

### Question Types

| Type | Tiles display | Number row | Used in Ch3 |
|---|---|---|---|
| `letter_tile` | Individual boxes at Q_TEXT_X, same y as badge | Yes (filled bg row below) | Q1–Q5 |
| `letter_tile_no_nums` | Individual boxes at Q_TEXT_X | No | (reserved) |
| `letter_plain` | Plain spaced text `"  ".join(tiles)` at Q_TEXT_X, same y as badge | No | Q6–Q16 |
| `letter_plain_subtext` | Plain tiles on badge line, then subtext below, then options | No | Q17–Q20 |

**`render_letter_tiles(y, tiles, x=None, show_nums=True)`:**
```python
cell_w  = fig(32)
cell_h  = fig(28)
tx      = x if x is not None else LEFT
hdr_bg  = chapter_table_bg(CH_NUM)
bor_col = chapter_table_bor(CH_NUM)
rows = [(tiles, False)]
if show_nums:
    rows.append(([str(i+1) for i in range(len(tiles))], True))
# Row 0: letter tiles (white fill)
# Row 1 if show_nums: number row (filled chapter bg)
rows_drawn = 2 if show_nums else 1
return y + rows_drawn * cell_h + fig(8)
```

**`letter_plain` rendering:**
```python
text_str = "  ".join(q["tiles"])
badge_h  = _lh("body") + fig(6)
cy       = y + badge_h // 2
draw.text((Q_TEXT_X, cy), text_str, font=F["body"], fill=(*TEXT_DARK, 255), anchor="lm")
y += badge_h + fig(4)
```
Note: badge is drawn without advancing y — tiles/text start at the same y as the badge top.

**`letter_plain_subtext` rendering:**
- Same as `letter_plain` for the tiles line
- Then `subtext` drawn below via `draw_wrapped` at `Q_TEXT_X`
- Then options follow

**Badge-only render (no tiles, no text):**
```python
badge_h = _line_h(F["q_text"]) + fig(6)
# draw badge only — do NOT advance y; tiles start at same y as badge
```

### ABCD Options

**Checkbox style** (`_draw_single_opt`):
```python
_OPT_BOX     = fig(20)
_OPT_NEUTRAL = (151, 147, 140)   # neutral-500 #97938C
# Rounded rectangle: white fill, neutral border
# Label (A/B/C/D) centered inside box in _OPT_NEUTRAL
# Option text to the right in TEXT_DARK
```

**2-column layout** (`options_2col`):
```python
col_w  = Q_CONTENT_W // 2
row_h  = _OPT_BOX + fig(4)   # 4px gap between rows
```

**4-column layout** (`_options_row`):
```python
col_w  = Q_CONTENT_W // 4
row_h  = _OPT_BOX + fig(10)
```

### Separator Between Questions

```python
y = separator(y, gap_before=fig(12), gap_after=fig(24))
# Line: fill=(*CHARCOAL, 80), width=max(1, px(0.75))
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
      { "type": "mcq", "questions": [...] }
    ]
  }]
}
```

Intro text split at "Type III:" boundary:
- Part 1 (Type I + II) → intro page 1 → **Temp1**
- Part 2 (Type III + IV) → intro page 2 → **Temp3**

### Ch3 Question Type Map

| Q# | type | tiles | text | subtext |
|---|---|---|---|---|
| Q1–Q5 | `letter_tile` | letters | question text | — |
| Q6–Q7 | `letter_plain` | letters | `""` | — |
| Q8–Q9 | `letter_plain` | letters | `""` | — |
| Q10–Q14 | `letter_plain` | letters | `""` | — |
| Q15–Q16 | `letter_plain` | letters | question text | — |
| Q17–Q20 | `letter_plain_subtext` | letters | `""` | `"The word formed belongs to:"` |

---

## Known System Constraints

- **cairosvg**: fails (`OSError: cairo native library not found` due to SIP). Do not use.
- **SVG → PNG**: use `rsvg-convert -z 4 --background-color none` (requires `brew install librsvg`).
- **F dict import**: always access fonts via `_b.F["key"]` in `generate_g3_page.py` — never import `F` directly (empty before `setup()` runs).
- **PDF caching in Preview**: macOS Preview caches PDFs. Always open with **Adobe Acrobat DC** to see updates.

---

## Output Structure

```
personal/workspace/pdf-gen/
└── ch<N>/
    ├── content.json
    ├── page-001.pdf     ← Temp1 (intro pg 1)
    ├── page-002.pdf     ← Temp3 (intro pg 2)
    ├── page-003.pdf     ← Temp2 (MCQ first page, Q1–Q4)
    ├── page-004.pdf     ← Temp3 (MCQ page 2, Q5–Q9)
    ├── page-005.pdf     ← Temp4 (MCQ page 3, Q10–Q16)
    ├── page-006.pdf     ← Temp4 (MCQ page 4, Q17–Q20)
    └── chapter-<N>.pdf  ← merged final
```

---

## Chapter Map (IMO LR G3)

| Key | Chapter | Source pages (printed) |
|---|---|---|
| 3 | Alphabet Test | 27–42 |

---

## Handling Feedback

- **Layout** (spacing, overflow) → adjust constants/spacing in `generate_g3_page.py`
- **Content** (wrong text) → fix `content.json` or extraction script
- **Style** (color, font, alignment) → update draw functions in `generate_g3_page.py` or `imo_g3_base.py`
- **Template** (wrong header) → fix `render_page()` logic in `generate_g3_page.py`

Always regenerate the **same page** after a fix. Do not move to next page until user confirms.
