# igcse-revision-toolkit

A self-hosted revision dashboard for Cambridge IGCSE students. Drop your own past papers, notes, and flashcards into a folder structure; serve a local web UI that tracks your coverage, surfaces gaps, and lets you study from any device on your LAN (works well on an iPad).

Originally built for **0654 Co-ordinated Sciences (Double Award) — syllabus 2025-2027, papers 22 / 42 / 62**. The structure generalizes cleanly to any other Cambridge IGCSE syllabus you point it at.

## What this gives you

- **A dashboard** at `http://localhost:8765` showing per-topic coverage based on your notes
- **A topic tree** parsed from a syllabus YAML you provide
- **Flashcard runner** that consumes simple JSON decks
- **Coverage rules**: any subtopic heading (`## B1.1`, `## B1.2` …) with ≥30 characters of content beneath it is marked covered
- **No build step**: Python stdlib HTTP server, vanilla JS frontend

## What it does NOT include

This repo is the **engine, not the content**. You bring your own:

- Past papers (Cambridge International copyright — not redistributable)
- Mark schemes
- Textbook/resource scans
- Personal notes

Drop them into the directory layout below and the dashboard reads them automatically.

## Directory layout

```
your-revision-folder/
├── syllabus/        official syllabus PDF + topics.yaml (parsed topic tree)
├── papers/          past papers per paper variant (you bring these)
├── notes/           markdown notes — one stub per topic + mistake journal
├── flashcards/      JSON decks
├── resources/       textbooks, workbooks, study guides (you bring these)
├── dashboard/       local web app (this repo)
└── _inbox/          drop new files here, then sort
```

## Quickstart

```bash
git clone https://github.com/Cyberfilo/igcse-revision-toolkit.git
cd igcse-revision-toolkit

python3 -m venv .venv
source .venv/bin/activate
pip install pypdf markdown pyyaml python-docx python-pptx

# 1. Provide a syllabus YAML at syllabus/topics.yaml — see syllabus/EXAMPLE-topics.yaml
# 2. Drop your own notes in notes/<subject>/<TopicCode>-<slug>.md
# 3. Drop flashcards/<deck>.json
# 4. Drop your own papers/ and resources/

python dashboard/server.py
# Open http://localhost:8765
```

## Adding notes

Each topic stub uses Markdown frontmatter and one `##` heading per subtopic:

```markdown
---
topic: B1
subject: Biology
title: Characteristics of Living Organisms
---

## B1.1
[your notes here — 30+ chars marks this subtopic covered]

## B1.2
[your notes here]
```

## Adding flashcards

Drop a JSON file in `flashcards/`, shaped as either:

```json
[ { "term": "…", "definition": "…" }, ... ]
```

Or with metadata:

```json
{
  "title": "0654 — Biology B1",
  "source": "your-source",
  "cards": [ { "term": "…", "definition": "…" }, ... ]
}
```

## Adapting to another syllabus

The toolkit is wired specifically to the 0654 topic codes (`B1.1`, `C2.3`, `P5.4` etc.) by default, but the parser keys off:

1. `syllabus/topics.yaml` — list your subject codes
2. The notes-stub heading convention `## <code>`
3. The dashboard's per-subject view loops over whatever subjects you defined

Subject codes are free-form. Use whatever your syllabus uses. To switch from 0654 to, say, 0580 Mathematics or 0610 Biology, just rewrite `topics.yaml` and rename the note stubs.

## Cambridge International copyright note

This repo does not contain any Cambridge International or third-party copyrighted material. Past papers, mark schemes, and official syllabus content remain the property of Cambridge International Examinations and are not redistributed here. Bring your own copies (legally obtainable through your school or Cambridge's website).

