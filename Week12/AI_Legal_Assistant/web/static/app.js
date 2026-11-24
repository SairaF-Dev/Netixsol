/* Khan & Associates - Legal Assistant: front end for web/server.py. All text is inserted as text, never as HTML. */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const URDU = /[؀-ۿ]/;

function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

/* text block that switches to Nastaliq and right-to-left when it contains Urdu script */
function prose(tag, text, cls = "") {
  const urdu = URDU.test(text || "");
  return h(tag, { class: (cls + (urdu ? " urdu" : "")).trim(), dir: "auto", text: text || "" });
}

/* ---------------------------------------------------------------- sign-in token (this tab only) */
const store = {
  get() { try { return sessionStorage.getItem("la-token"); } catch (_) { return null; } },
  set(v) { try { v ? sessionStorage.setItem("la-token", v) : sessionStorage.removeItem("la-token"); } catch (_) { /* private mode */ } },
};
let TOKEN = store.get();

class ApiError extends Error {
  constructor(message, extra = {}) { super(message); Object.assign(this, extra); }
}

async function api(path, options = {}) {
  const headers = Object.assign({}, options.headers || {}, TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {});
  const res = await fetch(path, Object.assign({}, options, { headers }));
  let body = null;
  try { body = await res.json(); } catch (_) { /* not JSON */ }
  if (res.status === 401 && path !== "/api/login") { signOut(); throw new ApiError("Please sign in again."); }
  if (!res.ok) {
    const d = body && body.detail;
    if (d && typeof d === "object" && d.blocked) throw new ApiError(d.message, { blocked: d });
    throw new ApiError((typeof d === "string" && d) || `Request failed (${res.status})`);
  }
  return body;
}

/* downloads carry the token too, so a link cannot be shared to someone who is not signed in */
async function saveFile(url, name) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${TOKEN}` } });
  if (!res.ok) { alert("The file could not be downloaded."); return; }
  const blob = await res.blob();
  const a = h("a", { href: URL.createObjectURL(blob), download: name || url.split("/").pop() });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
const downloadLink = (url, text) => h("a", { class: "download", href: "#", text, onclick: e => { e.preventDefault(); saveFile(url); } });
const postJSON = (path, data) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

function copyToClipboard(text, btn, feedbackText = "Copied ✓") {
  const applyFeedback = () => {
    if (!btn) return;
    const orig = btn.textContent;
    btn.textContent = feedbackText;
    btn.classList.add("copied");
    setTimeout(() => { btn.textContent = orig; btn.classList.remove("copied"); }, 2000);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(applyFeedback).catch(() => fallbackCopy(text, applyFeedback));
  } else {
    fallbackCopy(text, applyFeedback);
  }
}
function fallbackCopy(text, cb) {
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    if (cb) cb();
  } catch (_) {}
}

function working(box, message) {
  box.replaceChildren(h("div", { class: "working" }, h("div", { class: "work-msg", text: message }), h("div", { class: "bar" }),
    h("div", { class: "note", text: "Cached research responses load immediately; new queries execute primary verification protocol." })));
}
function showError(box, err) {
  if (err.blocked) {
    const b = err.blocked;
    box.replaceChildren(h("div", { class: "blocked" },
      h("p", { class: "eyebrow", text: "Blocked · possible prompt injection" }),
      h("h2", { text: `${b.file} was not processed.` }),
      h("p", { text: b.message }),
      h("ul", { class: "cites" }, b.findings.map(f => h("li", {},
        h("div", { class: "cite-ref", text: `${f.kind}${f.hidden ? " · hidden text" : ""}` }),
        h("div", { class: "cite-meta", text: f.location }),
        prose("blockquote", f.text)))),
      h("p", { class: "note", text: "This attempt has been recorded in the audit log." })));
    return;
  }
  box.replaceChildren(h("p", { class: "error", text: err.message || String(err) }));
}

function hiddenWarning(list) {
  if (!list || !list.length) return null;
  return h("details", { class: "hidden-warn", open: true },
    h("summary", { text: `Warning: ${list.length} piece${list.length > 1 ? "s" : ""} of hidden text in the upload (white, tiny or hidden formatting)` }),
    h("ul", {}, list.map(t => h("li", {}, prose("span", t)))));
}
/* slow work runs as a background job: the request returns a job id at once, then the page polls it */
const sleep = ms => new Promise(r => setTimeout(r, ms));
const STATUS_TEXT = { queued: "Waiting for the worker", running: "Working" };

async function waitJob(reply, box) {
  if (!reply || !reply.job_id) return reply;
  const started = Date.now();
  for (;;) {
    await sleep(1500);
    const job = await api(`/api/jobs/${reply.job_id}`);
    if (job.status === "done") return job.result;
    if (job.status === "failed") throw new ApiError(job.error || "The job failed.");
    const msg = box && box.querySelector(".work-msg");
    if (msg) msg.textContent = `${STATUS_TEXT[job.status] || job.status}${job.progress ? ": " + job.progress : ""}… (${Math.round((Date.now() - started) / 1000)} s)`;
  }
}

async function run(form, box, message, task) {
  const btn = $("button[type=submit]", form);
  btn.disabled = true;
  working(box, message);
  try { await task(); }
  catch (err) { showError(box, err); }
  finally { btn.disabled = false; }
}

/* ---------------------------------------------------------------- views */
const VIEWS = ["research", "caselaw", "review", "compare", "drafting", "upload", "evaluation", "audit", "rating"];
function showView() {
  const name = VIEWS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "research";
  for (const v of VIEWS) $(`#view-${v}`).hidden = v !== name;
  document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("active", a.dataset.view === name));
  if (name === "evaluation" && META && !$("#report-body").dataset.loaded) openReport(META.reports[0]);
  if (name === "evaluation" && TOKEN && !DASH) loadDashboard();
  if (name === "audit" && TOKEN) loadAudit();
  if (name === "upload" && TOKEN) loadUploads();
  if (name === "rating" && TOKEN && !RATING) loadRating();
}
window.addEventListener("hashchange", () => { showView(); window.scrollTo(0, 0); });

/* ---------------------------------------------------------------- research and case law */
const MODE_LABEL = { vector: "Statutory Provisions", graph: "Judicial Precedents", hybrid: "Composite Corpus" };
const RESEARCH_EXAMPLES = [
  "Contract Act, 1872: Voidability of Unlawful Consideration (Section 23)",
  "Pakistan Penal Code, 1860: Standard of Proof & Sentencing for Qatl-e-Amd (Section 302)",
  "معاہدہ ایکٹ 1872: دفعہ 74 کے تحت خلاف ورزی پر ہرجانے اور تعزیری معاوضے کا تعین",
  "Supreme Court Precedent: Police Procedure upon Pre-Arrest Bail Dismissal",
  "Companies Act, 2017: Statutory Incorporation & Regulatory Compliance",
];
const GRAPH_EXAMPLES = [
  "Which judges sat on the cases in the corpus that refer to Section 324 of the Pakistan Penal Code?",
  "Which judges presided over proceedings referencing Article 129 of the Qanun-e-Shahadat Order, 1984?",
  "Which judges heard cases involving Section 7 of the Anti-Terrorism Act, 1997?",
  "Which Supreme Court judgments in the corpus refer to Article 212 of the Constitution?",
  "Which sections of the Pakistan Penal Code came up in cases heard by Justice Malik Shahzad Ahmad Khan?",
  "Which precedent is cited the most in the corpus?",
];

