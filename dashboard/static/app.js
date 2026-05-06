/* Ripasso 0654 — vanilla SPA */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const SUBJECT_META = {
  biology:   { label: "Biology",   short: "Bio",  cls: "bio"  },
  chemistry: { label: "Chemistry", short: "Chem", cls: "chem" },
  physics:   { label: "Physics",   short: "Phys", cls: "phys" },
};

const fmt = {
  bytes(n) {
    if (n < 1024) return n + " B";
    if (n < 1024*1024) return (n/1024).toFixed(0) + " KB";
    return (n/1024/1024).toFixed(1) + " MB";
  },
  pct(c, t) { return t ? Math.round((c/t)*100) : 0; },
};

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

const state = {
  topics: null,
  coverage: null,
  notes: null,
  resources: null,
  decks: null,
  sheets: null,
  paperFilter: new Set(["22","42","62"]),
};

// KaTeX delimiters used everywhere we render markdown.
const KATEX_OPTS = {
  delimiters: [
    { left: "$$", right: "$$", display: true },
    { left: "$",  right: "$",  display: false },
    { left: "\\[", right: "\\]", display: true },
    { left: "\\(", right: "\\)", display: false },
  ],
  throwOnError: false,
  trust: true,
  strict: "ignore",
};
function applyMath(el) {
  if (el && window.renderMathInElement) {
    try { renderMathInElement(el, KATEX_OPTS); } catch (e) { console.warn("KaTeX:", e); }
  }
}

// ---- Routing ----
const routes = {
  "/coverage":  pageCoverage,
  "/notes":     pageNotes,
  "/cards":     pageCards,
  "/sheets":    pageSheets,
  "/map":       pageMap,
  "/resources": pageResources,
  "/search":    pageSearch,
};

