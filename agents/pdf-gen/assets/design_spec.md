# Updated Layout — Design Specification

## Page

| Property | Value |
|---|---|
| Format | A4 portrait |
| Width | 595.28 pts |
| Height | 841.89 pts |
| Left margin | 40 pts |
| Right margin | 40 pts |
| Top margin (content pages) | 72 pts |
| Bottom margin | 48 pts |
| Content width | 515.28 pts |

> Note: The reference "Updated Layout.pdf" is A3 landscape (two-page spread).
> We generate individual A4 pages — same visual result when printed/spread.

---

## Colors

| Name | Hex | Usage |
|---|---|---|
| `color-bg` | `#FFF4F4` | Page background |
| `color-header` | `#F08080` | Chapter intro banner |
| `color-accent` | `#E85555` | Top accent stripe (4pt tall) |
| `color-badge-q` | `#E87878` | Question number badge |
| `color-badge-opt-border` | `#E8B0B0` | Option badge border (A/B/C/D) |
| `color-divider` | `#F0C0C0` | Horizontal rule between questions |
| `color-tile-bg` | `#F0F0F0` | Letter tile background |
| `color-tile-border` | `#CCCCCC` | Letter tile border |
| `color-text-body` | `#1A1A1A` | Main body text |
| `color-text-secondary` | `#555555` | Labels, directions text |
| `color-footer` | `#888888` | Footer text |
| `color-white` | `#FFFFFF` | Option badge background |

---

## Typography

| Role | Font | Size | Weight | Color |
|---|---|---|---|---|
| Chapter title (banner) | Helvetica-Bold | 24pt | Bold | White |
| Chapter subtitle | Helvetica | 11pt | Regular | White |
| Grade badge | Helvetica-Bold | 18pt | Bold | `#E85555` |
| Section heading | Helvetica-Bold | 10pt | Bold | `#1A1A1A` |
| Directions text | Helvetica | 9pt | Regular | `#1A1A1A` |
| Question text | Helvetica | 9.5pt | Regular | `#1A1A1A` |
| Question bold intro | Helvetica-Bold | 9.5pt | Bold | `#1A1A1A` |
| Option text | Helvetica | 9pt | Regular | `#1A1A1A` |
| Answer label | Helvetica-Bold | 9pt | Bold | `#1A1A1A` |
| Letter tile | Helvetica-Bold | 9pt | Bold | `#1A1A1A` |
| Footer | Helvetica | 7.5pt | Regular | `#888888` |
| Cuemath logo text | Helvetica-Bold | 9pt | Bold | `#1A1A1A` |
| Logo tagline | Helvetica | 6.5pt | Regular | `#555555` |

---

## Components

### Chapter Header Banner (Intro page — left side)

```
┌─────────────────────────────────────────┐  ← full page width
│ [4pt accent stripe — color-accent]      │
├──────────────────────────────┬──────────┤
│ Chapter N (11pt, white)      │          │
│ Chapter Title (24pt, white)  │  Grade   │  ← 80pt tall
│                              │   (O)    │
└──────────────────────────────┴──────────┘
```
- Banner height: 80 pts
- Grade badge: 44pt circle, white bg, `color-accent` text
- Badge position: right side, vertically centered in banner

### Content Page Header (all non-intro pages)

```
┌──────────────────────────────────────────┐
│ [2pt accent stripe]                      │
├──────────────────────────────────────────┤
│ [Chapter N: Chapter Name]  CUEMATH logo  │  ← 28pt tall
│                            Making Kids.. │
├──────────────────────────────────────────┤
```
- Left: "Chapter N: Chapter Name" in Helvetica 8pt, `#555555`
- Right: CUEMATH bold 9pt + "Making Kids MathFit®" 6.5pt

### Question Block

```
┌──┐
│01│  Question text here...
└──┘
   A option text    B option text
   C option text    D option text
─────────────────────────────────  ← divider
```
- Badge: 18×18pt rounded rect (radius 3), `color-badge-q` bg, white text 8pt bold
- Options: 2 columns, equal width (content_width / 2)
- Option badge: 14×14pt rounded rect, white bg, `color-badge-opt-border` border 0.5pt
- Option letter: 8pt bold, `#E87878`
- Divider: 0.5pt `color-divider`, full content width
- Space before next question: 10pt

### Letter Tile

```
┌─┐ ┌─┐ ┌─┐ ┌─┐ ┌─┐
│G│ │T│ │O│ │U│ │H│
└─┘ └─┘ └─┘ └─┘ └─┘
 1   2   3   4   5
```
- Each tile: 20×20pt, rounded rect radius 3
- Tile bg: `color-tile-bg`, border: `color-tile-border` 0.5pt
- Letter: Helvetica-Bold 10pt centered
- Number below: Helvetica 7pt centered, `#555555`
- Gap between tiles: 4pt

### Answer/Solution block

```
Answer:  (B) BEST
```
- "Answer:" bold 9pt, answer text regular 9pt

### Footer

```
© Cue Learn Pvt. Ltd.              27              Grade 3: Logical Reasoning
```
- Left: copyright text 7.5pt `color-footer`
- Center: page number 7.5pt `color-footer`
- Right: section name 7.5pt `color-footer`

---

## Page Layout Rules

1. **Intro page** (first page of each chapter):
   - Full-width banner at top (accent stripe + header)
   - Body: Introduction text, then Types/Examples
   - No Cuemath logo header (banner IS the header)

2. **Content pages** (MCQ, Assessment):
   - Cuemath logo header (28pt)
   - Questions flow top to bottom
   - Auto page-break when content overflows
   - Always show chapter context in header

3. **Two-column option layout**:
   - Columns: each `(content_width - 8) / 2` wide
   - Left col: options A, C
   - Right col: options B, D
   - Single-row options (only A/B): side by side

4. **Image placement**:
   - Images go below question text, above options
   - Max image width: `content_width - 20` pts
   - Max image height: 120 pts (scale proportionally)