function exampleButtons(box, list, input, form) {
  for (const q of list) {
    box.append(h("button", { type: "button", class: URDU.test(q) ? "urdu" : "", dir: "auto", text: q,
      onclick: () => { input.value = q; form.requestSubmit(); } }));
  }
}

function graphItem(text) {
  // "<case> (<document id>): <details>" or a plain name
  const m = /^(.*?) \(([A-Za-z0-9_.\-]+)\)(?:: (.*))?$/.exec(text);
  if (!m) return h("li", {}, prose("span", text));
  return h("li", {}, prose("span", m[1]), h("span", { class: "detail", text: [m[3], m[2]].filter(Boolean).join(" · ") }));
}

function renderGraph(g) {
  const out = [h("h3", { text: "From the case-law graph" })];
  if (g.error) out.push(h("p", { class: "error", text: `The graph query failed: ${g.error}` }));
  out.push(h("p", { class: "count", text: String(g.items.length) }),
    h("p", { class: "note", text: g.items.length === 1 ? "result" : "results" }));
  if (g.items.length) out.push(h("ul", { class: "items" }, g.items.map(graphItem)));
  else out.push(h("p", { class: "note", text: "No judgment in the graph matches. Check the provision or citation, or ask in text search." }));
  const how = { local: "Followed citations, provisions and benches named in the inquiry.",
                global: "Aggregated over the complete judicial precedent repository.",
                "text-to-cypher": "Direct entity index missed; relational query executed under read-only verification policy." };
  out.push(h("details", {}, h("summary", { text: "How this was found" }),
    h("p", { class: "note", text: how[g.method] || g.method }), g.cypher ? h("pre", { text: g.cypher }) : null));
  return h("div", { class: "graph-block" }, out);
}

function citationRef(c) {
  return [c.act_or_case, c.reference, c.title ? `(${c.title})` : null].filter(Boolean).join(", ").replace(", (", " (");
}

function conclusionNote(check, refused) {
  if (!check) return null;
  if (check.withheld) return h("p", { class: "check-note bad" }, h("b", { text: "Withheld after review. " }),
    `An answer was drafted twice, but its conclusion does not follow from the sources: ${check.issue}`);
  if (check.redrafted) return h("p", { class: "check-note" }, h("b", { text: refused ? "First answer rejected. " : "Redrafted after review. " }),
    `A review found the first answer's conclusion did not follow from the sources: ${check.first_issue}`);
  if (check.verdict === "partly") return h("p", { class: "check-note warn" }, h("b", { text: "Read with care. " }), check.issue);
  return refused ? null : h("p", { class: "check-note ok", text: "Conclusion checked against all retrieved passages." });
}

function renderAnswer(a) {
  const refused = !a.citations.length;
  const copyMemoBtn = !refused ? h("button", {
    type: "button",
    class: "btn-action-sm",
    text: "Copy Legal Memorandum",
    onclick: e => {
      const full = `MEMORANDUM OF LAW\nJurisdiction: Islamic Republic of Pakistan\n\nOPINION:\n${a.short_answer}\n\nLEGAL GROUNDS & REASONING:\n${a.explanation || ''}\n\nAUTHORITIES CITED:\n${a.citations.map(c => `• ${citationRef(c)}${c.page ? ', page ' + c.page : ''}:\n  "${c.quote}"`).join('\n\n')}`;
      copyToClipboard(full, e.target, "Memorandum Copied ✓");
    }
  }) : null;

  const left = h("div", { class: refused ? "refusal" : "" }, h("h3", { text: "Answer" }), prose("p", a.short_answer, "short"),
    a.explanation ? prose("p", a.explanation, "explain") : null,
    conclusionNote(a.conclusion_check, refused),
    copyMemoBtn,
    refused && !(a.conclusion_check || {}).redrafted ? h("p", { class: "note", text: "Repository protocol: Opinions are rendered only where authoritative statutory or judicial sources substantiate the position." }) : null);
  const right = h("div", {}, h("h3", { text: refused ? "Sources" : "Verified sources" }),
    refused ? h("p", { class: "note", text: "No citation passed the checks." }) :
      h("ol", { class: "cites" }, a.citations.map(c => h("li", {},
        h("div", { class: "cite-head" },
          prose("div", citationRef(c), "cite-ref"),
          h("button", {
            type: "button",
            class: "btn-copy-cite",
            text: "Copy Citation",
            onclick: e => {
              const text = `"${c.quote}"\n— ${citationRef(c)}${c.page ? ', page ' + c.page : ''} (Supreme Court / High Court of Pakistan)`;
              copyToClipboard(text, e.target, "Copied ✓");
            }
          })
        ),
        c.page ? h("div", { class: "cite-meta", text: `page ${c.page}` }) : null,
        prose("blockquote", c.quote)))));
  const extra = [];
  if (a.removed_citations.length) {
    extra.push(h("details", {}, h("summary", { text: `${a.removed_citations.length} citation${a.removed_citations.length > 1 ? "s" : ""} removed by the checker` }),
      h("ul", {}, a.removed_citations.map(r => h("li", {}, prose("span", r.citation), h("span", { class: "note", text: ` · ${r.reason}` }))))));
  }
  extra.push(h("details", {}, h("summary", { text: `Passages retrieved (${a.retrieved.length})` }),
    h("ul", {}, a.retrieved.map(r => h("li", {}, prose("span", r.source))))));
  return h("div", {}, h("div", { class: "answer" }, left, right), extra);
}

function renderAsk(box, data) {
  const signals = [...data.route.graph_signals, ...data.route.content_signals];
  const route = h("div", { class: "route" }, h("b", { text: MODE_LABEL[data.mode] }),
    h("span", { text: data.chosen_by === "router" ? `Chosen by the router${signals.length ? ": " + signals.join("; ") : " (no graph signal, so text search)"}` : "Chosen by you" }));
  const parts = [route];
  for (const e of data.errors || []) parts.push(h("p", { class: "error", text: e }));
  if (data.graph) parts.push(renderGraph(data.graph));
  if (data.answer) parts.push(renderAnswer(data.answer));
  box.replaceChildren(...parts);
}

$("#ask-form").addEventListener("submit", e => {
  e.preventDefault();
  const question = $("#ask-q").value.trim();
  const mode = $("input[name=mode]:checked").value;
  const box = $("#ask-result");
  run(e.target, box, "Searching the corpus, then checking every citation against its source…",
    async () => renderAsk(box, await postJSON("/api/ask", { question, mode })));
});
$("#graph-form").addEventListener("submit", e => {
  e.preventDefault();
  const box = $("#graph-result");
  run(e.target, box, "Following links in the graph…",
    async () => renderAsk(box, await postJSON("/api/ask", { question: $("#graph-q").value.trim(), mode: "graph" })));
});

