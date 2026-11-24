"""
Day 5: latency and cost of the main paths, measured with the Gemini cache OFF (every call is a real call).

  research  20 evaluation questions (fixed seed; statute, case law and no-answer; all three languages) through
            the app's research path (config "rerank"): retrieval -> answer -> citation check (code) ->
            conclusion check -> one redraft when the check fails. Each stage is timed separately.
  retrieval all 100 evaluation questions, retrieval only, for the configurations that need no LLM
            (naive, section, hybrid, rerank) - no Gemini calls.
  graph     the 6 case-law example questions of the app (linked questions need no LLM).
  review    2 contracts through the playbook review.

Gemini time is the time inside the API call (call_log of the client), not the free-tier spacing between calls
(LLM_MIN_INTERVAL); end-to-end = sum of the stages, i.e. what a paid key without spacing would see.
Cost = tokens x list price of the answer model (Gemini 3.5 Flash-Lite, standard tier, checked 2026-11-24:
$0.30 per 1M input tokens, $2.50 per 1M output tokens incl. thinking). On the free tier the cost is 0.

Run:  python evaluations/latency_cost.py      (about 60 Gemini calls)
      python evaluations/latency_cost.py --only research,review   (rerun some parts, keep the rest from the JSON;
      useful when Gemini was overloaded - 503 "high demand" - during a run, which inflates the Gemini times)
-> evaluations/latency_cost.json, evaluations/latency_cost_report.md
"""

import json
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PRICE_IN, PRICE_OUT = 0.30, 2.50          # USD per 1M tokens
PRICE_DATE = "2026-11-24"
OUT_JSON = ROOT / "evaluations" / "latency_cost.json"
OUT_MD = ROOT / "evaluations" / "latency_cost_report.md"
SEED = 2026
PLAN = {"statute": 8, "case_law": 6, "no_answer": 6}
GRAPH_QUESTIONS = [
    "Which judges sat on the cases in the corpus that refer to Section 324 of the Pakistan Penal Code?",
    "Which judges presided over proceedings referencing Article 129 of the Qanun-e-Shahadat Order, 1984?",
    "Which judges heard cases involving Section 7 of the Anti-Terrorism Act, 1997?",
    "Which Supreme Court judgments in the corpus refer to Article 212 of the Constitution?",
    "Which sections of the Pakistan Penal Code came up in cases heard by Justice Malik Shahzad Ahmad Khan?",
    "Which precedent is cited the most in the corpus?",
]
REVIEW_CONTRACTS = ["CONT_SYNTH_001", "CUAD_REAL_001"]


def usd(calls: List[Dict]) -> float:
    return sum(c["input_tokens"] for c in calls) * PRICE_IN / 1e6 + sum(c["output_tokens"] for c in calls) * PRICE_OUT / 1e6


def stats(values: List[float]) -> Dict:
    values = sorted(values)
    if not values:
        return {}
    p90 = values[min(len(values) - 1, int(round(0.9 * (len(values) - 1))))]
    return {"n": len(values), "median": round(statistics.median(values), 3), "p90": round(p90, 3),
            "mean": round(statistics.mean(values), 3), "max": round(values[-1], 3)}


def new_calls(llm, since: int) -> List[Dict]:
    return llm.call_log[since:]


