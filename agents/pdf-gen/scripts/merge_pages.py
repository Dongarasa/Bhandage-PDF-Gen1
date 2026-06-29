"""
merge_pages.py — Merge individual page PDFs into one final PDF.

Usage:
  python3 merge_pages.py \
    --input-dir <path/to/pages/> \
    --output    <path/to/final.pdf>

Merges all page-*.pdf files in input-dir, sorted by filename.
"""

import argparse
import glob
import os
import sys
from pypdf import PdfWriter, PdfReader


def merge(input_dir, output_path):
    pattern = os.path.join(input_dir, "page-*.pdf")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"Error: no page-*.pdf files found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    writer = PdfWriter()
    for f in files:
        reader = PdfReader(f)
        for page in reader.pages:
            writer.add_page(page)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as out:
        writer.write(out)

    print(f"Merged {len(files)} pages → {output_path}", file=sys.stderr)
    print(len(files))  # stdout for agent to read


def main():
    parser = argparse.ArgumentParser(description="Merge page PDFs into final PDF")
    parser.add_argument("--input-dir", required=True, help="Directory with page-*.pdf files")
    parser.add_argument("--output", required=True, help="Output PDF path")
    args = parser.parse_args()

    merge(args.input_dir, args.output)


if __name__ == "__main__":
    main()