/* ---------------------------------------------------------------- review */
const STATUS = { green: "Acceptable", amber: "Negotiate", red: "Unacceptable", missing: "Missing" };
const status = s => h("span", { class: `s s-${s}`, text: STATUS[s] || s });

function renderReview(box, r) {
  const count = s => r.findings.filter(f => f.status === s).length;
  const findings = r.findings.slice().sort((a, b) => ["red", "missing", "amber", "green"].indexOf(a.status) - ["red", "missing", "amber", "green"].indexOf(b.status));
  box.replaceChildren(
    h("div", { class: "score" },
      h("div", { class: "big" }, String(r.risk_score), h("small", { text: " / 100" })),
      h("div", {}, h("div", { class: `band s-${r.band.toLowerCase()}`, text: `${r.band} risk` }),
        h("h2", { text: r.title || "Contract" }),
        h("div", { class: "note", text: `Reviewed for ${r.party}${r.type ? " · " + r.type : ""}` }))),
    h("div", { class: "tally" }, ["green", "amber", "red", "missing"].map(s => h("span", {}, status(s), ` ${count(s)}`))),
    downloadLink(r.download, "Download the Word file with margin comments"), hiddenWarning(r.hidden_text),
    h("div", { class: "findings" }, findings.map(f => h("article", { class: "finding" },
      h("div", {}, status(f.status), f.required ? h("div", { class: "note", text: "required" }) : null),
      h("div", {},
        h("h4", {}, f.title, f.clause_ids.length ? h("span", { class: "clause", text: "clause " + f.clause_ids.join(", ") }) : null),
        prose("p", f.reason),
        f.quote ? prose("blockquote", f.quote) : null,
        f.quote_note ? h("div", { class: "warnline", text: `Quote removed: ${f.quote_note.replace(/^the model's quote /, "the quote ")}` }) : null,
        (f.suggested_wording || f.sources.length) ? h("details", {}, h("summary", { text: f.suggested_wording ? "Suggested wording and legal source" : "Legal source" }),
          f.suggested_wording ? prose("p", f.suggested_wording, "wording") : null,
          f.sources.map(s => h("div", { class: "src" }, h("b", { text: `${s.act}, section ${s.section} (${s.title})` }), s.page ? `, page ${s.page}` : "", prose("blockquote", s.quote)))) : null)))),
  );
}

$("#review-form").addEventListener("submit", e => {
  e.preventDefault();
  const fd = new FormData();
  const file = $("#review-file").files[0];
  if (file) { fd.append("file", file); fd.append("matter", $("#review-matter").value); } else fd.append("contract_id", $("#review-sample").value);
  fd.append("party", $("#review-party").value);
  const box = $("#review-result");
  run(e.target, box, "Finding the relevant clauses, rating each playbook position and checking every quote…",
    async () => renderReview(box, await waitJob(await api("/api/review", { method: "POST", body: fd }), box)));
});
$("#review-file").addEventListener("change", e => {
  const chosen = !!e.target.files.length;
  $("#review-sample").disabled = chosen; $("#review-matter-field").hidden = !chosen;
});

/* ---------------------------------------------------------------- compare */
function renderCompare(box, r) {
  const head = h("div", { class: "score" },
    h("div", { class: "big", text: String(r.changes.length) }),
    h("div", {}, h("div", { class: "band", text: r.changes.length === 1 ? "change" : "changes" }),
      h("h2", { text: r.new }), h("div", { class: "note", text: `against ${r.old} · ${r.unchanged} clause${r.unchanged === 1 ? "" : "s"} unchanged · for ${r.client}` })));
  const changes = r.changes.map(c => {
    const imp = c.impact || {};
    const ops = c.diff || (c.kind === "removed" ? [["delete", c.old_text]] : [["insert", c.new_text]]);
    const red = h("p", { class: "redline", dir: "auto" }, ops.map(([op, t], i) =>
      [i ? " " : "", op === "delete" ? h("del", { text: t }) : op === "insert" ? h("ins", { text: t }) : h("span", { class: "same", text: t })]));
    return h("article", { class: "change" }, h("div", { class: "n", text: String(c.n) }), h("div", {},
      h("div", { class: "change-head" }, h("h4", { text: c.new_clause || c.old_clause }),
        h("span", { class: "meta" }, c.kind, " · ", imp.risk ? h("span", { class: `s s-${imp.risk}`, text: imp.risk === "none" ? "no risk" : `${imp.risk} risk` }) : "not rated",
          imp.favours && imp.favours !== "neither" ? ` · favours the ${imp.favours}` : "")),
      red,
      imp.summary ? h("p", { class: "impact" }, h("b", { text: imp.summary + " " }), imp.legal_impact || "") : h("p", { class: "note", text: "No explanation returned for this change." })));
  });
  box.replaceChildren(head, downloadLink(r.download, "Download the Word redline"), hiddenWarning(r.hidden_text) || "", h("div", { class: "findings" }, changes));
}

$("#compare-sample").addEventListener("change", e => { $("#compare-uploads").hidden = e.target.checked; });
$("#compare-form").addEventListener("submit", e => {
  e.preventDefault();
  const fd = new FormData();
  const sample = $("#compare-sample").checked;
  fd.append("use_sample", sample ? "true" : "false");
  if (!sample) {
    const a = $("#compare-old").files[0], b = $("#compare-new").files[0];
    if (!a || !b) { showError($("#compare-result"), new Error("Choose both versions, or use the sample pair.")); return; }
    fd.append("old_file", a); fd.append("new_file", b); fd.append("matter", $("#compare-matter").value);
  }
  fd.append("client", $("#compare-client").value);
  const box = $("#compare-result");
  run(e.target, box, "Matching clauses, marking changed words and explaining each change…",
    async () => renderCompare(box, await waitJob(await api("/api/compare", { method: "POST", body: fd }), box)));
});

/* ---------------------------------------------------------------- drafting */
function renderDraft(box, d) {
  const sheet = h("article", { class: "sheet" },
    h("div", { class: "stamp", text: "Draft — for lawyer review" }),
    prose("h2", d.title),
    d.header ? h("p", { class: "head", text: d.header }) : null,
    d.sections.map(s => h("section", {}, prose("h5", s.heading), prose("p", s.text, "body"),
      s.sources.length ? h("ul", { class: "fn" }, s.sources.map(src => h("li", {}, h("i", { text: src.source }), ": ", prose("span", `“${src.quote}”`)))) : null)),
    Object.entries(d.authorities || {}).filter(([, v]) => v.length).map(([k, v]) =>
      h("section", {}, h("h5", { text: `Authorities: ${k}` }), h("p", { class: "note", text: v.join("; ") + " (from the knowledge graph)" }))),
    h("p", { class: "note", style: "margin-top:26px", text: `${d.removed_citations} citation${d.removed_citations === 1 ? "" : "s"} removed by verification.` }));
  const printBtn = h("button", {
    type: "button",
    class: "btn-action-print",
    text: "Print Document / Save PDF",
    onclick: () => window.print()
  });
  box.replaceChildren(h("div", { class: "draft-toolbar" }, downloadLink(d.download, "Download as Word (.docx)"), printBtn), sheet);
}

