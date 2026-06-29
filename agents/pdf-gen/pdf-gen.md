---
name: pdf-gen
type: personal-agent
agent: pdf-gen
command: /my pdf-gen
date: 2026-06-24
description: "Converts Cuemath IMO source book PDF into Updated Layout format. Page-by-page generation with review, then merges into final PDF."
---

# PDF Generator — Cuemath IMO Book

Converts source IMO book content into the Cuemath Updated Layout design — pink/salmon theme, chapter banners, letter tiles, MCQ styling.

## What I do

1. Ask for source PDF path + chapter number
2. Extract all pages for that chapter
3. Generate one page at a time — show preview path after each
4. Wait for your approval before moving to next page
5. Merge all approved pages into a single final PDF

## Full spec
`personal/agents/pdf-gen/SKILL.md`

## Scripts
`personal/agents/pdf-gen/scripts/`
- `extract_content.py` — extract structured content from source PDF
- `generate_page.py` — generate a single page PDF
- `merge_pages.py` — merge all pages into final PDF
