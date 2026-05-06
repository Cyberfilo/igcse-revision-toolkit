# Ripasso 0654 — Dashboard

Local revision dashboard for IGCSE 0654 Co-ordinated Sciences (Double Award).

## Run

From the project root:

```bash
source .venv/bin/activate
python dashboard/server.py
```

Open http://localhost:8765.

To pick a different port:

```bash
RIPASSO_PORT=9000 python dashboard/server.py
```

## What's where

- `server.py` — single-file HTTP server (Python stdlib + `markdown` + `pyyaml`)
- `static/index.html` — SPA shell
- `static/style.css` — design system + page styles
- `static/app.js` — vanilla JS routing & rendering (no framework, no CDN)

## Pages

- **Coverage** — subject → topic → subtopic tree with covered / missing badges; click a topic row to expand subtopics.
- **Notes** — file tree on the left, rendered markdown on the right with an Edit button (saves back to the `.md` file).
- **Flashcards** — flip cards (click or `Space`), `←` / `→` to navigate, `S` to shuffle. Decks come from JSON files in `../flashcards/`.
- **Resources** — grouped by subject. PDFs and images open in an in-app modal; pptx/docx open in your default app.
- **Search** — searches across notes (full text) and flashcards (term + definition).

## Coverage logic

A subtopic is marked **covered** when any note under `notes/<subject>/` either:

1. Has a `## <subtopic-code>` heading with ≥30 chars of meaningful content beneath it, or
2. Has `code: <topic-code>` in its frontmatter and ≥400 chars of body content (counts as coverage for all subtopics of that topic).

To make a stub topic count as covered, fill in the content under one of its `## B1.1`, `## C2.3` etc headings.

## API (for tinkering)

| Method | Path                          | Returns |
|--------|-------------------------------|---------|
| GET    | `/api/topics`                 | full topic tree |
| GET    | `/api/coverage`               | tree + coverage per subtopic |
| GET    | `/api/notes`                  | list of notes with frontmatter |
| GET    | `/api/note?path=…`            | rendered note (raw + html) |
| POST   | `/api/note?path=…`            | save note (body: `{ "raw": "…" }`) |
| GET    | `/api/resources`              | grouped resource list |
| GET    | `/api/flashcards`             | all decks |
| GET    | `/api/search?q=…`             | matches across notes + cards |
| GET    | `/asset/<path>`               | raw file under project root |