document.querySelectorAll("input[name=dkind]").forEach(r => r.addEventListener("change", () => {
  const kind = $("input[name=dkind]:checked").value;
  for (const k of ["brief", "notice", "clauses"]) $(`#draft-${k}`).hidden = k !== kind;
}));
const lines = id => $(id).value.split("\n").map(s => s.trim()).filter(Boolean);

$("#draft-brief").addEventListener("submit", e => {
  e.preventDefault();
  const label = $("#brief-judgment").value.trim();
  const j = META.judgments.find(x => x.label === label || x.id === label);
  const box = $("#draft-result");
  if (!j) { showError(box, new Error("Choose a judgment from the list.")); return; }
  run(e.target, box, "Reading the judgment and checking each quote against its paragraph…",
    async () => renderDraft(box, await waitJob(await postJSON("/api/draft/brief", { document_id: j.id }), box)));
});
$("#draft-notice").addEventListener("submit", e => {
  e.preventDefault();
  const box = $("#draft-result");
  const body = { sender: $("#n-sender").value, recipient: $("#n-recipient").value, date: $("#n-date").value,
    contract: $("#n-contract").value, facts: lines("#n-facts"), demand: $("#n-demand").value, legal_questions: lines("#n-law") };
  run(e.target, box, "Researching the legal basis and verifying every citation…",
    async () => renderDraft(box, await waitJob(await postJSON("/api/draft/notice", body), box)));
});
$("#draft-clauses").addEventListener("submit", e => {
  e.preventDefault();
  const box = $("#draft-result");
  const facts = {};
  for (const l of lines("#c-facts")) { const i = l.indexOf(":"); if (i > 0) facts[l.slice(0, i).trim()] = l.slice(i + 1).trim(); }
  const items = [...document.querySelectorAll("#c-items input:checked")].map(i => i.value);
  run(e.target, box, "Adapting the firm's standard wording to the deal…",
    async () => renderDraft(box, await waitJob(await postJSON("/api/draft/clauses", { title: $("#c-title").value, facts, items }), box)));
});

/* ---------------------------------------------------------------- evaluation: a small Markdown renderer */
function inline(text) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|~~[^~]+~~|`[^`]+`|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith("**")) out.push(h("strong", { text: t.slice(2, -2) }));
    else if (t.startsWith("~~")) out.push(h("del", { text: t.slice(2, -2) }));
    else if (t.startsWith("`")) out.push(h("code", { text: t.slice(1, -1) }));
    else out.push(h("em", { text: t.slice(1, -1) }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}
const cells = row => row.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
const NUMERIC = /^[-+]?[\d.,]+\s*%?$|^[-–]$/;

function markdown(src) {
  const root = document.createDocumentFragment();
  const rows = src.replace(/\r/g, "").split("\n");
  for (let i = 0; i < rows.length;) {
    const line = rows[i];
    if (!line.trim()) { i++; continue; }
    const head = /^(#{1,4})\s+(.*)$/.exec(line);
    if (head) { root.append(h(`h${Math.min(head[1].length, 3)}`, {}, inline(head[2]))); i++; continue; }
    if (line.trim().startsWith("|") && rows[i + 1] && /^\s*\|?\s*:?-{2,}/.test(rows[i + 1])) {
      const header = cells(line); i += 2;
      const body = [];
      while (i < rows.length && rows[i].trim().startsWith("|")) body.push(cells(rows[i++]));
      const numCol = header.map((_, c) => body.length && body.every(r => !r[c] || NUMERIC.test(r[c])));
      root.append(h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, header.map((c, k) => h("th", { class: numCol[k] ? "num" : "" }, inline(c))))),
        h("tbody", {}, body.map(r => h("tr", {}, header.map((_, k) => h("td", { class: numCol[k] ? "num" : "", dir: "auto" }, inline(r[k] || "")))))))));
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const list = h(ordered ? "ol" : "ul");
      while (i < rows.length && /^\s*([-*]|\d+\.)\s+/.test(rows[i])) list.append(h("li", { dir: "auto" }, inline(rows[i++].replace(/^\s*([-*]|\d+\.)\s+/, ""))));
      root.append(list); continue;
    }
    if (line.startsWith(">")) {
      const q = [];
      while (i < rows.length && rows[i].startsWith(">")) q.push(rows[i++].replace(/^>\s?/, ""));
      root.append(h("blockquote", { dir: "auto" }, inline(q.join(" ")))); continue;
    }
    if (line.startsWith("```")) {
      const code = []; i++;
      while (i < rows.length && !rows[i].startsWith("```")) code.push(rows[i++]);
      i++; root.append(h("pre", { text: code.join("\n") })); continue;
    }
    const para = [];
    while (i < rows.length && rows[i].trim() && !/^(#{1,4}\s|\||>|```|\s*([-*]|\d+\.)\s)/.test(rows[i])) para.push(rows[i++].trim());
    if (!para.length) { para.push(rows[i++]); }
    root.append(h("p", { dir: "auto" }, inline(para.join(" "))));
  }
  return root;
}

async function openReport(r) {
  if (!r) return;
  const body = $("#report-body");
  body.dataset.loaded = "1";
  document.querySelectorAll("#report-list button").forEach(b => b.classList.toggle("active", b.dataset.file === r.file));
  body.replaceChildren(h("p", { class: "note", text: "Loading…" }));
  try {
    const data = await api(`/api/report/${encodeURIComponent(r.file)}`);
    body.replaceChildren(markdown(data.markdown));
  } catch (err) { showError(body, err); }
}

/* ---------------------------------------------------------------- upload */
async function loadUploads() {
  const box = $("#upload-list");
  try {
    const docs = await api("/api/uploads");
    box.replaceChildren(docs.length
      ? h("ul", { class: "items" }, docs.map(d => h("li", {}, prose("span", d.title),
          h("span", { class: "detail", text: `${d.matter} · ${d.clauses} clauses · ${d.id}` }))))
      : h("p", { class: "note", text: "Nothing uploaded on your matters yet." }));
  } catch (err) { showError(box, err); }
}

$("#upload-form").addEventListener("submit", e => {
  e.preventDefault();
  const file = $("#upload-file").files[0];
  const box = $("#upload-result");
  if (!file) { showError(box, new Error("Choose a file.")); return; }
  const fd = new FormData();
  fd.append("file", file); fd.append("matter", $("#upload-matter").value);
  run(e.target, box, "Reading the file and screening it for hidden instructions…", async () => {
    const reply = await api("/api/upload", { method: "POST", body: fd });
    const r = await waitJob(reply, box);
    box.replaceChildren(h("div", { class: "score" },
      h("div", { class: "big", text: String(r.clauses) }),
      h("div", {}, h("div", { class: "band", text: "clauses indexed" }), prose("h2", r.title),
        h("div", { class: "note", text: `${r.passages} searchable passages on ${r.matter}. It now appears in Research and Contract review for the people on this matter, and for no one else.` }))),
      hiddenWarning(reply.hidden_text) || "");
    $("#upload-file").value = "";
    loadUploads();
    load();   // the contract lists now include the upload
  });
});

