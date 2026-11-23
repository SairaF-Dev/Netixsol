"""
Pack the data the web app needs but git does not hold (search index, saved Gemini answers, accounts, matters)
into build/codespace_data.tar.gz, to copy into a GitHub Codespace:

    python deploy/codespaces/pack_data.py
    gh codespace cp -c <codespace> build/codespace_data.tar.gz remote:/tmp/codespace_data.tar.gz
    gh codespace ssh -c <codespace> -- "cd /workspaces/Netixsol/Week12/AI_Legal_Assistant && tar -xzf /tmp/codespace_data.tar.gz && bash deploy/codespaces/start.sh"

Same allowlist as the Hugging Face bundle (deploy/build_space.py): no .env, no demo-password file, no audit log,
no uploads - secrets are Codespaces secrets, and the repository is public, so none of this goes into git.
"""

import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # deploy/
from build_space import DATA, NEVER, ROOT                       # noqa: E402

OUT = ROOT / "build" / "codespace_data.tar.gz"
SKIP = ("__pycache__", ".lock", ".tmp", ".pyc")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for rel in DATA:
        path = ROOT / rel
        if not path.exists():
            sys.exit(f"missing: {rel}")
        files += [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    files = [p for p in files if not any(s in p.name or s in p.parts for s in SKIP)]
    leaked = [p for p in files if p.name in NEVER]
    if leaked:
        sys.exit(f"refusing to pack: {leaked}")
    with tarfile.open(OUT, "w:gz") as tar:
        for p in files:
            tar.add(p, arcname=p.relative_to(ROOT).as_posix())
    print(f"{OUT}: {len(files)} files, {sum(p.stat().st_size for p in files) / 1e6:.0f} MB before compression, "
          f"{OUT.stat().st_size / 1e6:.0f} MB packed")


if __name__ == "__main__":
    main()