def research(questions: List[Dict]) -> Dict:
    from src.llm.gemini_client import GeminiClient
    from src.rag.answer import CitedAnswer, NO_SOURCE, answer_question, is_refusal
    from src.rag.conclusion_check import check_conclusion
    from src.rag.pipeline import DEFAULT_CONFIG, _retriever
    from src.rag.verify import verify_answer

    t = time.perf_counter()
    retriever = _retriever(DEFAULT_CONFIG)
    retriever.retrieve("warm-up: punishment for theft", top_k=5)      # loads the models and indices once
    load_s = time.perf_counter() - t
    llm = GeminiClient(use_cache=False)
    rows = []
    for q in questions:
        row = {"id": q["id"], "type": q["type"], "language": q["language"]}
        t = time.perf_counter(); results = retriever.retrieve(q["question"], top_k=5); row["retrieval_s"] = time.perf_counter() - t
        n = len(llm.call_log)
        draft = answer_question(llm, q["question"], results)
        row["answer_calls"] = new_calls(llm, n)
        t = time.perf_counter(); verified, _ = verify_answer(draft, results); row["verify_s"] = time.perf_counter() - t
        n = len(llm.call_log)
        check = check_conclusion(llm, q["question"], verified, results)
        row["check_calls"] = new_calls(llm, n)
        row["redraft_calls"] = []
        if check.verdict == "not_supported":
            n = len(llm.call_log)
            second = answer_question(llm, q["question"], results, review_note=check.issue)
            verified, _ = verify_answer(second, results)
            check = check_conclusion(llm, q["question"], verified, results)
            row["redraft_calls"] = new_calls(llm, n)
            if check.verdict == "not_supported":
                verified = CitedAnswer(short_answer=NO_SOURCE)
        row["refused"] = is_refusal(verified)
        calls = row["answer_calls"] + row["check_calls"] + row["redraft_calls"]
        row["gemini_s"] = sum(c["seconds"] for c in calls)
        row["total_s"] = row["retrieval_s"] + row["verify_s"] + row["gemini_s"]
        row["calls"] = len(calls)
        row["input_tokens"] = sum(c["input_tokens"] for c in calls)
        row["output_tokens"] = sum(c["output_tokens"] for c in calls)
        row["usd"] = usd(calls)
        rows.append(row)
        print(f"  {q['id']:10s} {row['total_s']:5.1f}s  {row['calls']} calls  ${row['usd']:.5f}", flush=True)
    stage = lambda key: stats([r[key] for r in rows])
    gem = lambda key: stats([sum(c["seconds"] for c in r[key]) for r in rows if r[key]])
    return {"overloaded": llm.overloaded, "config": DEFAULT_CONFIG, "questions": len(rows), "load_s": round(load_s, 1),
            "retrieval_s": stage("retrieval_s"), "answer_s": gem("answer_calls"), "verify_s": stage("verify_s"),
            "check_s": gem("check_calls"), "redraft_s": gem("redraft_calls"),
            "redrafts": sum(bool(r["redraft_calls"]) for r in rows), "total_s": stage("total_s"),
            "calls_per_question": round(statistics.mean(r["calls"] for r in rows), 2),
            "input_tokens_per_question": round(statistics.mean(r["input_tokens"] for r in rows)),
            "output_tokens_per_question": round(statistics.mean(r["output_tokens"] for r in rows)),
            "usd_per_question": statistics.mean(r["usd"] for r in rows),
            "by_type": {t: stats([r["total_s"] for r in rows if r["type"] == t]) for t in PLAN},
            "rows": [{k: v for k, v in r.items() if not k.endswith("_calls")} for r in rows]}


def retrieval_only(questions: List[Dict]) -> Dict:
    from src.rag.pipeline import _retriever
    out = {}
    for config in ("naive", "section", "hybrid", "rerank"):
        retriever = _retriever(config)
        retriever.retrieve("warm-up: punishment for theft", top_k=5)
        times = []
        for q in questions:
            t = time.perf_counter(); retriever.retrieve(q["question"], top_k=5); times.append(time.perf_counter() - t)
        out[config] = stats(times)
        print(f"  retrieval {config:8s} median {out[config]['median'] * 1000:.0f} ms", flush=True)
    return out


def graph() -> Dict:
    from src.graph.graphrag import GraphRAG
    from src.llm.gemini_client import GeminiClient
    llm = GeminiClient(use_cache=False)
    g = GraphRAG(llm=llm)
    g.answer("Which precedent is cited the most in the corpus?")           # warm-up: connection
    rows = []
    for q in GRAPH_QUESTIONS:
        n = len(llm.call_log)
        t = time.perf_counter(); res = g.answer(q); s = time.perf_counter() - t
        calls = llm.call_log[n:]
        rows.append({"question": q, "method": res["method"], "items": len(res["items"]), "seconds": s,
                     "calls": len(calls), "usd": usd(calls)})
        print(f"  graph {s:5.2f}s {res['method']} {len(res['items'])} items", flush=True)
    return {"seconds": stats([r["seconds"] for r in rows]), "llm_calls": sum(r["calls"] for r in rows),
            "usd_per_question": statistics.mean(r["usd"] for r in rows), "rows": rows}