/* ---------------------------------------------------------------- results dashboard (Day 5) */
let DASH = null;
const pct = x => x == null ? "–" : `${Math.round(x * 100)}%`;
const fix2 = x => x == null ? "–" : x.toFixed(2);
const secs = s => s < 1 ? `${Math.round(s * 1000)} ms` : `${s.toFixed(1)} s`;
const SVG_NS = "http://www.w3.org/2000/svg";
function s(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) node.setAttribute(k, v);
  for (const c of children.flat()) if (c != null) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return node;
}

async function loadDashboard() {
  const box = $("#dashboard");
  try { DASH = await api("/api/dashboard"); renderDashboard(box, DASH); }
  catch (err) { DASH = null; showError(box, err); }
}

function tile(value, label, sub) {
  return h("div", { class: "tile" }, h("div", { class: "tile-value", text: value }),
    h("div", { class: "tile-label", text: label }), sub ? h("div", { class: "tile-sub", text: sub }) : null);
}

/* horizontal bars: rows [{label, value, text, highlight, tip}], one scale from 0 to max */
function barChart(title, rows, max, caption) {
  const W = 640, labelW = 170, valueW = 64, rowH = 30, barH = 14, top = 6;
  const H = top + rows.length * rowH;
  const x = v => labelW + (W - labelW - valueW) * (v / max);
  const tip = h("div", { class: "chart-tip", hidden: true });
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", "aria-label": title });
  for (const t of [0, 0.5, 1].map(f => f * max))
    svg.append(s("line", { x1: x(t), x2: x(t), y1: 0, y2: H, class: "chart-grid" }));
  rows.forEach((r, i) => {
    const y = top + i * rowH, w = Math.max(2, x(r.value) - labelW);
    const g = s("g", { class: "chart-row" + (r.highlight ? " hl" : ""), tabindex: "0" },
      s("rect", { x: 0, y, width: W, height: rowH, class: "chart-hit" }),
      s("text", { x: labelW - 10, y: y + rowH / 2 + 4, "text-anchor": "end", class: "chart-label" }, r.label),
      s("path", { d: `M${labelW},${y + (rowH - barH) / 2} h${w - 4} a4,4 0 0 1 4,4 v${barH - 8} a4,4 0 0 1 -4,4 h${-(w - 4)} z`, class: "chart-bar" }),
      s("text", { x: x(r.value) + 8, y: y + rowH / 2 + 4, class: "chart-value" }, r.text));
    const show = ev => {
      tip.replaceChildren(h("strong", { text: r.label }), ...r.tip.map(t => h("div", { text: t })));
      tip.hidden = false;
      const box = svg.getBoundingClientRect();
      tip.style.left = `${Math.min(box.width - 220, Math.max(0, (x(r.value) / W) * box.width - 40))}px`;
      tip.style.top = `${((y + rowH) / H) * box.height + 4}px`;
    };
    g.addEventListener("mouseenter", show); g.addEventListener("focus", show);
    g.addEventListener("mouseleave", () => { tip.hidden = true; }); g.addEventListener("blur", () => { tip.hidden = true; });
    svg.append(g);
  });
  return h("figure", { class: "chart-card" }, h("figcaption", { class: "chart-title", text: title }),
    h("div", { class: "chart-wrap" }, svg, tip), caption ? h("p", { class: "note", text: caption }) : null);
}

function table(head, rows, highlightRow) {
  return h("div", { class: "dash-table-wrap" }, h("table", { class: "dash-table" },
    h("thead", {}, h("tr", {}, head.map((c, i) => h("th", { scope: "col", class: i ? "num" : "", text: c })))),
    h("tbody", {}, rows.map((r, j) => h("tr", { class: highlightRow && highlightRow(j) ? "hl" : "" },
      r.map((c, i) => i ? h("td", { class: "num", text: c }) : h("th", { scope: "row", text: c })))))));
}

const section = (title, lede, ...body) => h("section", { class: "dash-section" },
  h("h2", { text: title }), lede ? h("p", { class: "note", text: lede }) : null, ...body);

