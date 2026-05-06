#!/usr/bin/env python3
"""Local dashboard server for IGCSE 0654 revision project.

Run:
    source .venv/bin/activate
    python dashboard/server.py

Then open http://localhost:8765
"""
from __future__ import annotations

import json
import mimetypes
import os
import pathlib
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import markdown
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard"
STATIC = DASHBOARD / "static"
TOPICS_YAML = ROOT / "syllabus" / "topics.yaml"
NOTES_DIR = ROOT / "notes"
RESOURCES_DIR = ROOT / "resources"
FLASHCARDS_DIR = ROOT / "flashcards"
PAPERS_DIR = ROOT / "papers"
SYLLABUS_DIR = ROOT / "syllabus"
REVIEW_SHEETS_DIR = ROOT / "notes" / "_review-sheets"

PORT = int(os.environ.get("RIPASSO_PORT", 8765))

# -------- Helpers --------

def load_topics() -> dict:
    with open(TOPICS_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


_FM_RE_MD   = re.compile(r"^---\n(.*?)\n---\n?", re.S)
_FM_RE_HTML = re.compile(r"^<!--meta\s*\n(.*?)\n-->\s*\n?", re.S)
NOTE_EXTS = (".md", ".html")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_RE_MD.match(text) or _FM_RE_HTML.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception:
        fm = {}
    return fm, text[m.end():]


def _content_length(body: str) -> int:
    """Visible content length: strip HTML tags, comments, collapse whitespace."""
    text = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return len(text.strip())


def list_notes() -> list[dict]:
    if not NOTES_DIR.exists():
        return []
    out = []
    for path in NOTES_DIR.rglob("*"):
        if path.suffix.lower() not in NOTE_EXTS or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        fm, body = parse_frontmatter(text)
        out.append({
            "path": str(path.relative_to(ROOT)),
            "name": path.name,
            "ext": path.suffix.lower().lstrip("."),
            "frontmatter": fm,
            "body_chars": _content_length(body),
        })
    return out


def _content_under_subtopic(body: str, code: str) -> int:
    """How many non-trivial chars sit under a `## <code>` heading (md) or `<h2>...<code>...</h2>` (html)."""
    # Markdown variant
    md_pat = re.compile(rf"(?m)^##\s+{re.escape(code)}\b.*?\n(.*?)(?=^##\s+|^#\s+|\Z)", re.S)
    m = md_pat.search(body)
    if m:
        return _content_length(m.group(1))
    # HTML variant: <h2 ...>... CODE ...</h2> (content) (until next <h2> or end)
    html_pat = re.compile(
        rf"<h[12][^>]*>[^<]*\b{re.escape(code)}\b[^<]*</h[12]>(.*?)(?=<h[12][^>]*>|\Z)", re.S | re.I
    )
    m = html_pat.search(body)
    if m:
        return _content_length(m.group(1))
    return 0


def compute_coverage() -> dict:
    topics = load_topics()
    notes = list_notes()
    # code -> list of note paths
    coverage: dict[str, list[str]] = {}

    def _add(code: str, p: str):
        bucket = coverage.setdefault(code, [])
        if p not in bucket:
            bucket.append(p)

    for n in notes:
        path = ROOT / n["path"]
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        clean_len = _content_length(body)
        declared = fm.get("subtopics") or []

        # 1. Per-subtopic check: ## <code> heading with ≥30 chars beneath
        for sub_code in declared:
            if _content_under_subtopic(body, sub_code) >= 30:
                _add(sub_code, n["path"])

        # 2. Whole-file fallback: if body is substantial (≥400 chars), trust the
        #    frontmatter — mark all declared subtopics covered, or fan out from
        #    the topic code if no subtopics are declared.
        if clean_len >= 400:
            if declared:
                for sub_code in declared:
                    _add(sub_code, n["path"])
            else:
                top_code = fm.get("code")
                if top_code:
                    for sub_list in topics.values():
                        for t in sub_list:
                            if t["code"] == top_code:
                                for s in (t["subtopics"] or [{"code": t["code"]}]):
                                    _add(s["code"], n["path"])

    out = {}
    for subject, items in topics.items():
        items_out = []
        for t in items:
            subs = t["subtopics"] or [{"code": t["code"], "title": t["title"]}]
            sub_out = []
            for s in subs:
                sub_out.append({
                    "code": s["code"],
                    "title": s["title"],
                    "covered": s["code"] in coverage,
                    "note_paths": coverage.get(s["code"], []),
                })
            covered = sum(1 for s in sub_out if s["covered"])
            items_out.append({
                "code": t["code"],
                "title": t["title"],
                "subtopics": sub_out,
                "covered": covered,
                "total": len(sub_out),
            })
        # macro stats
        macro_covered = sum(t["covered"] for t in items_out)
        macro_total = sum(t["total"] for t in items_out)
        out[subject] = {
            "topics": items_out,
            "covered": macro_covered,
            "total": macro_total,
        }
    return out


_RESOURCE_EXT_LABEL = {
    "pdf": "PDF", "pptx": "Slides", "ppt": "Slides",
    "jpg": "Image", "jpeg": "Image", "png": "Image", "gif": "Image",
    "docx": "Word", "doc": "Word",
    "md": "Markdown",
    "yaml": "YAML", "json": "JSON",
}


def list_resources() -> dict:
    out: dict[str, list[dict]] = {
        "biology": [], "chemistry": [], "physics": [],
        "syllabus": [], "papers": [], "general": [],
    }
    bases = [
        (RESOURCES_DIR, None),
        (SYLLABUS_DIR, "syllabus"),
        (PAPERS_DIR, "papers"),
    ]
    for base, force_bucket in bases:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue
            rel = path.relative_to(ROOT)
            ext = path.suffix.lstrip(".").lower()
            entry = {
                "path": str(rel),
                "name": path.name,
                "size": path.stat().st_size,
                "ext": ext,
                "type_label": _RESOURCE_EXT_LABEL.get(ext, ext.upper() or "File"),
                "subdir": str(rel.parent),
            }
            if force_bucket:
                out[force_bucket].append(entry)
            elif len(rel.parts) >= 2 and rel.parts[1] in ("biology", "chemistry", "physics"):
                out[rel.parts[1]].append(entry)
            else:
                out["general"].append(entry)
    return out


def list_flashcards() -> list[dict]:
    if not FLASHCARDS_DIR.exists():
        return []
    out = []
    for path in sorted(FLASHCARDS_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            out.append({"path": str(path.relative_to(ROOT)), "name": path.stem, "error": str(e), "cards": []})
            continue
        cards = data if isinstance(data, list) else data.get("cards", [])
        meta = {} if isinstance(data, list) else {k: v for k, v in data.items() if k != "cards"}
        out.append({
            "path": str(path.relative_to(ROOT)),
            "name": meta.get("title") or path.stem,
            "meta": meta,
            "cards": cards,
            "count": len(cards),
        })
    return out


def list_review_sheets() -> dict:
    """Read the manifest.json each subject's review-sheets folder produces."""
    out: dict[str, dict] = {}
    if not REVIEW_SHEETS_DIR.exists():
        return out
    for sub_dir in sorted(REVIEW_SHEETS_DIR.iterdir()):
        if not sub_dir.is_dir():
            continue
        manifest_path = sub_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        slides = []
        for s in data.get("slides", []):
            slides.append({
                "index": s["index"],
                "title": s.get("title"),
                "pictures": s.get("pictures", 0),
                "url": f"/asset/notes/_review-sheets/{sub_dir.name}/{s['image']}",
            })
        out[sub_dir.name] = {
            "subject": sub_dir.name,
            "slide_count": data.get("slide_count", len(slides)),
            "width": data.get("slide_width"),
            "height": data.get("slide_height"),
            "slides": slides,
        }
    return out


def render_md(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "sane_lists", "toc", "md_in_html"],
        output_format="html5",
    )


# -------- HTTP --------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def _json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: pathlib.Path, *, inline: bool = True):
        if not path.is_file():
            self.send_error(404)
            return
        ctype, _ = mimetypes.guess_type(str(path))
        ctype = ctype or "application/octet-stream"
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-cache")
        if not inline and path.suffix.lower() not in (".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf"):
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)

    def _safe_under(self, base: pathlib.Path, rel: str) -> pathlib.Path | None:
        target = (ROOT / rel).resolve()
        if not str(target).startswith(str(base.resolve())):
            return None
        return target

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path

        try:
            if p == "/api/topics":
                return self._json(200, load_topics())
            if p == "/api/coverage":
                return self._json(200, compute_coverage())
            if p == "/api/notes":
                return self._json(200, list_notes())
            if p == "/api/note":
                rel = q.get("path", [""])[0]
                target = self._safe_under(NOTES_DIR, rel)
                if not target or not target.exists():
                    return self._json(404, {"error": "not found"})
                text = target.read_text(encoding="utf-8")
                fm, body = parse_frontmatter(text)
                ext = target.suffix.lower()
                if ext == ".html":
                    body_html = body  # already HTML; do not run through markdown
                else:
                    body_html = render_md(body)
                return self._json(200, {
                    "path": rel, "raw": text,
                    "frontmatter": fm, "body_md": body,
                    "body_html": body_html, "ext": ext.lstrip("."),
                })
            if p == "/api/resources":
                return self._json(200, list_resources())
            if p == "/api/flashcards":
                return self._json(200, list_flashcards())
            if p == "/api/review-sheets":
                return self._json(200, list_review_sheets())
            if p == "/api/search":
                term = q.get("q", [""])[0].strip().lower()
                if not term:
                    return self._json(200, {"results": []})
                results = []
                for n in list_notes():
                    text = (ROOT / n["path"]).read_text(encoding="utf-8", errors="ignore").lower()
                    if term in text:
                        idx = text.find(term)
                        snippet_src = (ROOT / n["path"]).read_text(encoding="utf-8", errors="ignore")
                        snippet = snippet_src[max(0, idx - 80):idx + 160]
                        results.append({
                            "kind": "note",
                            "path": n["path"],
                            "title": (n["frontmatter"] or {}).get("title") or n["name"],
                            "snippet": snippet,
                        })
                # flashcards
                for deck in list_flashcards():
                    for card in deck.get("cards") or []:
                        t = (card.get("term","") + " " + card.get("definition","")).lower()
                        if term in t:
                            results.append({
                                "kind": "flashcard",
                                "deck": deck["name"],
                                "term": card.get("term",""),
                                "definition": card.get("definition",""),
                            })
                            if sum(1 for r in results if r["kind"] == "flashcard") > 30:
                                break
                # extracted PDFs
                extracted = ROOT / "resources" / "_extracted"
                if extracted.exists():
                    pdf_hits = 0
                    for txt in extracted.rglob("*.txt"):
                        content = txt.read_text(encoding="utf-8", errors="ignore")
                        lc = content.lower()
                        idx = lc.find(term)
                        if idx < 0:
                            continue
                        # scan backwards for the page-marker
                        page_no = "?"
                        for m in re.finditer(r"--- page (\d+) ---", content[:idx]):
                            page_no = m.group(1)
                        snippet = content[max(0, idx - 80):idx + 200]
                        snippet = re.sub(r"--- page \d+ ---\n?", "", snippet)
                        # Map back to the source PDF path
                        rel_pdf = str(txt.relative_to(extracted)).replace(".txt", ".pdf")
                        # rel_pdf is e.g. "biology/workbook.pdf" or "syllabus/664572-...pdf"
                        # the actual source lives at resources/<rel_pdf> or syllabus/<rel_pdf>
                        # The extraction layout mirrors the source tree under _extracted.
                        candidates = [ROOT / "resources" / rel_pdf, ROOT / rel_pdf]
                        src_path = next((str(c.relative_to(ROOT)) for c in candidates if c.exists()), None)
                        results.append({
                            "kind": "pdf",
                            "title": txt.stem.replace("-", " ").title(),
                            "page": page_no,
                            "path": src_path or str(txt.relative_to(ROOT)),
                            "snippet": snippet,
                        })
                        pdf_hits += 1
                        if pdf_hits >= 30:
                            break
                return self._json(200, {"results": results[:120]})

            # Asset serving (PDFs, images, pptx, syllabus, anything under ROOT)
            if p.startswith("/asset/"):
                rel = urllib.parse.unquote(p[len("/asset/"):])
                target = self._safe_under(ROOT, rel)
                if not target:
                    self.send_error(403); return
                return self._file(target)

            # Static frontend
            if p in ("/", "/index.html"):
                return self._file(STATIC / "index.html")
            if p.startswith("/static/"):
                target = self._safe_under(STATIC, "dashboard/static/" + p[len("/static/"):])
                if not target:
                    self.send_error(403); return
                return self._file(target)
            # SPA fallback
            return self._file(STATIC / "index.html")
        except Exception as e:
            sys.stderr.write(f"GET {p} error: {e}\n")
            return self._json(500, {"error": str(e)})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        p = u.path
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")

        try:
            if p == "/api/note":
                rel = q.get("path", [""])[0]
                target = self._safe_under(NOTES_DIR, rel)
                if not target:
                    return self._json(403, {"error": "forbidden"})
                data = json.loads(body)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(data["raw"], encoding="utf-8")
                return self._json(200, {"ok": True})
            return self._json(404, {"error": "no route"})
        except Exception as e:
            return self._json(500, {"error": str(e)})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Ripasso 0654 dashboard → http://localhost:{PORT}")
    print(f"  Project root: {ROOT}")
    print("  Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