def review() -> Dict:
    from src.contracts.review import review_contract
    from src.llm.gemini_client import GeminiClient
    llm = GeminiClient(use_cache=False)
    rows = []
    for cid in REVIEW_CONTRACTS:
        n = len(llm.call_log)
        t = time.perf_counter(); res = review_contract(cid, "the Client", llm); s = time.perf_counter() - t
        calls = llm.call_log[n:]
        gemini_s = sum(c["seconds"] for c in calls)
        # wall time includes the free-tier spacing only if there was more than one call; report both
        rows.append({"contract": cid, "findings": len(res["findings"]), "wall_s": s, "gemini_s": gemini_s,
                     "calls": len(calls), "input_tokens": sum(c["input_tokens"] for c in calls),
                     "output_tokens": sum(c["output_tokens"] for c in calls), "usd": usd(calls)})
        print(f"  review {cid} {s:5.1f}s {len(calls)} calls ${rows[-1]['usd']:.5f}", flush=True)
    return {"overloaded": llm.overloaded, "rows": rows, "usd_per_review": statistics.mean(r["usd"] for r in rows)}


def report(data: Dict) -> None:
    r, ms = data["research"], lambda s: f"{s * 1000:.0f} ms"
    sec = lambda s: f"{s:.1f} s"
    lines = [
        "# Latency and cost (Day 5)", "",
        f"Measured on {data['date']} on {data['machine']}, with the Gemini answer cache **off** (every call real). "
        "Gemini time is the time inside the API call; the free tier's spacing between calls is excluded, so the "
        "figures are what a paid key would see. Cost uses the list price of Gemini 3.5 Flash-Lite (standard tier, "
        f"checked {PRICE_DATE}): ${PRICE_IN:.2f} per 1M input and ${PRICE_OUT:.2f} per 1M output tokens. On the free tier "
        "the cost is 0, and a question asked before costs nothing (answers are cached).", "",
        f"## Research question (app default: `{r['config']}`), {r['questions']} questions", "",
        "| Stage | Median | 90th percentile |", "|---|---|---|",
        f"| Retrieval (hybrid search + reranker, on the server) | {ms(r['retrieval_s']['median'])} | {ms(r['retrieval_s']['p90'])} |",
        f"| Answer (Gemini) | {sec(r['answer_s']['median'])} | {sec(r['answer_s']['p90'])} |",
        f"| Citation check (code) | {ms(r['verify_s']['median'])} | {ms(r['verify_s']['p90'])} |",
        f"| Conclusion check (Gemini) | {sec(r['check_s']['median'])} | {sec(r['check_s']['p90'])} |",
    ]
    if r["redrafts"]:
        lines.append(f"| Redraft + second check, {r['redrafts']} of {r['questions']} questions | {sec(r['redraft_s']['median'])} | {sec(r['redraft_s']['p90'])} |")
    lines += [
        f"| **End to end** | **{sec(r['total_s']['median'])}** | **{sec(r['total_s']['p90'])}** |", "",
        f"* Gemini calls per question: {r['calls_per_question']}; tokens per question: {r['input_tokens_per_question']:,} in, "
        f"{r['output_tokens_per_question']:,} out.",
        f"* **Cost per question: ${r['usd_per_question']:.5f}** - about **${1000 * r['usd_per_question']:.2f} per 1,000 questions**.",
    ] + ([f"* **Gemini was overloaded during this run**: {data['gemini_503_retries']} calls were refused with 503 \"high demand\" "
          "and retried. The waits for those retries are not counted, but the calls that did go through were slow, so the "
          "90th percentiles mostly show Google's load that day; the medians are the better guide."]
         if data.get("gemini_503_retries") else []) + [
        f"* One-time start: loading the models and the index takes {r['load_s']} s after the server starts.",
        "* By question type (end to end, median): " + ", ".join(
            f"{t.replace('_', ' ')} {sec(v['median'])}" for t, v in r["by_type"].items() if v) + ".", "",
        "## Retrieval only, all 100 evaluation questions (no Gemini)", "",
        "| Configuration | Median | 90th percentile |", "|---|---|---|",
    ]
    for config, s in data["retrieval"].items():
        lines.append(f"| {config} | {ms(s['median'])} | {ms(s['p90'])} |")
    g = data["graph"]
    lines += ["", "The reranker costs the most time but is what lifts recall@5 from 0.70 to 0.78 and MRR from 0.56 to "
              "0.73 (`rag_comparison_report.md`). It reads 30 (question, passage) pairs of up to 512 tokens each on "
              "the CPU. Tried on this laptop: fewer threads is slower (14-18 s); the 8-bit model file published with the "
              "model saves about 1 s but changes the order of the top 5; ONNX Runtime's memory arena saves about 4 s but "
              "makes memory grow with every search (5.4 GB after 100, which is why it is off). A server CPU, or a GPU, "
              "is the real fix. Query rewriting and HyDE score higher still (recall@5 0.94) but add a Gemini call before "
              "the search - one more wait of several seconds and one more request per question against the free daily "
              "quota - which is why the app's default is `rerank`.", "",
              f"## Case-law graph, {len(g['rows'])} questions", "",
              f"Median {ms(g['seconds']['median'])}, 90th percentile {ms(g['seconds']['p90'])} (Neo4j AuraDB over the internet). "
              f"Gemini calls: {g['llm_calls']} (linked questions run a ready-made query; no LLM).", "",
              "| Question | Method | Results | Time |", "|---|---|---|---|"]
    for row in g["rows"]:
        lines.append(f"| {row['question']} | {row['method']} | {row['items']} | {ms(row['seconds'])} |")
    v = data["review"]
    lines += ["", "## Contract review", "", "| Contract | Playbook findings | Gemini calls | Gemini time | Tokens in / out | Cost |",
              "|---|---|---|---|---|---|"]
    for row in v["rows"]:
        lines.append(f"| {row['contract']} | {row['findings']} | {row['calls']} | {sec(row['gemini_s'])} | "
                     f"{row['input_tokens']:,} / {row['output_tokens']:,} | ${row['usd']:.5f} |")
    lines += ["", f"Cost per review: about ${v['usd_per_review']:.4f}.", "",
              "## Free tier in practice", "",
              f"The free key allows about 500 requests a day. At {r['calls_per_question']} calls per research question that is "
              f"about {int(500 / r['calls_per_question'])} new questions a day (repeated questions are free), or mixed with "
              "reviews and drafts somewhat fewer. The free tier also limits requests per minute, which the app respects "
              "by spacing calls 4 s apart - on the free key a research question therefore takes a few seconds longer "
              "than the figures above."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    import argparse
    import platform
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="retrieval,research,graph,review",
                        help="comma-separated parts to run; the others are kept from the last JSON")
    parts = set(parser.parse_args().only.split(","))
    questions = [json.loads(l) for l in open(ROOT / "evaluations" / "rag_eval_set.jsonl", encoding="utf-8")]
    rng = random.Random(SEED)
    sample = [q for kind, n in PLAN.items() for q in rng.sample([x for x in questions if x["type"] == kind], n)]
    data = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}
    data.update({"date": time.strftime("%Y-%m-%d"), "machine": f"{platform.system()} laptop, {platform.processor() or 'CPU'}",
                 "price": {"input_per_1m": PRICE_IN, "output_per_1m": PRICE_OUT, "checked": PRICE_DATE}})
    steps = {"retrieval": ("retrieval only (100 questions)", lambda: retrieval_only(questions)),
             "research": ("research (20 questions, cache off)", lambda: research(sample)),
             "graph": ("graph", graph), "review": ("review", review)}
    for name, (label, run) in steps.items():
        if name in parts or name not in data:
            print(label)
            data[name] = run()
    data["gemini_503_retries"] = sum(data[k].get("overloaded", 0) for k in ("research", "review"))
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    report(data)
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()