function renderDashboard(box, d) {
  const R = d.retrieval, def = R.configs.find(c => c.default), naive = R.configs.find(c => c.config === "naive");
  const L = d.latency, G = d.graph.methods, sec = d.security;
  const graphF1 = G.find(m => m.method === "graph"), vecF1 = G.find(m => m.method === "vector");
  const tiles = h("div", { class: "tiles" },
    tile(pct(def.recall_at_5), "Right passage in the top 5", `app default (${def.label.replace("+ ", "")}); naive search ${pct(naive.recall_at_5)}`),
    tile(String(d.citations.fabricated_shown), "Invented citations shown to a user", `${d.citations.citations_checked} citations checked by code`),
    tile(pct(def.correct_refusals), "Correct refusals", "questions the library cannot answer"),
    tile(fix2(graphF1.f1), "Case-law relationship F1 (graph)", `vector search ${fix2(vecF1.f1)}`),
    tile(`${sec.held}/${sec.attacks}`, "Red-team attacks held", `${sec.weaknesses_fixed} weaknesses found and fixed`),
    L ? tile(secs(L.end_to_end.median), "Research answer, median", `90th percentile ${secs(L.end_to_end.p90)}`) : null,
    L ? tile(`$${L.usd_per_1000.toFixed(2)}`, "Per 1,000 questions (paid tier)", "free tier: $0") : null,
    d.contracts.comparison_planted ? tile(`${d.contracts.comparison_planted.found}/${d.contracts.comparison_planted.of}`, "Planted contract changes found", "version comparison") : null);

  const recall = barChart("Right passage in the top 5 (recall@5), by retrieval setup",
    R.configs.map(c => ({ label: c.label, value: c.recall_at_5, text: pct(c.recall_at_5), highlight: c.default,
      tip: [`MRR@5 ${fix2(c.mrr_at_5)}`, `Statutes ${pct(c.recall_at_5_statute)} · case law ${pct(c.recall_at_5_case_law)}`,
            c.citation_accuracy != null ? `Correct citation ${pct(c.citation_accuracy)}` : "Answer metrics not run",
            c.default ? "The app's default setup" : c.description] })), 1,
    `${R.questions} evaluation questions; each setup adds one step to the one above. Highlighted: the app's default. Query rewrite and HyDE score higher but add a Gemini call before every search.`);
  const retrievalTable = table(["Setup", "Recall@5", "MRR@5", "Correct citation", "Faithful", "Correct refusals", "False refusals"],
    R.configs.map(c => [c.label + (c.default ? " (default)" : ""), pct(c.recall_at_5), fix2(c.mrr_at_5), pct(c.citation_accuracy),
      pct(c.faithfulness), pct(c.correct_refusals), pct(c.false_refusals)]), j => R.configs[j].default);

  const parts = [h("p", { class: "dash-built", text: `Built ${d.built} from the evaluation files (python evaluations/dashboard.py).` }), tiles,
    section("Retrieval and answers", null, recall, retrievalTable),
    section("Citations", "Every citation is checked word for word against its source by code; a citation that fails is removed before the answer is shown.",
      table(["Setup", "Citations", "Verified", "Invented (caught)", "Invented shown"],
        d.citations.configs.map(c => [c.config.replace(/^\d+\.\s*/, ""), String(c.citations), pct(c.verified / c.citations), String(c.fabricated), String(c.fabricated_shown)])),
      h("p", { class: "note", text: `Conclusion check on ${Object.values(d.citations.conclusion_check).reduce((a, b) => a + b, 0)} answers: ` +
        Object.entries(d.citations.conclusion_check).map(([k, v]) => `${k.replace("_", " ")} ${v}`).join(", ") + "." }))];
  if (L) parts.push(section("Speed and cost", `Measured ${L.date} on ${L.questions} questions with the answer cache off. Gemini time is time inside the API call; ` +
      `cost at the list price ($${L.price.input_per_1m} / $${L.price.output_per_1m} per 1M input / output tokens).` +
      (L.gemini_overloaded ? ` Gemini was overloaded that day (${L.gemini_overloaded} calls refused with "high demand" and retried), ` +
        "so the 90th percentiles mostly show Google's load; the medians are the better guide." : ""),
    barChart("Research question, median time per stage", L.stages.map(st => ({ label: st.stage, value: st.median_s, text: secs(st.median_s),
      tip: [`Median ${secs(st.median_s)}`, `90th percentile ${secs(st.p90_s)}`] })), Math.max(...L.stages.map(st => st.median_s)) * 1.15),
    table(["Measure", "Value"], [
      ["End to end, median / 90th percentile", `${secs(L.end_to_end.median)} / ${secs(L.end_to_end.p90)}`],
      ["Gemini calls per question", String(L.calls_per_question)],
      ["Tokens per question (in / out)", `${L.tokens_in.toLocaleString("en")} / ${L.tokens_out.toLocaleString("en")}`],
      ["Cost per question", `$${L.usd_per_question.toFixed(5)}`],
      ["Case-law graph question, median", secs(L.graph_median_s)],
      ["Contract review: Gemini time / cost", `${secs(L.review_gemini_s)} / $${L.review_usd.toFixed(4)}`],
      ...Object.entries(L.retrieval_only).map(([k, v]) => [`Retrieval only, ${k} (100 questions, median)`, secs(v.median)])])));
  parts.push(section("Case law (knowledge graph)", "Relationship questions such as “which judges heard cases on Section 324 PPC”.",
    table(["Method", "Precision", "Recall", "F1"], G.map(m => [m.method, pct(m.precision), pct(m.recall), fix2(m.f1)]), j => G[j].method === "routed"),
    table(["Extracted link (held-out judgments)", "Precision", "Recall"], d.graph.extraction_heldout.map(e => [e.link, pct(e.precision), pct(e.recall)]))));
  const C = d.contracts;
  parts.push(section("Contracts", null,
    table(["Clause classification (28 CUAD types)", "Micro F1", "Macro F1"], C.clause_classification.map(m => [m.model, fix2(m.micro_f1), fix2(m.macro_f1)])),
    table(["Finding 10 clause types in 10 contracts", "Accuracy", "Time per contract"], C.long_context_vs_rag.map(m => [m.method, pct(m.accuracy), `${m.seconds} s`]))));
  parts.push(section("Security (red team)", "Attacks run against the app after the fixes; a limitation is a documented gap, not a failure of a defence.",
    table(["Attack group", "Attacks", "Held", "Broke", "Limitation"], sec.groups.map(g => [g.group.replace(/^[A-Z]\.\s*/, ""), String(g.attacks), String(g.held), String(g.broke), String(g.limitation)]))));
  const B = d.blind_rating;
  if (B) {
    for (const [user, r] of Object.entries(B.raters)) {
      const v = r.results, cols = ["naive", "final"].filter(k => v[k]);
      parts.push(section(`Blind rating of 30 answers (rater: ${user})`, "Rated by a person without knowing which version wrote which answer.",
        table(["", ...cols], [
          ["Acceptable answers", ...cols.map(k => `${v[k].acceptable} / ${v[k].rated}`)],
          ["Correct, questions with an answer", ...cols.map(k => `${v[k].correct_answerable} / ${v[k].answerable}`)],
          ["Correct refusals", ...cols.map(k => `${v[k].refused_no_answer} / ${v[k].no_answer}`)],
          ["Citations fully support the answer", ...cols.map(k => `${v[k].support.yes} / ${v[k].rated}`)],
          ["Usefulness, mean of 1-5", ...cols.map(k => String(v[k].useful))]])));
    }
  } else {
    parts.push(section("Blind rating of 30 answers", "Waiting for the ratings (page 09); the results appear here once they are in."));
  }
  const O = d.ocr.engines;
  parts.push(section("Urdu OCR (scanned laws)", null, table(["Engine", "Character error", "Word error", "Time per page"],
    O.map(e => [e.engine, pct(e.cer), pct(e.wer), secs(e.ms / 1000)]))));
  box.replaceChildren(...parts);
}

/* ---------------------------------------------------------------- blind rating (Day 5) */
let RATING = null, RATING_POS = 0;
const CORRECT_OPTS = [["correct", "Correct"], ["partly", "Partly correct"], ["wrong", "Wrong"], ["refused", "Refused (gave no answer)"]];
const SUPPORT_OPTS = [["yes", "Yes, fully"], ["partly", "Partly"], ["no", "No"], ["none", "No citations"]];

async function loadRating() {
  const root = $("#rating-root");
  root.replaceChildren(h("p", { class: "note", text: "Loading the thirty answers…" }));
  try {
    RATING = await api("/api/rating");
    if (!RATING.complete) {
      const first = RATING.items.findIndex(i => !RATING.ratings[i.id]);
      RATING_POS = first < 0 ? 0 : first;
    }
    renderRating();
  } catch (err) { RATING = null; showError(root, err); }
}

function choice(name, opts, current) {
  return h("div", { class: "choice", role: "radiogroup" }, opts.map(([value, label]) =>
    h("label", { class: "choice-opt" },
      h("input", { type: "radio", name, value, checked: current === value }), h("span", { text: label }))));
}

function renderRating() {
  const items = RATING.items, done = Object.keys(RATING.ratings).length;
  const strip = h("div", { class: "rating-strip", "aria-label": "Answers" }, items.map((it, i) => h("button", {
    type: "button", text: it.id, title: RATING.ratings[it.id] ? "rated" : "not rated yet",
    class: "rating-dot" + (RATING.ratings[it.id] ? " done" : "") + (i === RATING_POS ? " current" : ""),
    onclick: () => { RATING_POS = i; renderRating(); } })));
  const progress = h("p", { class: "rating-progress" }, h("strong", { text: `${done} of ${items.length}` }), " answers rated");
  $("#rating-root").replaceChildren(progress, RATING.complete ? ratingResults() : "", strip, ratingCard(items[RATING_POS], RATING.complete));
}

