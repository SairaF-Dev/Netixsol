"""
Assemble the Hugging Face Space in build/hf_space/: the code, the Space Dockerfile and README, and only the
data the web app reads (allowlist below). Nothing secret is copied: no .env, no demo-password file, no audit
log, no uploads; secrets are set in the Space settings.

Run:  python deploy/build_space.py
Then (after `hf auth login`):  hf upload <user>/<space> build/hf_space --repo-type space
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "hf_space"

CODE = ["src", "web", "requirements-server.txt"]
DATA = [                                           # what the web app reads at run time
    "data/indices/vstore_legal.sqlite3",           # vector search (section-level passages)
    "data/indices/bm25_legal.pkl",                 # keyword search
    "data/structured",                             # statutes, judgments, contracts (citation checks, briefs, review)
    "data/graph",                                  # judgment list, authorities for briefs
    "data/llm_cache",                              # saved Gemini answers: demo questions cost no quota
    "data/contracts/versions",                     # comparison sample pair
    "data/contracts/drafting",                     # drafting samples
    "data/playbook",                               # firm playbook
    "data/security/users.json",                    # accounts (password hashes only)
    "data/security/matters.json",                  # client matters
]
NEVER = {".env", "initial_passwords.txt", "audit.jsonl", "jobs.sqlite3", "owners.json"}   # must not ship


def copy(rel: str) -> None:
    src, dst = ROOT / rel, OUT / rel
    if not src.exists():
        sys.exit(f"missing: {rel}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.lock", "*.tmp"))
    else:
        shutil.copy2(src, dst)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for rel in CODE + DATA:
        copy(rel)
    (OUT / "evaluations").mkdir()
    for pattern in ("*.md", "blind_rating_*.json"):        # the Evaluation and Blind Rating pages
        for report in (ROOT / "evaluations").glob(pattern):
            shutil.copy2(report, OUT / "evaluations" / report.name)
    for name in ("Dockerfile", "README.md"):
        shutil.copy2(ROOT / "deploy" / "hf_space" / name, OUT / name)
    leaked = [p for p in OUT.rglob("*") if p.name in NEVER]
    if leaked:
        shutil.rmtree(OUT)
        sys.exit(f"refusing to build: {leaked}")
    files = [p for p in OUT.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"{OUT}: {len(files)} files, {size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
