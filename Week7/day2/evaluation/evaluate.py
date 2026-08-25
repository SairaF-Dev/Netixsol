"""
Hallucination Evaluation — Task 5

Runs the 20 questions in questions.json through the RAG pipeline and
measures:

  Grounding Rate     = % of ANSWERABLE questions where the top retrieved
                        chunk actually matches the expected_source
                        (i.e. the agent found the right evidence)
  Retrieval Accuracy = same signal, reported per-question with the
                        actual top chunk_id, so you can eyeball misses
  Hallucination Rate = % of UNANSWERABLE questions where the pipeline
                        confidently returns an answer near/above the
                        similarity threshold instead of refusing
                        (this is the "made something up" case)

Run: python evaluation/evaluate.py
Produces: evaluation/results.json + prints a summary table
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag"))

from pipeline import build_pipeline, answer_query

REFUSAL_PHRASE = "confirm karke aapko bataana hoga"


def load_questions():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "questions.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate():
    retriever, n_docs, n_chunks = build_pipeline()
    questions = load_questions()

    results = []
    for q in questions:
        answer, retrieved = answer_query(retriever, q["question"], top_k=1)
        top_chunk = retrieved[0]
        refused = REFUSAL_PHRASE in answer

        if q["answerable"]:
            # Grounded correctly if top chunk's doc_id matches expected source AND it didn't refuse
            grounded = (top_chunk["chunk_id"].startswith(q["expected_source"])) and not refused
            hallucinated = False  # hallucination only scored on unanswerable questions
        else:
            grounded = None
            # Hallucination = it answered (didn't refuse) on a question it shouldn't be able to answer
            hallucinated = not refused

        results.append({
            "id": q["id"],
            "question": q["question"],
            "answerable": q["answerable"],
            "expected_source": q.get("expected_source"),
            "top_chunk_id": top_chunk["chunk_id"],
            "top_score": round(top_chunk["score"], 3),
            "refused": refused,
            "grounded": grounded,
            "hallucinated": hallucinated,
        })

    answerable = [r for r in results if r["answerable"]]
    unanswerable = [r for r in results if not r["answerable"]]

    grounding_rate = sum(1 for r in answerable if r["grounded"]) / len(answerable) * 100
    hallucination_rate = sum(1 for r in unanswerable if r["hallucinated"]) / len(unanswerable) * 100
    retrieval_accuracy = grounding_rate  # same metric here since retrieval IS the grounding signal

    summary = {
        "total_questions": len(questions),
        "answerable_questions": len(answerable),
        "unanswerable_questions": len(unanswerable),
        "grounding_rate_pct": round(grounding_rate, 1),
        "retrieval_accuracy_pct": round(retrieval_accuracy, 1),
        "hallucination_rate_pct": round(hallucination_rate, 1),
    }

    out = {"summary": summary, "results": results}
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("=== Hallucination Evaluation Summary ===")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"\nFull results written to {out_path}\n")

    print(f"{'ID':4} {'Answerable':11} {'Grounded':9} {'Hallucinated':13} {'Top Chunk'}")
    for r in results:
        print(f"{r['id']:4} {str(r['answerable']):11} {str(r['grounded']):9} {str(r['hallucinated']):13} {r['top_chunk_id']}")

    return out


if __name__ == "__main__":
    evaluate()