function ratingCard(it, locked) {
  const r = RATING.ratings[it.id] || {}, a = it.answer, ref = it.reference;
  const answer = h("div", { class: "rating-answer" },
    h("h3", { text: `Answer ${it.id}` + (locked ? ` · written by the ${RATING.key[it.id]} version` : "") }),
    prose("p", a.short_answer, "short"),
    a.explanation ? prose("p", a.explanation, "explain") : null,
    a.citations.length
      ? h("ol", { class: "cites" }, a.citations.map(c => h("li", {}, prose("div", c.source, "cite-ref"), prose("blockquote", c.quote))))
      : h("p", { class: "note", text: "No citations." }));
  const reference = h("aside", { class: "rating-ref" },
    h("h3", { text: "Reference answer" }),
    ref.no_answer ? h("p", { class: "note", text: "The corpus has no answer to this question: refusing (“No sufficient source found”) is the right outcome." }) : null,
    prose("p", ref.answer, "ref-answer"),
    ref.source ? prose("p", ref.source, "cite-ref") : null,
    ref.quote ? prose("blockquote", ref.quote) : null);
  const error = h("p", { class: "error", hidden: true });
  const form = h("form", { class: "rating-form" },
    h("fieldset", { disabled: locked }, h("legend", { text: "1. Compared with the reference, the answer is…" }), choice("correctness", CORRECT_OPTS, r.correctness)),
    h("fieldset", { disabled: locked }, h("legend", { text: "2. Do the quoted sources support what the answer says?" }), choice("support", SUPPORT_OPTS, r.support)),
    h("fieldset", { disabled: locked }, h("legend", { text: "3. How useful would this be to a lawyer starting research? (1 = not at all, 5 = very)" }),
      choice("useful", ["1", "2", "3", "4", "5"].map(n => [n, n]), r.useful ? String(r.useful) : null)),
    h("label", { class: "field" }, h("span", { text: "Note (optional)" }),
      h("input", { type: "text", name: "note", value: r.note || "", maxlength: "500", disabled: locked })),
    error,
    h("div", { class: "rating-actions" },
      h("button", { type: "button", class: "btn-quiet", text: "← Previous", disabled: RATING_POS === 0,
        onclick: () => { RATING_POS--; renderRating(); } }),
      locked
        ? h("button", { type: "button", class: "btn-quiet", text: "Next →", disabled: RATING_POS === RATING.items.length - 1,
            onclick: () => { RATING_POS++; renderRating(); } })
        : h("button", { type: "submit", class: "btn", text: "Save and next" })));
  if (!locked) form.addEventListener("submit", async e => {
    e.preventDefault();
    const fd = new FormData(form);
    const body = { correctness: fd.get("correctness"), support: fd.get("support"), useful: Number(fd.get("useful")), note: fd.get("note") || "" };
    if (!body.correctness || !body.support || !body.useful) { error.textContent = "Answer all three questions first."; error.hidden = false; return; }
    try {
      const reply = await postJSON(`/api/rating/${it.id}`, body);
      RATING.ratings[it.id] = body;
      if (reply.complete) { await loadRating(); window.scrollTo(0, 0); return; }
      const later = RATING.items.findIndex((x, i) => i > RATING_POS && !RATING.ratings[x.id]);
      const any = RATING.items.findIndex(x => !RATING.ratings[x.id]);
      RATING_POS = later >= 0 ? later : (any >= 0 ? any : RATING_POS);
      renderRating();
    } catch (ex) { error.textContent = ex.message; error.hidden = false; }
  });
  return h("article", { class: "rating-card" },
    h("p", { class: "eyebrow", text: `${it.type.replace("_", " ")} question · ${it.language}` }),
    prose("h2", it.question, "rating-question"),
    h("div", { class: "rating-grid" }, answer, reference),
    form);
}

function ratingResults() {
  const res = RATING.results, cols = ["naive", "final"].filter(v => res[v]);
  const row = (label, f) => h("tr", {}, h("th", { scope: "row", text: label }), cols.map(v => h("td", { text: f(res[v]) })));
  return h("section", { class: "rating-results" },
    h("h2", { text: "The versions, revealed" }),
    h("p", { class: "note", text: "naive = vector search only · final = hybrid search with the reranker, the app's default. Both use the same answer model; only retrieval differs. Your ratings are now final." }),
    h("table", { class: "rating-table" },
      h("thead", {}, h("tr", {}, h("th", { text: "" }), cols.map(v => h("th", { scope: "col", text: v })))),
      h("tbody", {},
        row("Acceptable answers", x => `${x.acceptable} / ${x.rated}`),
        row("Correct, questions with an answer", x => `${x.correct_answerable} / ${x.answerable}`),
        row("Partly correct · wrong", x => `${x.correctness.partly} · ${x.correctness.wrong}`),
        row("Correct refusals, no-answer questions", x => `${x.refused_no_answer} / ${x.no_answer}`),
        row("Citations fully support the answer", x => `${x.support.yes} / ${x.rated}`),
        row("Usefulness, mean of 1–5", x => String(x.useful)))),
    h("p", { class: "note", text: "Each answer below now shows which version wrote it." }));
}

/* ---------------------------------------------------------------- audit log (admin) */
let AUDIT_LOG_ITEMS = [];

function renderAuditRows() {
  const tbody = $("#audit-table-body");
  if (!tbody) return;
  const q = ($("#audit-filter") ? $("#audit-filter").value : "").toLowerCase().trim();
  const outcome = $("#audit-outcome-filter") ? $("#audit-outcome-filter").value : "";
  const filtered = AUDIT_LOG_ITEMS.filter(e => {
    if (outcome && e.outcome !== outcome) return false;
    if (q) {
      const line = `${e.ts} ${e.user} ${e.action} ${e.matter || ''} ${e.target || ''} ${e.detail || ''}`.toLowerCase();
      if (!line.includes(q)) return false;
    }
    return true;
  });
  const rows = filtered.map(e => h("tr", { class: e.outcome !== "ok" ? `o-${e.outcome}` : "" },
    h("td", { class: "mono", text: e.ts.replace("T", " ").replace("+00:00", " UTC") }),
    h("td", { text: e.user }),
    h("td", { text: e.action }),
    h("td", { text: e.outcome }),
    h("td", { text: e.matter || "" }),
    h("td", {}, prose("span", [e.target, e.detail].filter(Boolean).join(" · ")))
  ));
  tbody.replaceChildren(...(rows.length ? rows : [h("tr", {}, h("td", { colspan: 6, style: "text-align:center; padding: 24px; color: var(--text-muted);", text: "No audit records matching filter criteria." }))]));
}

async function loadAudit() {
  const box = $("#audit-result");
  box.replaceChildren(h("p", { class: "note", text: "Verifying cryptographic proof chain and loading ledger…" }));
  try {
    const a = await api("/api/admin/audit?n=300");
    AUDIT_LOG_ITEMS = a.log || [];
    const tbody = h("tbody", { id: "audit-table-body" });
    box.replaceChildren(
      h("p", { class: `chain ${a.intact ? "ok" : "bad"}`, text: a.intact
        ? `Chain intact: all ${a.entries} entries verified.`
        : `Chain BROKEN at line ${a.first_broken_line}: an entry was changed or removed.` }),
      h("div", { class: "md" }, h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, ["Time", "User", "Action", "Outcome", "Matter", "Detail"].map(t => h("th", { text: t })))),
        tbody))));
    renderAuditRows();
    const filterInput = $("#audit-filter");
    const outcomeSelect = $("#audit-outcome-filter");
    if (filterInput && !filterInput.dataset.wired) {
      filterInput.dataset.wired = "1";
      filterInput.addEventListener("input", renderAuditRows);
    }
    if (outcomeSelect && !outcomeSelect.dataset.wired) {
      outcomeSelect.dataset.wired = "1";
      outcomeSelect.addEventListener("change", renderAuditRows);
    }
  } catch (err) { showError(box, err); }
}

