#!/usr/bin/env python3
"""Extract text from every PDF in resources/ and syllabus/ into a .txt sidecar
under resources/_extracted/<original-path>.txt — searchable by the dashboard.

Run:
    python scripts/extract_pdf_text.py
"""
from __future__ import annotations

import pathlib
import sys

from pypdf import PdfReader

ROOT = pathlib.Path(".")
SOURCES = [ROOT / "resources", ROOT / "syllabus"]
OUT_BASE = ROOT / "resources" / "_extracted"


def extract_one(pdf_path: pathlib.Path) -> tuple[pathlib.Path, int, int]:
    rel = pdf_path.relative_to(ROOT)
    out = OUT_BASE / rel.with_suffix(".txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_mtime > pdf_path.stat().st_mtime:
        return out, 0, 0  # cached

    try:
        r = PdfReader(str(pdf_path))
    except Exception as e:
        sys.stderr.write(f"  !! {pdf_path}: {e}\n")
        return out, 0, 0

    pages = []
    for i, page in enumerate(r.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        pages.append(f"--- page {i+1} ---\n{t}")

    out.write_text("\n".join(pages), encoding="utf-8")
    return out, len(r.pages), sum(len(p) for p in pages)


def main():
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    total = 0; total_chars = 0
    for src in SOURCES:
        if not src.exists():
            continue
        for pdf in sorted(src.rglob("*.pdf")):
            out, n_pages, n_chars = extract_one(pdf)
            print(f"  {pdf.name:60s}  {n_pages:3d} pages  {n_chars:>9} chars  → {out.name}")
            total += n_pages; total_chars += n_chars
    print(f"\ntotal: {total} pages, {total_chars/1000:.1f}K chars extracted")


if __name__ == "__main__":
    main()
