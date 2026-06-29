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
| `imo_g3_base.py` | Shared base: canvas setup, fonts, colors, template headers, logo, footer |
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

**Always ask the user before generating any page.** Do not generate automatically.

```bash
python3 personal/agents/pdf-gen/scripts/generate_g3_page.py \
  --content personal/workspace/pdf-gen/ch<N>/content.json \
  --page <page_index> \
  --output personal/workspace/pdf-gen/ch<N>/page-<NNN>.pdf
```

The script prints total page count to stdout. Use it to know how many pages exist.

After generation, open the PDF:
```bash
open personal/workspace/pdf-gen/ch<N>/page-<NNN>.pdf
```

Then ask: **"Theek hai? Ya kuch fix karna hai?"** — wait for approval before next page.

---

### Step 3 — Merge into final PDF

After all pages are approved:

```bash
python3 -c "
import img2pdf, glob, os
pages = sorted(glob.glob('personal/workspace/pdf-gen/ch<N>/page-*.pdf'))
# merge individual PDFs via pypdf
from pypdf import PdfWriter
w = PdfWriter()
for p in pages:
    from pypdf import PdfReader
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

Badge bg uses 300-shade: Gold `#FAD6AC`, Error `#FFB8B7`, Info `#C1DCFF`, Success `#BCEAC8`.

---

## Intro Page Layout (Figma node 232:4)

Indentation levels (in Figma 72-DPI px, converted via `fig()`):

| Level | px | Used for |
|---|---|---|
| `INTRO_L0 = fig(40)` | 40px | Section headings, "Type X:" label, bullets |
| `INTRO_L1 = fig(87)` | 87px | Type description text ("Use the given numbers…") |
| `INTRO_L2 = fig(154)` | 154px | (reserved; not currently used as a hard indent) |

- **Example label + text body**: both at `INTRO_L1`, text body x computed dynamically as `_ex_body_x = INTRO_L1 + label_width + fig(6)`
- **Letter/Number table**: starts at `_ex_body_x`
- **ABCD options**: starts at `_ex_body_x`
- **Standalone letter sequence (e.g. "ACEG")**: single filled box drawn at `_ex_body_x`
- **Body text after an Example block** (`_ex_active = True`): drawn at `_ex_body_x` (not `INTRO_L0`)
- **Solution**: label + first line at `_ex_body_x` when inside Example block; continuation lines each on new line at `_ex_body_x`
- **Answer**: always at `INTRO_L1` (not affected by `_ex_active`)
- **`_ex_active` flag**: set `True` after Example block renders; reset `False` on new Type block

**Paragraph spacing**: `PARA_GAP = fig(8)` added after every block (Type title, Type description, Example, Answer, Solution, default body text).

Typography:
- Section headings: UntitledSans Medium 14pt UPPERCASE
- "Type I: Title": full line in UntitledSans Medium 12pt at `INTRO_L0`
- Description text: UntitledSans Regular 12pt at `INTRO_L1`
- Body / bullets: UntitledSans Regular 12pt
- Example/Answer/Solution labels: UntitledSans Medium 12pt

---

## Fonts

Stored in `~/Library/Fonts/`:

| Key | Font file | Size |
|---|---|---|
| `ch_num` | Athletics-Regular.otf | 14pt |
| `ch_title` | Athletics-Light.otf | 24pt |
| `ch_big` | Athletics-Black.otf | 32pt |
| `grade` | Athletics-Regular.otf | 12pt |
| `sec_head` | UntitledSans-Medium.otf | 14pt |
| `medium` | UntitledSans-Medium.otf | 12pt |
| `body` | UntitledSans-Regular.otf | 12pt |
| `direction` | UntitledSans-Light.otf | 12pt |
| `footer` | UntitledSans-Regular.otf | 10pt |

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

Intro text is split at "Type III:" boundary:
- Part 1 (Type I + II) → intro page 1 → **Temp1**
- Part 2 (Type III + IV) → intro page 2 → **Temp3**

---

## Known System Constraints

- **cairosvg**: fails on this system (`OSError: cairo native library not found` due to SIP). Do not use.
- **SVG → PNG**: use `rsvg-convert -z 4 --background-color none` (requires `brew install librsvg`).
- **F dict import**: always access fonts via `_b.F["key"]` in `generate_g3_page.py` — never import `F` directly (it's empty before `setup()` runs).

---

## Output Structure

```
personal/workspace/pdf-gen/
└── ch<N>/
    ├── content.json
    ├── page-001.pdf     ← Temp1 (intro pg 1)
    ├── page-002.pdf     ← Temp3 (intro pg 2)
    ├── page-003.pdf     ← Temp2 (MCQ first page)
    ├── page-004.pdf     ← Temp3 (MCQ page 2)
    ├── page-005.pdf     ← Temp4 (MCQ page 3+)
    └── chapter-<N>.pdf  ← merged final
```

---

## Chapter Map (IMO LR G3)

| Key | Chapter | Source pages (printed) |
|---|---|---|
| 3 | Alphabet Test | 27–42 |

(Add other chapters as they are processed.)

---

## Handling Feedback

- **Layout** (spacing, overflow) → adjust constants/spacing in `generate_g3_page.py`
- **Content** (wrong text) → fix `content.json` or extraction script
- **Style** (color, font, alignment) → update draw functions in `generate_g3_page.py` or `imo_g3_base.py`
- **Template** (wrong header) → fix `render_page()` logic in `generate_g3_page.py`

Always regenerate the **same page** after a fix. Do not move to next page until user confirms.