/* ---------------------------------------------------------------- sign-in and start */
let META = null;

function signOut() {
  TOKEN = null; store.set(null); META = null;
  location.hash = "";
  location.reload();
}
$("#signout").addEventListener("click", signOut);

$("#signin-form").addEventListener("submit", async e => {
  e.preventDefault();
  const err = $("#si-error"); err.hidden = true;
  try {
    const r = await api("/api/login", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: $("#si-user").value, password: $("#si-pass").value }) });
    TOKEN = r.token; store.set(TOKEN);
    $("#si-pass").value = "";
    $("#signin").hidden = true;
    await load();
  } catch (ex) { err.textContent = ex.message; err.hidden = false; }
});

async function load() {
  try { META = await api("/api/meta"); }
  catch (err) { $("#services").textContent = err.message; return; }
  const u = META.user;
  $("#who").hidden = false;
  $("#who-name").textContent = `${u.name} · ${u.role}`;
  $("#who-matters").textContent = META.matters.length ? `Matters: ${META.matters.map(m => m.id).join(", ")}` : "No client matters";
  const avatar = $(".who-avatar");
  if (avatar && u.name) {
    avatar.textContent = u.name.split(" ").map(w => w[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
  }
  $("#nav-audit").hidden = u.role !== "admin";

  $("#services").replaceChildren(
    h("div", { class: "service-item" },
      h("span", { class: "service-dot " + (META.gemini ? "on" : "off") }),
      h("span", { class: "service-label", text: META.gemini ? "Verification Engine: Active" : "Verification Engine: Offline" })
    ),
    h("div", { class: "service-item" },
      h("span", { class: "service-dot " + (META.graph ? "on" : "off") }),
      h("span", { class: "service-label", text: META.graph ? "Precedent Graph: Synced" : "Precedent Graph: Offline" })
    )
  );
  for (const dd of document.querySelectorAll("#graph-ledger dd")) dd.textContent = (META.graph_counts[dd.dataset.k] || 0).toLocaleString("en");

  // contracts grouped by the user's client matters; other matters' contracts are not sent at all
  const sel = $("#review-sample");
  sel.replaceChildren();
  for (const m of META.matters) {
    const list = META.contracts.filter(c => c.matter === m.id);
    if (list.length) sel.append(h("optgroup", { label: `${m.id} · ${m.name} (${m.client})` }, list.map(c => h("option", { value: c.id, text: c.label }))));
  }
  if (!sel.options.length) sel.append(h("option", { value: "", text: "No contracts on your matters" }));
  for (const ms of document.querySelectorAll(".matter-select"))
    ms.replaceChildren(...META.matters.map(m => h("option", { value: m.id, text: `${m.id} · ${m.name}` })));
  
  // Synchronize global matter context in the topbar
  const gSel = $("#global-matter-select");
  if (gSel) {
    gSel.replaceChildren(
      h("option", { value: "", text: "All Matters & Public Corpus" }),
      ...META.matters.map(m => h("option", { value: m.id, text: `${m.id}: ${m.name} (${m.client})` }))
    );
    if (!gSel.dataset.wired) {
      gSel.dataset.wired = "1";
      gSel.addEventListener("change", e => {
        const val = e.target.value;
        for (const ms of document.querySelectorAll(".matter-select")) {
          if (val) ms.value = val;
        }
      });
      for (const ms of document.querySelectorAll(".matter-select")) {
        ms.addEventListener("change", e => {
          if (gSel && e.target.value) gSel.value = e.target.value;
        });
      }
    }
  }

  if (!META.version_pair.length) {
    $("#compare-sample").checked = false; $("#compare-sample").disabled = true; $("#compare-uploads").hidden = false;
  }

  $("#judgment-list").replaceChildren(...META.judgments.map(j => h("option", { value: j.label })));
  const n = META.notice_sample;
  $("#n-sender").value = n.sender || ""; $("#n-recipient").value = n.recipient || ""; $("#n-date").value = n.date || "";
  $("#n-contract").value = n.contract || ""; $("#n-facts").value = (n.facts || []).join("\n"); $("#n-demand").value = n.demand || "";
  $("#n-law").value = (n.legal_questions || []).join("\n");
  const c = META.clause_sample;
  $("#c-title").value = c.title || "";
  $("#c-facts").value = Object.entries(c.facts || {}).map(([k, v]) => `${k}: ${v}`).join("\n");
  $("#c-items").replaceChildren(...META.playbook.map(p => h("label", {}, h("input", { type: "checkbox", value: p.id, checked: (c.items || []).includes(p.id) }), p.title)));

  $("#report-list").replaceChildren(...META.reports.map(r => h("button", { type: "button", "data-file": r.file, text: r.title, onclick: () => openReport(r) })));
  showView();
}

function initTheme() {
  const saved = localStorage.getItem("la-theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", saved);
  const btn = $("#theme-toggle");
  if (btn) {
    const label = $("#theme-label");
    if (label) label.textContent = saved === "dark" ? "Light" : "Dark";
    btn.addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme") || "light";
      const next = cur === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("la-theme", next);
      if (label) label.textContent = next === "dark" ? "Light" : "Dark";
    });
  }
}

function initAutoExpandTextareas() {
  document.querySelectorAll("textarea").forEach(tx => {
    const adjust = () => {
      tx.style.height = "auto";
      tx.style.height = Math.min(Math.max(tx.scrollHeight, 56), 260) + "px";
    };
    tx.addEventListener("input", adjust);
    adjust();
  });
}

function initDropzones() {
  document.querySelectorAll("input[type=file]").forEach(input => {
    const parent = input.closest(".field") || input.parentElement;
    if (!parent || parent.dataset.dropzone) return;
    parent.dataset.dropzone = "1";
    parent.classList.add("dropzone");
    ["dragenter", "dragover"].forEach(evt => {
      parent.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); parent.classList.add("dragover"); });
    });
    ["dragleave", "drop"].forEach(evt => {
      parent.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); parent.classList.remove("dragover"); });
    });
    parent.addEventListener("drop", e => {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  });
}

function start() {
  initTheme();
  initAutoExpandTextareas();
  initDropzones();
  for (const sel of ["#ask-q", "#graph-q"]) {
    const el = $(sel);
    if (el) el.addEventListener("keydown", e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        el.form.requestSubmit();
      }
    });
  }
  exampleButtons($("#ask-examples"), RESEARCH_EXAMPLES, $("#ask-q"), $("#ask-form"));
  exampleButtons($("#graph-examples"), GRAPH_EXAMPLES, $("#graph-q"), $("#graph-form"));
  if (!TOKEN) { $("#signin").hidden = false; $("#si-user").focus(); return; }
  showView();
  load();
}
start();
