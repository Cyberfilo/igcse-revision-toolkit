#!/usr/bin/env python3
"""Read notes/_diagrams/manifest.json and append `<figure>` blocks to each
target HTML note, idempotently (a re-run replaces the existing block, doesn't
duplicate it).

Run after generate_diagrams.py:
    python scripts/embed_diagrams.py
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import defaultdict

ROOT = pathlib.Path(".")
NOTES = ROOT / "notes"
MANIFEST = NOTES / "_diagrams" / "manifest.json"

START_MARK = "<!-- diagrams:start -->"
END_MARK   = "<!-- diagrams:end -->"
BLOCK_RE = re.compile(
    re.escape(START_MARK) + r".*?" + re.escape(END_MARK) + r"\s*",
    re.S,
)


def main():
    if not MANIFEST.exists():
        raise SystemExit(f"missing manifest: {MANIFEST}")
    diagrams = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # group by target html
    by_target: dict[str, list[dict]] = defaultdict(list)
    for d in diagrams:
        by_target[d["target_html"]].append(d)

    for target, items in by_target.items():
        target_path = NOTES / target
        if not target_path.exists():
            print(f"  ! target missing, skipped: {target}")
            continue
        # group by section so multiple diagrams under one section sit together
        by_section: dict[str, list[dict]] = defaultdict(list)
        for it in items:
            by_section[it["section"]].append(it)

        block = [START_MARK]
        for section, group in by_section.items():
            block.append(f'<div class="section-h">{section}</div>')
            block.append('<div class="diagram-grid">')
            for d in group:
                # figure out path relative to the html file
                # html lives at notes/<subject>/<file>.html
                # diagrams live at notes/_diagrams/<key>.png
                # → relative path: ../_diagrams/<key>.png
                img_rel = "../_diagrams/" + pathlib.Path(d["image"]).name
                block.append(
                    '<figure class="diagram">'
                    f'<img src="{img_rel}" alt="{d["caption"]}" loading="lazy" />'
                    f'<figcaption>{d["caption"]}</figcaption>'
                    '</figure>'
                )
            block.append('</div>')
        block.append(END_MARK)
        block_html = "\n".join(block) + "\n"

        text = target_path.read_text(encoding="utf-8")
        if BLOCK_RE.search(text):
            text = BLOCK_RE.sub(block_html, text)
        else:
            text = text.rstrip() + "\n\n" + block_html
        target_path.write_text(text, encoding="utf-8")
        print(f"  ✓ {target} ({sum(len(g) for g in by_section.values())} diagrams)")


if __name__ == "__main__":
    main()
