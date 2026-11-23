"""Scoring for the blind rating of 30 answers (Day 5) - shared by the web app (page 09) and
evaluations/blind_rating.py, which builds the set and writes the report."""

from statistics import mean

SYSTEMS = {"naive": "naive", "rerank": "final"}          # Day 2 run -> name shown after the reveal
CORRECTNESS = ("correct", "partly", "wrong", "refused")
SUPPORT = ("yes", "partly", "no", "none")


def acceptable(item: dict, rating: dict) -> bool:
    """A good outcome: a correct answer, or a refusal where the corpus has no answer."""
    if item["reference"]["no_answer"]:
        return rating["correctness"] == "refused"
    return rating["correctness"] == "correct"


def summarise(items: list, key: dict, ratings: dict) -> dict:
    """Per version: answers rated, acceptable %, correctness counts, support counts, mean usefulness."""
    by_id = {i["id"]: i for i in items}
    out = {}
    for system in SYSTEMS.values():
        rated = [(by_id[i], r) for i, r in ratings.items() if i in by_id and key.get(i) == system]
        if not rated:
            continue
        count = lambda field, value: sum(r[field] == value for _, r in rated)
        answered = [(it, r) for it, r in rated if not it["reference"]["no_answer"]]
        out[system] = {
            "rated": len(rated),
            "acceptable": sum(acceptable(it, r) for it, r in rated),
            "correctness": {v: count("correctness", v) for v in CORRECTNESS},
            "support": {v: count("support", v) for v in SUPPORT},
            "useful": round(mean(r["useful"] for _, r in rated), 2),
            "useful_answerable": round(mean(r["useful"] for _, r in answered), 2) if answered else None,
            "correct_answerable": sum(r["correctness"] == "correct" for _, r in answered),
            "answerable": len(answered),
            "refused_no_answer": sum(r["correctness"] == "refused" for it, r in rated if it["reference"]["no_answer"]),
            "no_answer": sum(it["reference"]["no_answer"] for it, _ in rated),
        }
    return out
