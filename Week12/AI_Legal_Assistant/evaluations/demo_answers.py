"""
Day 2 deliverable: demo of 5 answers with verified citations.

Five questions covering the cases the system must handle: the brief's example
(Roman Urdu, Contract Act s. 23), a Penal Code question, an Urdu-script
question, a case-law question, and a question whose answer is not in the corpus.
Each answer goes through the full pipeline (retrieval -> Gemini -> code
verification of every citation); the output is written to
evaluations/demo_verified_answers.md exactly as `main.py --ask` prints it.

Run:  python -m evaluations.demo_answers [--config rerank]
"""

import argparse
import json
from pathlib import Path

from src.rag.pipeline import answer_with_citations, format_answer

OUT = Path("evaluations/demo_verified_answers.md")
QUESTIONS = [
    ("Example from the brief (Roman Urdu, statute)", "Agar consideration unlawful ho to kya contract void hai?"),
    ("Penal Code (English)", "What is the punishment for qatl-e-amd under the Pakistan Penal Code?"),
    ("Urdu script (statute)", "اگر معاہدے میں خلاف ورزی کی صورت میں جرمانے کی رقم طے ہو تو کیا عدالت اس سے زیادہ رقم دلا سکتی ہے؟"),
    ("Case law (English)", "What did the Supreme Court say about the duty of police when a court dismisses a pre-arrest bail application?"),
    ("Not in the corpus (must refuse)", "What are the registration requirements for a private limited company under the Companies Act, 2017?"),
]


def main(config: str) -> None:
    blocks, results = [], []
    for title, question in QUESTIONS:
        result = answer_with_citations(question, config=config)
        results.append(result)
        verified = len(result["citations"])
        removed = len(result["removed_citations"])
        blocks.append(f"## {title}\n\nVerified citations shown: {verified}; removed by verification: {removed}.\n\n"
                      f"```text\n{format_answer(result)}\n```\n")
    OUT.write_text(f"""# Demo: 5 answers with verified citations (Day 2)

Pipeline: retrieval configuration `{config}` → Gemini answer (short answer, explanation, citations
with quotes) → code verification of every citation (`src/rag/verify.py`: passage exists, Act/case
matches, section/paragraph exists in the corpus, quote appears verbatim). Unverified citations are
removed; an answer with none left becomes "No sufficient source found". Then a conclusion check
(`src/rag/conclusion_check.py`) asks whether the conclusion actually follows from the retrieved passages;
an answer that fails is drafted once more with the reviewer's note, and withheld if it fails again.

""" + "\n".join(blocks), encoding="utf-8")
    (OUT.with_suffix(".json")).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="rerank")
    main(parser.parse_args().config)
