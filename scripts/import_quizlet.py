#!/usr/bin/env python3
"""Convert a Quizlet text export (term <TAB> definition <NEWLINE>) into the JSON
deck format the dashboard expects.

Usage:
    python scripts/import_quizlet.py <input.txt> [--title "Deck title"] [--out path.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Quizlet export .txt (tab-separated term/def, one card per line)")
    ap.add_argument("--title", default=None, help="Deck title (default: input filename stem)")
    ap.add_argument("--source", default="quizlet", help="Source attribution")
    ap.add_argument("--out", default=None, help="Output path (default: same name with .json)")
    ap.add_argument("--term-sep", default="\t", help="Separator between term and definition (default: TAB)")
    ap.add_argument("--card-sep", default="\n", help="Separator between cards (default: newline)")
    args = ap.parse_args()

    src = pathlib.Path(args.input)
    if not src.exists():
        sys.exit(f"input not found: {src}")
    raw = src.read_text(encoding="utf-8")

    # Normalise line endings if --card-sep is newline
    if args.card_sep == "\n":
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    chunks = [c for c in raw.split(args.card_sep) if c.strip()]
    cards = []
    for line in chunks:
        if args.term_sep in line:
            t, d = line.split(args.term_sep, 1)
        else:
            # Tolerate two-space or pipe fallbacks if user used those
            for fb in ["  ", " | ", " — ", " - "]:
                if fb in line:
                    t, d = line.split(fb, 1); break
            else:
                continue
        cards.append({"term": t.strip(), "definition": d.strip()})

    title = args.title or src.stem
    out_path = pathlib.Path(args.out) if args.out else src.with_suffix(".json")
    deck = {"title": title, "source": args.source, "count": len(cards), "cards": cards}
    out_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path} ({len(cards)} cards)")


if __name__ == "__main__":
    main()