function parseHash() {
  const h = location.hash.replace(/^#/, "") || "/coverage";
  const [path, qs] = h.split("?");
  const params = new URLSearchParams(qs || "");
  return { path: path || "/coverage", params };
}

async function render() {
  const { path, params } = parseHash();
  const route = path.split("/").slice(0, 2).join("/"); // /coverage, /notes, ...
  const fn = routes[route] || pageCoverage;
  $$("#nav a").forEach(a => {
    a.classList.toggle("active", a.dataset.route === route.replace("/", ""));
  });
  $("#view").innerHTML = '<div class="empty">Loading…</div>';
  try {
    await fn(params);
  } catch (e) {
    $("#view").innerHTML = `<div class="empty">Error: ${e.message}</div>`;
    console.error(e);
  }
}

window.addEventListener("hashchange", render);

// ---- Page: Coverage ----
async function pageCoverage() {
  if (!state.coverage) state.coverage = await api("/api/coverage");
  setCrumbs([{ label: "Coverage" }]);
  const cov = state.coverage;
  const subjects = ["biology", "chemistry", "physics"];
  const totalCovered = subjects.reduce((a,s) => a + (cov[s]?.covered||0), 0);
  const totalAll     = subjects.reduce((a,s) => a + (cov[s]?.total||0), 0);

  let html = `<h1>Coverage <span style="color:var(--tx-3);font-weight:400;font-size:14px;">— ${totalCovered}/${totalAll} subtopics covered (${fmt.pct(totalCovered,totalAll)}%)</span></h1>`;

  // Summary cards
  html += '<div class="cov-summary">';
  for (const s of subjects) {
    const m = SUBJECT_META[s];
    const c = cov[s] || { covered: 0, total: 0 };
    const p = fmt.pct(c.covered, c.total);
    html += `
      <div class="cov-card ${m.cls}">
        <div class="cov-card-name">${m.label}</div>
        <div class="cov-card-pct">${p}%</div>
        <div class="cov-card-frac">${c.covered} / ${c.total} subtopics</div>
        <div class="cov-bar"><div style="width:${p}%"></div></div>
      </div>`;
  }
  html += '</div>';

  // Per-subject sections
  for (const s of subjects) {
    const m = SUBJECT_META[s];
    const data = cov[s];
    if (!data) continue;
    html += `
      <section class="cov-section ${m.cls}" data-subject="${s}">
        <div class="cov-section-head">
          <div class="name"><span class="dot"></span>${m.label}</div>
          <div class="frac">${data.covered}/${data.total}</div>
        </div>`;
    for (const t of data.topics) {
      const p = fmt.pct(t.covered, t.total);
      html += `
        <div class="topic-row" data-toggle="${s}-${t.code}">
          <div class="code">${t.code}</div>
          <div class="title">${escapeHtml(t.title)}</div>
          <div class="meter">
            <div class="meter-bar"><div style="width:${p}%"></div></div>
            <span>${t.covered}/${t.total}</span>
          </div>
        </div>
        <div class="subtopic-list" id="sub-${s}-${t.code}" style="display:none;">`;
      for (const sub of t.subtopics) {
        const link = sub.note_paths[0]
          ? `<a href="#/notes?path=${encodeURIComponent(sub.note_paths[0])}" class="badge covered">covered</a>`
          : `<span class="badge uncovered">missing</span>`;
        html += `
          <div class="subtopic-row">
            <div class="code">${sub.code}</div>
            <div class="title">${escapeHtml(sub.title)}</div>
            ${link}
          </div>`;
      }
      html += '</div>';
    }
    html += '</section>';
  }
  $("#view").innerHTML = html;

  // toggles
  $$(".topic-row").forEach(row => {
    row.addEventListener("click", () => {
      const id = row.dataset.toggle;
      const panel = $(`#sub-${id}`);
      panel.style.display = panel.style.display === "none" ? "block" : "none";
    });
  });
}

// ---- Page: Notes (topic-aware picker) ----
async function pageNotes(params) {
  if (!state.notes)    state.notes    = await api("/api/notes");
  if (!state.coverage) state.coverage = await api("/api/coverage");
  if (!state.topics)   state.topics   = await api("/api/topics");

  const wantedPath = params.get("path");
  const filter = (params.get("q") || "").toLowerCase();
  setCrumbs([
    { label: "Notes" },
    ...(wantedPath ? [{ label: wantedPath.split("/").pop() }] : []),
  ]);

  // Index notes: subtopic-code → list, plus an "extras" bucket for non-topic notes
  const bySub = new Map();
  const extras = []; // notes without a parseable code (e.g. mistake journal)
  for (const n of state.notes) {
    const fm = n.frontmatter || {};
    const subs = (fm.subtopics && fm.subtopics.length ? fm.subtopics : (fm.code ? [fm.code] : []));
    if (!subs.length) { extras.push(n); continue; }
    for (const s of subs) {
      if (!bySub.has(s)) bySub.set(s, []);
      bySub.get(s).push(n);
    }
  }

  const matches = (n) => {
    if (!filter) return true;
    const fm = n.frontmatter || {};
    const hay = `${fm.code||""} ${fm.title||""} ${n.name}`.toLowerCase();
    return hay.includes(filter);
  };

  let tree = `
    <div class="picker-controls">
      <input id="picker-filter" class="picker-filter" placeholder="Filter — type code or word…" value="${escapeAttr(filter)}" />
      <div class="picker-legend"><span class="dot covered"></span> covered <span class="dot stub" style="margin-left:10px;"></span> stub</div>
    </div>`;

  const isStub = (n) => (n.body_chars < 80 && n.ext === "md");

  for (const [subjectKey, info] of Object.entries(state.topics)) {
    const meta = SUBJECT_META[subjectKey] || { label: subjectKey, cls: "" };
    const subjCov = state.coverage[subjectKey] || { covered: 0, total: 0 };
    let subjHtml = "";
    let subjTopicCount = 0;

    for (const t of info) {
      const tCov = state.coverage[subjectKey].topics.find(x => x.code === t.code) || {};
      const subtopics = t.subtopics?.length ? t.subtopics : [{ code: t.code, title: t.title }];

      // Collect viewable notes for this topic, dedup by path, attach owning subtopic
      const seen = new Set();
      const notes = [];
      for (const s of subtopics) {
        for (const n of (bySub.get(s.code) || [])) {
          if (seen.has(n.path)) continue;
          if (isStub(n)) continue;
          if (!matches(n)) continue;
          seen.add(n.path);
          notes.push({ note: n, sub: s });
        }
      }

      // Hide topics with no viewable notes
      if (notes.length === 0) continue;
      subjTopicCount++;

      const tCovered = tCov.covered ?? 0;
      const tTotal = tCov.total ?? subtopics.length;
      const tPct = tTotal ? Math.round((tCovered / tTotal) * 100) : 0;
      const tFracLabel = `${tCovered}/${tTotal}`;

      // Single-note topics → render as a direct link (no expansion needed)
      if (notes.length === 1) {
        const { note: n } = notes[0];
        subjHtml += `
          <a class="picker-topic single" href="#/notes?path=${encodeURIComponent(n.path)}" data-path="${escapeAttr(n.path)}">
            <span class="topic-code">${t.code}</span>
            <span class="topic-title">${escapeHtml(t.title)}</span>
            <span class="topic-meter" title="${tPct}% covered"><div style="width:${tPct}%"></div></span>
            <span class="topic-frac">${tFracLabel}</span>
          </a>`;
        continue;
      }

      // Multi-note topics → collapsible details
      let tInner = "";
      for (const { note: n, sub: s } of notes) {
        const fm = n.frontmatter || {};
        const tag = n.ext;
        const title = fm.title || n.name.replace(/\.[^.]+$/, "");
        tInner += `<a class="picker-leaf" href="#/notes?path=${encodeURIComponent(n.path)}" data-path="${escapeAttr(n.path)}">
          <span class="leaf-tag tag-${tag}">${tag}</span>
          <span class="leaf-sub">${s.code}</span>
          <span class="leaf-title">${escapeHtml(title)}</span>
        </a>`;
      }
      subjHtml += `
        <details class="picker-topic" ${filter ? 'open' : ''}>
          <summary>
            <span class="topic-code">${t.code}</span>
            <span class="topic-title">${escapeHtml(t.title)}</span>
            <span class="topic-meter" title="${tPct}% covered"><div style="width:${tPct}%"></div></span>
            <span class="topic-frac">${tFracLabel}</span>
            <span class="topic-count" title="${notes.length} notes">${notes.length}</span>
          </summary>
          <div class="picker-topic-body">${tInner}</div>
        </details>`;
    }

    // Hide subjects with no viewable topics
    if (subjTopicCount === 0) continue;

    tree += `
      <div class="picker-subject ${meta.cls}">
        <div class="picker-subject-head">
          <span class="dot subj"></span>
          <span class="subj-name">${meta.label}</span>
          <span class="subj-frac">${subjCov.covered}/${subjCov.total}</span>
        </div>
        ${subjHtml}
      </div>`;
  }

  // Extras (mistake journal etc.) — viewable only
  const extrasViewable = extras.filter(n => !isStub(n));
  if (extrasViewable.length && !filter) {
    tree += `<div class="picker-subject"><div class="picker-subject-head"><span class="dot subj" style="background:var(--tx-3)"></span><span class="subj-name">Other</span><span class="subj-frac">${extrasViewable.length}</span></div>`;
    for (const n of extrasViewable) {
      const fm = n.frontmatter || {};
      tree += `<a class="picker-topic single" href="#/notes?path=${encodeURIComponent(n.path)}" data-path="${escapeAttr(n.path)}">
        <span class="topic-code">${n.ext}</span>
        <span class="topic-title">${escapeHtml(fm.title || n.name.replace(/\.[^.]+$/, ""))}</span>
      </a>`;
    }
    tree += `</div>`;
  }

  // Compute quick stats for the empty-state panel
  const totalCovered = Object.values(state.coverage)
    .filter(v => v && typeof v.covered === 'number')
    .reduce((a, v) => a + v.covered, 0);
  const totalSubs = Object.values(state.coverage)
    .filter(v => v && typeof v.total === 'number')
    .reduce((a, v) => a + v.total, 0);
  const pctAll = totalSubs ? Math.round((totalCovered / totalSubs) * 100) : 0;

  const emptyPane = `
    <div class="note-pane-empty">
      <div class="nph">Pick a topic to start</div>
      <div class="npp">Topics with notes are listed on the left, grouped by subject. Click a topic to open its note — or expand it if it has more than one. The filter accepts a code (e.g. <code>B1.2</code>) or any keyword.</div>
      <div class="npstats">
        <span><b>${state.notes.length}</b> notes</span>
        <span><b>${totalCovered}</b>/${totalSubs} subtopics covered</span>
        <span><b>${pctAll}%</b> overall</span>
      </div>
    </div>`;

  $("#view").innerHTML = `
    <h1>Notes <span style="color:var(--tx-3);font-weight:400;font-size:14px;">— ${state.notes.length} files</span></h1>
    <div class="notes-layout">
      <div class="note-tree picker">${tree}</div>
      <div class="note-pane" id="note-pane">
        ${wantedPath ? '<div class="empty">Loading…</div>' : emptyPane}
      </div>
    </div>`;

  // Mark active (both leaves and single-note topic links)
  $$(".picker-leaf, .picker-topic.single").forEach(a => a.classList.toggle("active", a.dataset.path === wantedPath));
  // Auto-open the topic that contains the current note
  if (wantedPath) {
    const activeEl = $(`[data-path="${escapeAttr(wantedPath)}"]`);
    if (activeEl) {
      const topic = activeEl.closest("details.picker-topic");
      if (topic) topic.open = true;
      activeEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  // Filter input
  const fi = $("#picker-filter");
  let fdebounce;
  fi.addEventListener("input", e => {
    clearTimeout(fdebounce);
    fdebounce = setTimeout(() => {
      const v = e.target.value;
      const newHash = `/notes?${v ? `q=${encodeURIComponent(v)}` : ""}${wantedPath ? `${v?'&':''}path=${encodeURIComponent(wantedPath)}` : ""}`;
      location.hash = newHash;
    }, 180);
  });

  if (wantedPath) {
    const note = await api(`/api/note?path=${encodeURIComponent(wantedPath)}`);
    renderNote(note);
  }
}

let editorState = null;

function renderNote(note) {
  const fm = note.frontmatter || {};
  const chips = [];
  if (fm.code)     chips.push(`<span class="chip">${fm.code}</span>`);
  if (fm.subject)  chips.push(`<span class="chip">${fm.subject}</span>`);
  if (fm.papers)   chips.push(`<span class="chip">P${fm.papers.join(", P")}</span>`);
  if (fm.subtopics) chips.push(`<span class="chip">${fm.subtopics.length} subtopics</span>`);

  $("#note-pane").innerHTML = `
    <div class="note-toolbar">
      <button class="btn" id="btn-edit">Edit</button>
      <button class="btn primary" id="btn-save" style="display:none">Save</button>
      <button class="btn" id="btn-cancel" style="display:none">Cancel</button>
      <span style="margin-left:auto;color:var(--tx-3);font-size:11px;">${escapeHtml(note.path)}</span>
    </div>
    ${chips.length ? `<div class="note-meta">${chips.join("")}</div>` : ""}
    <div id="note-rendered">${rewriteAssetSrcs(note.body_html, note.path)}</div>
  `;

  applyMath($("#note-rendered"));
  editorState = note;

  $("#btn-edit").addEventListener("click", () => enterEdit(note));

  loadRelatedResources(note);
}

async function loadRelatedResources(note) {
  const fm = note.frontmatter || {};
  const title = (fm.title || "").trim();
  if (!title) return;
  // Pick the most distinctive 2 words of the title for search.
  const stop = new Set(["the","of","in","and","to","a","an","for","with","on","is","at","by","from"]);
  const words = title
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, " ")
    .split(/\s+/)
    .filter(w => w && !stop.has(w) && w.length > 2);
  if (!words.length) return;
  const q = words.slice(0, 2).join(" ");
  try {
    const data = await api(`/api/search?q=${encodeURIComponent(q)}`);
    const pdfs = (data.results || []).filter(r => r.kind === "pdf").slice(0, 6);
    if (!pdfs.length) return;
    const wrap = document.createElement("div");
    wrap.className = "related-resources";
    wrap.innerHTML = `
      <div class="section-h">Related in resources <span style="color:var(--tx-3);text-transform:none;letter-spacing:0;font-weight:400;font-size:10px;">— matched on "${escapeHtml(q)}"</span></div>
      <div class="related-list">
        ${pdfs.map(r => `
          <a href="/asset/${encodeURI(r.path)}#page=${r.page}" target="_blank" class="related-item">
            <div class="ri-meta">${escapeHtml(r.path.split('/').slice(1).join(' · '))} · <span class="ri-page">p.${escapeHtml(String(r.page))}</span></div>
            <div class="ri-snippet">${highlight(r.snippet.replace(/\s+/g, ' ').slice(0, 240), q)}</div>
          </a>
        `).join("")}
      </div>
    `;
    $("#note-pane").appendChild(wrap);
  } catch (e) { /* silent */ }
}

function enterEdit(note) {
  $("#note-rendered").innerHTML = `<textarea class="note-editor" id="editor"></textarea>`;
  $("#editor").value = note.raw;
  $("#btn-edit").style.display = "none";
  $("#btn-save").style.display = "";
  $("#btn-cancel").style.display = "";
  $("#btn-save").onclick = async () => {
    const raw = $("#editor").value;
    const r = await fetch(`/api/note?path=${encodeURIComponent(note.path)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw }),
    });
    if (r.ok) {
      // refresh
      state.coverage = null; state.notes = null;
      const fresh = await api(`/api/note?path=${encodeURIComponent(note.path)}`);
      renderNote(fresh);
      flashStatus("Saved");
    } else {
      flashStatus("Save failed");
    }
  };
  $("#btn-cancel").onclick = () => renderNote(note);
}

function rewriteAssetSrcs(html, notePath) {
  const dir = notePath.split("/").slice(0, -1).join("/");
  // Rewrite relative img paths to /asset/ URLs
  return html.replace(/<img\s+([^>]*?)src="([^"]+)"([^>]*)>/g, (m, pre, src, post) => {
    if (src.startsWith("http") || src.startsWith("/asset/") || src.startsWith("data:")) return m;
    const abs = src.startsWith("/") ? src.slice(1) : `${dir}/${src}`;
    return `<img ${pre}src="/asset/${encodeURI(abs)}"${post}>`;
  });
}

// ---- Page: Flashcards ----
async function pageCards(params) {
  if (!state.decks) state.decks = await api("/api/flashcards");
  setCrumbs([{ label: "Flashcards" }]);

  if (!state.decks.length) {
    $("#view").innerHTML = `
      <h1>Flashcards</h1>
      <div class="empty-deck">
        <div style="font-size:36px;margin-bottom:8px;">⎘</div>
        <div>No flashcard decks yet.</div>
        <div style="font-size:12px;margin-top:6px;color:var(--tx-3);">Drop a JSON file in <code>flashcards/</code> shaped as <code>[{"term":"…","definition":"…"}, …]</code> or <code>{"title":"…","cards":[…]}</code>.</div>
      </div>`;
    return;
  }

  const deckIdx = parseInt(params.get("deck") || "0", 10);
  const cardIdx = parseInt(params.get("i") || "0", 10);
  const deck = state.decks[deckIdx] || state.decks[0];

  let pickerHtml = '<div class="deck-picker">';
  state.decks.forEach((d, i) => {
    pickerHtml += `<a href="#/cards?deck=${i}" class="deck-pill ${i===deckIdx?'active':''}">${escapeHtml(d.name)} <span style="opacity:.6">· ${d.count}</span></a>`;
  });
  pickerHtml += '</div>';

  if (!deck.cards.length) {
    $("#view").innerHTML = `<h1>Flashcards</h1>${pickerHtml}<div class="empty-deck">Deck is empty.</div>`;
    return;
  }

  const i = Math.max(0, Math.min(cardIdx, deck.cards.length - 1));
  const card = deck.cards[i];
  $("#view").innerHTML = `
    <h1>Flashcards <span style="color:var(--tx-3);font-weight:400;font-size:14px;">— ${escapeHtml(deck.name)}</span></h1>
    ${pickerHtml}
    <div class="flashcard-stage">
      <div class="flashcard" id="card">
        <div class="flashcard-face front">
          <div class="face-label">term</div>
          <div>${escapeHtml(card.term || "")}</div>
          <div class="card-index">${i+1} / ${deck.cards.length}</div>
        </div>
        <div class="flashcard-face back">
          <div class="face-label">definition</div>
          <div>${escapeHtml(card.definition || "")}</div>
          <div class="card-index">${i+1} / ${deck.cards.length}</div>
        </div>
      </div>
    </div>
    <div class="flashcard-controls">
      <button class="btn" id="prev">← Prev</button>
      <div class="flashcard-progress"><div style="width:${((i+1)/deck.cards.length)*100}%"></div></div>
      <button class="btn" id="next">Next →</button>
    </div>
    <div style="text-align:center;color:var(--tx-3);font-size:11px;margin-top:12px;">
      Click card or press <kbd>Space</kbd> to flip · <kbd>←</kbd> <kbd>→</kbd> to navigate · <kbd>S</kbd> to shuffle
    </div>
  `;

  const cardEl = $("#card");
  cardEl.addEventListener("click", () => cardEl.classList.toggle("flipped"));
  $("#prev").onclick = () => navCard(deckIdx, i - 1, deck.cards.length);
  $("#next").onclick = () => navCard(deckIdx, i + 1, deck.cards.length);
}

function navCard(deck, i, total) {
  const next = (i + total) % total;
  location.hash = `/cards?deck=${deck}&i=${next}`;
}

// ---- Page: Review Sheets ----
async function pageSheets(params) {
  if (!state.sheets) state.sheets = await api("/api/review-sheets");
  setCrumbs([{ label: "Review Sheets" }]);

  const subjects = Object.keys(state.sheets);
  if (!subjects.length) {
    $("#view").innerHTML = `<h1>Review Sheets</h1><div class="empty-deck">No review sheets rendered yet.</div>`;
    return;
  }
  const subject = params.get("s") || "biology";
  const slideIdx = Math.max(1, parseInt(params.get("n") || "1", 10));
  const data = state.sheets[subject] || state.sheets[subjects[0]];
  const i = Math.min(Math.max(slideIdx, 1), data.slide_count);
  const slide = data.slides[i - 1];

  // subject tabs
  let tabs = '<div class="deck-picker">';
  for (const s of ["biology", "chemistry", "physics"]) {
    if (!state.sheets[s]) continue;
    const m = SUBJECT_META[s];
    tabs += `<a href="#/sheets?s=${s}&n=1" class="deck-pill ${s===subject?'active':''}">${m.label} <span style="opacity:.6">· ${state.sheets[s].slide_count}</span></a>`;
  }
  tabs += '</div>';

  // thumbs
  let thumbs = '<div class="thumb-strip">';
  for (let n = 1; n <= data.slide_count; n++) {
    const url = data.slides[n-1].url;
    thumbs += `<a class="thumb ${n===i?'active':''}" href="#/sheets?s=${subject}&n=${n}" title="Slide ${n}"><img src="${url}" alt="${n}" loading="lazy" /><span>${n}</span></a>`;
  }
  thumbs += '</div>';

  $("#view").innerHTML = `
    <h1>Review Sheets <span style="color:var(--tx-3);font-weight:400;font-size:14px;">— ${SUBJECT_META[subject]?.label || subject}</span></h1>
    ${tabs}
    <div class="slide-viewer">
      <button class="slide-nav prev" id="slide-prev" aria-label="Previous slide">‹</button>
      <div class="slide-stage" id="slide-stage">
        <img class="slide-img" src="${slide.url}" alt="Slide ${i}" />
      </div>
      <button class="slide-nav next" id="slide-next" aria-label="Next slide">›</button>
    </div>
    <div class="slide-meta">
      <div class="slide-counter">Slide ${i} / ${data.slide_count}${slide.title ? ` · ${escapeHtml(slide.title)}` : ""}</div>
      <div class="slide-progress"><div style="width:${(i/data.slide_count)*100}%"></div></div>
      <button class="btn" id="slide-fullscreen">Fullscreen</button>
    </div>
    ${thumbs}
    <div style="text-align:center;color:var(--tx-3);font-size:11px;margin-top:14px;">
      <kbd>←</kbd> <kbd>→</kbd> navigate · <kbd>F</kbd> fullscreen · <kbd>Esc</kbd> exit · <kbd>Home</kbd>/<kbd>End</kbd> jump
    </div>
  `;

  const goto = n => location.hash = `/sheets?s=${subject}&n=${Math.min(Math.max(n,1), data.slide_count)}`;
  $("#slide-prev").onclick = () => goto(i - 1);
  $("#slide-next").onclick = () => goto(i + 1);
  $("#slide-fullscreen").onclick = () => {
    const stage = $("#slide-stage");
    if (stage.requestFullscreen) stage.requestFullscreen();
  };
  // scroll active thumb into view
  const activeThumb = $(".thumb.active");
  if (activeThumb) activeThumb.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
}

// ---- Page: Resources ----
async function pageResources() {
  if (!state.resources) state.resources = await api("/api/resources");
  setCrumbs([{ label: "Resources" }]);
  const groups = [
    ["biology", "Biology"],
    ["chemistry", "Chemistry"],
    ["physics", "Physics"],
    ["syllabus", "Syllabus"],
    ["papers", "Past Papers"],
    ["general", "General"],
  ];
  let html = `<h1>Resources</h1>`;
  for (const [key, label] of groups) {
    const items = state.resources[key] || [];
    if (!items.length) continue;
    html += `<h2>${label} <span style="color:var(--tx-3);font-weight:400;font-size:13px;">${items.length}</span></h2>`;
    html += '<div class="res-grid">';
    for (const r of items.sort((a,b) => a.name.localeCompare(b.name))) {
      html += `
        <div class="res-card" data-path="${escapeAttr(r.path)}" data-ext="${r.ext}">
          <div class="res-type">${r.type_label}</div>
          <div class="res-name">${escapeHtml(r.name)}</div>
          <div class="res-meta">${escapeHtml(r.subdir)} · ${fmt.bytes(r.size)}</div>
        </div>`;
    }
    html += '</div>';
  }
  $("#view").innerHTML = html;
  $$(".res-card").forEach(c => {
    c.addEventListener("click", () => openAsset(c.dataset.path, c.dataset.ext));
  });
}

function openAsset(path, ext) {
  const url = "/asset/" + encodeURI(path);
  if (["pdf","jpg","jpeg","png","gif","svg"].includes(ext)) {
    showModal(path, `<iframe src="${url}"></iframe>`);
  } else {
    // For pptx, docx, etc — trigger download / open in default app
    window.open(url, "_blank");
  }
}

function showModal(title, inner) {
  const modal = document.createElement("div");
  modal.className = "modal";
  modal.innerHTML = `
    <div class="modal-inner">
      <div class="modal-head">
        <span style="font-size:13px;color:var(--tx-1);">${escapeHtml(title)}</span>
        <button class="btn" id="close">Close</button>
      </div>
      <div class="modal-body">${inner}</div>
    </div>`;
  modal.addEventListener("click", e => {
    if (e.target === modal || e.target.id === "close") modal.remove();
  });
  document.body.appendChild(modal);
}

// ---- Page: Map (Obsidian-style connection graph) ----
let mapAnim = null;

async function pageMap() {
  if (!state.topics)   state.topics   = await api("/api/topics");
  if (!state.coverage) state.coverage = await api("/api/coverage");
  if (!state.notes)    state.notes    = await api("/api/notes");
  setCrumbs([{ label: "Map" }]);

  // Build nodes & edges
  const nodes = [];
  const edges = [];
  const idx = new Map();
  const add = (id, type, label, meta = {}) => {
    const n = { id, type, label, ...meta, x: Math.random()*800, y: Math.random()*600, vx: 0, vy: 0 };
    idx.set(id, n);
    nodes.push(n);
    return n;
  };
  const link = (a, b, kind = "tree") => edges.push({ a, b, kind });

  // Subjects
  const SUBJ_COLOR = { biology: "#4ec97a", chemistry: "#7fa8ff", physics: "#f0a861" };
  for (const s of Object.keys(state.topics)) {
    add(`s:${s}`, "subject", SUBJECT_META[s].label, { color: SUBJ_COLOR[s], r: 28 });
  }
  // Topics + subtopics
  for (const [s, topics] of Object.entries(state.topics)) {
    for (const t of topics) {
      const tnode = add(`t:${t.code}`, "topic", t.code, {
        title: t.title,
        color: SUBJ_COLOR[s],
        subject: s,
        r: 12,
      });
      link(`s:${s}`, `t:${t.code}`);
      const subs = t.subtopics?.length ? t.subtopics : [{ code: t.code, title: t.title }];
      for (const sub of subs) {
        const tcov = state.coverage[s].topics.find(x => x.code === t.code);
        const subCov = tcov?.subtopics.find(x => x.code === sub.code);
        const covered = !!subCov?.covered;
        add(`u:${sub.code}`, "subtopic", sub.code, {
          title: sub.title,
          color: SUBJ_COLOR[s],
          subject: s,
          covered,
          notes: subCov?.note_paths || [],
          r: 6,
        });
        link(`t:${t.code}`, `u:${sub.code}`);
      }
    }
  }

  // Cross-links: subtopics that share a covering note (light dashed edges)
  const subByNote = new Map();
  for (const subj in state.coverage) {
    for (const t of state.coverage[subj].topics) {
      for (const sub of t.subtopics) {
        for (const np of sub.note_paths) {
          if (!subByNote.has(np)) subByNote.set(np, []);
          subByNote.get(np).push(sub.code);
        }
      }
    }
  }
  for (const codes of subByNote.values()) {
    for (let i = 0; i < codes.length; i++)
      for (let j = i + 1; j < codes.length; j++)
        link(`u:${codes[i]}`, `u:${codes[j]}`, "cross");
  }

  $("#view").innerHTML = `
    <h1>Map <span style="color:var(--tx-3);font-weight:400;font-size:14px;">— ${nodes.length} nodes, ${edges.length} edges</span></h1>
    <div class="map-container">
      <svg class="map-svg" id="map-svg" xmlns="http://www.w3.org/2000/svg"></svg>
      <div class="map-controls">
        <button id="map-reset" title="Reset view">⤾</button>
        <button id="map-relax" title="Relax layout">↺</button>
      </div>
      <div class="map-legend">
        <div class="lg-row"><span class="lg-dot" style="background:#4ec97a"></span>Biology</div>
        <div class="lg-row"><span class="lg-dot" style="background:#7fa8ff"></span>Chemistry</div>
        <div class="lg-row"><span class="lg-dot" style="background:#f0a861"></span>Physics</div>
        <div class="lg-row" style="margin-top:4px;color:var(--tx-3);">solid = parent · dashed = shared note</div>
      </div>
      <div class="map-tooltip" id="map-tt"></div>
    </div>
    <div style="text-align:center;color:var(--tx-3);font-size:11px;">
      Drag nodes · scroll to zoom · click subtopic to open its notes
    </div>
  `;

  const svg = $("#map-svg");
  const tooltip = $("#map-tt");
  const W = svg.clientWidth || 1000;
  const H = svg.clientHeight || 600;
  const cx = W / 2, cy = H / 2;

  // Initial layout: cluster around subject anchors
  const subjectAnchors = {};
  const subjects = Object.keys(state.topics);
  subjects.forEach((s, i) => {
    const angle = (i / subjects.length) * Math.PI * 2 - Math.PI/2;
    subjectAnchors[s] = { x: cx + Math.cos(angle) * 200, y: cy + Math.sin(angle) * 200 };
  });
  for (const n of nodes) {
    if (n.type === "subject") {
      const a = subjectAnchors[Object.keys(state.topics).find(k => `s:${k}` === n.id)];
      if (a) { n.x = a.x; n.y = a.y; }
    } else if (n.subject) {
      const a = subjectAnchors[n.subject];
      if (a) {
        const jitter = n.type === "topic" ? 80 : 120;
        n.x = a.x + (Math.random() - 0.5) * jitter;
        n.y = a.y + (Math.random() - 0.5) * jitter;
      }
    }
  }

  // SVG layers
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  let viewport = { x: 0, y: 0, scale: 1 };
  const gRoot = svgEl("g");
  const gEdges = svgEl("g");
  const gNodes = svgEl("g");
  gRoot.appendChild(gEdges); gRoot.appendChild(gNodes);
  svg.appendChild(gRoot);

  const edgeEls = edges.map(e => {
    const ln = svgEl("line", { class: `edge ${e.kind === "cross" ? "cross" : ""}` });
    gEdges.appendChild(ln);
    return ln;
  });

  const nodeEls = nodes.map(n => {
    const g = svgEl("g", { class: `node ${n.type}`, "data-id": n.id });
    const c = svgEl("circle", { r: n.r, fill: n.color || "var(--bg-3)" });
    const t = svgEl("text");
    t.textContent = n.label;
    g.appendChild(c); g.appendChild(t);
    gNodes.appendChild(g);

    g.addEventListener("mouseenter", () => showTip(n, g));
    g.addEventListener("mouseleave", () => tooltip.classList.remove("visible"));
    g.addEventListener("click", () => {
      if (n.type === "subtopic" && n.notes.length) {
        location.hash = `/notes?path=${encodeURIComponent(n.notes[0])}`;
      } else if (n.type === "subject") {
        location.hash = "/coverage";
      } else if (n.type === "topic") {
        location.hash = "/coverage";
      }
    });

    // Drag
    let dragging = false, lastX = 0, lastY = 0;
    g.addEventListener("mousedown", e => {
      dragging = true; lastX = e.clientX; lastY = e.clientY;
      n.fixed = true;
      e.stopPropagation();
    });
    document.addEventListener("mousemove", e => {
      if (!dragging) return;
      const dx = (e.clientX - lastX) / viewport.scale;
      const dy = (e.clientY - lastY) / viewport.scale;
      n.x += dx; n.y += dy;
      lastX = e.clientX; lastY = e.clientY;
    });
    document.addEventListener("mouseup", () => {
      if (dragging) { dragging = false; n.fixed = false; }
    });
    return { el: g, c, t, n };
  });

  function showTip(n, g) {
    const cov = n.covered ? "covered" : (n.type === "subtopic" ? "no notes" : "");
    tooltip.innerHTML = `
      <div class="tt-code">${n.id.startsWith("u:") || n.id.startsWith("t:") ? n.label : ""}</div>
      <div class="tt-title">${escapeHtml(n.title || n.label)}</div>
      ${cov ? `<div class="tt-meta">${cov}${n.notes?.length ? ` · ${n.notes.length} note${n.notes.length>1?'s':''}` : ''}</div>` : ''}
    `;
    const rect = svg.getBoundingClientRect();
    const containerRect = svg.parentElement.getBoundingClientRect();
    tooltip.style.left = ((n.x * viewport.scale + viewport.x + rect.left - containerRect.left) + 14) + "px";
    tooltip.style.top  = ((n.y * viewport.scale + viewport.y + rect.top  - containerRect.top) - 10) + "px";
    tooltip.classList.add("visible");
  }

  // Pan & zoom
  svg.addEventListener("wheel", e => {
    e.preventDefault();
    const d = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.25, Math.min(3, viewport.scale * d));
    // zoom toward mouse
    const r = svg.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    viewport.x = mx - (mx - viewport.x) * (newScale / viewport.scale);
    viewport.y = my - (my - viewport.y) * (newScale / viewport.scale);
    viewport.scale = newScale;
    applyTransform();
  }, { passive: false });

  let panning = false, panLx = 0, panLy = 0;
  svg.addEventListener("mousedown", e => {
    if (e.target.tagName === "svg" || e.target === gRoot) {
      panning = true; panLx = e.clientX; panLy = e.clientY;
    }
  });
  document.addEventListener("mousemove", e => {
    if (!panning) return;
    viewport.x += e.clientX - panLx;
    viewport.y += e.clientY - panLy;
    panLx = e.clientX; panLy = e.clientY;
    applyTransform();
  });
  document.addEventListener("mouseup", () => panning = false);

  function applyTransform() {
    gRoot.setAttribute("transform", `translate(${viewport.x},${viewport.y}) scale(${viewport.scale})`);
  }

  $("#map-reset").onclick = () => {
    viewport = { x: 0, y: 0, scale: 1 };
    applyTransform();
  };
  $("#map-relax").onclick = () => { ticks = 0; };

  // Force-directed simulation
  const REPULSION = 1400;
  const SPRING = 0.04;
  const SPRING_LEN = 70;
  const CROSS_LEN = 130;
  const DAMP = 0.86;
  const CENTER = 0.005;
  let ticks = 0;
  const MAX_TICKS = 600;

  function tick() {
    if (ticks >= MAX_TICKS) { mapAnim = null; return; }
    ticks++;
    // Reset forces
    for (const n of nodes) { n._fx = 0; n._fy = 0; }
    // Repulsion (n^2 — fine for ~150 nodes)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y;
        let d2 = dx*dx + dy*dy + 0.01;
        const f = REPULSION / d2;
        const d = Math.sqrt(d2);
        const fx = (dx/d) * f, fy = (dy/d) * f;
        a._fx += fx; a._fy += fy;
        b._fx -= fx; b._fy -= fy;
      }
    }
    // Springs
    for (const e of edges) {
      const a = idx.get(e.a), b = idx.get(e.b);
      if (!a || !b) continue;
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx*dx + dy*dy) + 0.01;
      const target = e.kind === "cross" ? CROSS_LEN : SPRING_LEN;
      const f = (d - target) * (e.kind === "cross" ? SPRING * 0.3 : SPRING);
      const fx = (dx/d) * f, fy = (dy/d) * f;
      a._fx += fx; a._fy += fy;
      b._fx -= fx; b._fy -= fy;
    }
    // Center pull
    for (const n of nodes) {
      n._fx += (cx - n.x) * CENTER;
      n._fy += (cy - n.y) * CENTER;
    }
    // Integrate
    for (const n of nodes) {
      if (n.fixed) continue;
      n.vx = (n.vx + n._fx) * DAMP;
      n.vy = (n.vy + n._fy) * DAMP;
      n.x += n.vx;
      n.y += n.vy;
    }
    // Render
    for (let i = 0; i < edgeEls.length; i++) {
      const e = edges[i], a = idx.get(e.a), b = idx.get(e.b);
      if (!a || !b) continue;
      edgeEls[i].setAttribute("x1", a.x);
      edgeEls[i].setAttribute("y1", a.y);
      edgeEls[i].setAttribute("x2", b.x);
      edgeEls[i].setAttribute("y2", b.y);
    }
    for (const ne of nodeEls) {
      ne.el.setAttribute("transform", `translate(${ne.n.x},${ne.n.y})`);
    }
    mapAnim = requestAnimationFrame(tick);
  }
  if (mapAnim) cancelAnimationFrame(mapAnim);
  mapAnim = requestAnimationFrame(tick);
}

function svgEl(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// ---- Page: Search ----
async function pageSearch(params) {
  setCrumbs([{ label: "Search" }]);
  const q = params.get("q") || "";
  $("#view").innerHTML = `
    <h1>Search</h1>
    <input id="search-input" class="quick-search" style="width:100%;padding:12px 14px;font-size:15px;" placeholder="Type to search notes & flashcards…" value="${escapeAttr(q)}" />
    <div id="search-results" style="margin-top:18px;"></div>
  `;
  $("#search-input").focus();
  let timer;
  $("#search-input").addEventListener("input", e => {
    clearTimeout(timer);
    timer = setTimeout(() => doSearch(e.target.value), 220);
  });
  if (q) doSearch(q);
}

async function doSearch(q) {
  const results = $("#search-results");
  if (!q.trim()) { results.innerHTML = ""; return; }
  results.innerHTML = '<div class="empty">Searching…</div>';
  const data = await api("/api/search?q=" + encodeURIComponent(q));
  if (!data.results.length) {
    results.innerHTML = '<div class="empty">No matches.</div>';
    return;
  }
  // group by kind for cleaner display
  const grouped = { note: [], flashcard: [], pdf: [] };
  for (const r of data.results) (grouped[r.kind] || (grouped[r.kind] = [])).push(r);

  let html = '<div class="search-results">';
  if (grouped.note.length) {
    html += `<h3>Notes <span style="color:var(--tx-3);font-weight:400">${grouped.note.length}</span></h3>`;
    for (const r of grouped.note) {
      html += `
        <a href="#/notes?path=${encodeURIComponent(r.path)}" class="search-result" style="display:block;">
          <div class="sr-kind kind-note">Note · ${escapeHtml(r.path.split("/").slice(1).join("/"))}</div>
          <div class="sr-title">${escapeHtml(r.title)}</div>
          <div class="sr-snippet">${highlight(r.snippet, q)}</div>
        </a>`;
    }
  }
  if (grouped.pdf.length) {
    html += `<h3>Resources (PDF) <span style="color:var(--tx-3);font-weight:400">${grouped.pdf.length}</span></h3>`;
    for (const r of grouped.pdf) {
      const url = `/asset/${encodeURI(r.path)}#page=${r.page}`;
      html += `
        <a href="${url}" target="_blank" class="search-result" style="display:block;">
          <div class="sr-kind kind-pdf">PDF · page ${escapeHtml(String(r.page))} · ${escapeHtml(r.path)}</div>
          <div class="sr-title">${escapeHtml(r.title)}</div>
          <div class="sr-snippet">${highlight(r.snippet, q)}</div>
        </a>`;
    }
  }
  if (grouped.flashcard.length) {
    html += `<h3>Flashcards <span style="color:var(--tx-3);font-weight:400">${grouped.flashcard.length}</span></h3>`;
    for (const r of grouped.flashcard) {
      html += `
        <div class="search-result">
          <div class="sr-kind kind-flashcard">Flashcard · ${escapeHtml(r.deck)}</div>
          <div class="sr-title">${highlight(r.term, q)}</div>
          <div class="sr-snippet">${highlight(r.definition, q)}</div>
        </div>`;
    }
  }
  html += '</div>';
  results.innerHTML = html;
}

// ---- Helpers ----
function setCrumbs(parts) {
  $("#crumbs").innerHTML = parts.map((p,i) =>
    `${i ? '<span class="sep">/</span>' : ''}<strong>${escapeHtml(p.label)}</strong>`
  ).join("");
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"]/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]));
}
function escapeAttr(s) { return escapeHtml(s).replace(/'/g, "&#39;"); }
function highlight(s, q) {
  const esc = escapeHtml(s);
  const re = new RegExp(escapeRe(q), "gi");
  return esc.replace(re, m => `<mark>${m}</mark>`);
}
function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
function naturalCompare(a, b) {
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}

function flashStatus(msg) {
  const pill = $("#status-pill");
  pill.textContent = msg;
  pill.style.background = "var(--accent-soft)";
  pill.style.color = "var(--accent)";
  setTimeout(() => {
    pill.textContent = state._statusBase || "ready";
    pill.style.background = "";
    pill.style.color = "";
  }, 1500);
}

// ---- Global keyboard ----
document.addEventListener("keydown", e => {
  // ignore in inputs
  if (["INPUT","TEXTAREA"].includes(e.target.tagName)) {
    if (e.key === "Escape") e.target.blur();
    return;
  }
  if (e.key === "/") {
    e.preventDefault();
    $("#quick-search").focus();
    return;
  }
  // flashcard shortcuts
  const card = $("#card");
  if (card) {
    const { path, params } = parseHash();
    if (path === "/cards") {
      const deckIdx = parseInt(params.get("deck") || "0", 10);
      const cardIdx = parseInt(params.get("i") || "0", 10);
      const total = state.decks[deckIdx]?.cards.length || 1;
      if (e.key === " ") { e.preventDefault(); card.classList.toggle("flipped"); }
      else if (e.key === "ArrowRight") navCard(deckIdx, cardIdx + 1, total);
      else if (e.key === "ArrowLeft")  navCard(deckIdx, cardIdx - 1, total);
      else if (e.key.toLowerCase() === "s") {
        const d = state.decks[deckIdx];
        for (let k = d.cards.length - 1; k > 0; k--) {
          const j = Math.floor(Math.random() * (k+1));
          [d.cards[k], d.cards[j]] = [d.cards[j], d.cards[k]];
        }
        navCard(deckIdx, 0, total);
      }
    }
  }
  // slide viewer shortcuts
  const stage = $("#slide-stage");
  if (stage) {
    const { path, params } = parseHash();
    if (path === "/sheets") {
      const subject = params.get("s") || "biology";
      const data = state.sheets?.[subject];
      const cur = parseInt(params.get("n") || "1", 10);
      const total = data?.slide_count || 1;
      const goto = n => location.hash = `/sheets?s=${subject}&n=${Math.min(Math.max(n,1), total)}`;
      if (e.key === "ArrowRight") goto(cur + 1);
      else if (e.key === "ArrowLeft") goto(cur - 1);
      else if (e.key === "Home") goto(1);
      else if (e.key === "End") goto(total);
      else if (e.key.toLowerCase() === "f") {
        if (stage.requestFullscreen) stage.requestFullscreen();
      }
    }
  }
});

// quick search
$("#quick-search").addEventListener("keydown", e => {
  if (e.key === "Enter") {
    location.hash = `/search?q=${encodeURIComponent(e.target.value)}`;
  }
});

// paper filter (currently informational — coverage filtering is future work)
$$('#paper-filter input').forEach(i => i.addEventListener("change", () => {
  state.paperFilter = new Set($$('#paper-filter input:checked').map(x => x.value));
}));

// status
async function bootStatus() {
  try {
    const cov = await api("/api/coverage");
    state.coverage = cov;
    const subjects = ["biology","chemistry","physics"];
    const c = subjects.reduce((a,s)=>a+(cov[s]?.covered||0),0);
    const t = subjects.reduce((a,s)=>a+(cov[s]?.total||0),0);
    state._statusBase = `${c}/${t} covered`;
    $("#status-pill").textContent = state._statusBase;
  } catch {
    $("#status-pill").textContent = "offline";
  }
}

// boot
bootStatus();
render();
