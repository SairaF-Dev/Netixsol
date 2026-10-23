import os
import sys
import argparse
from pathlib import Path

# Ensure src/ is on sys.path
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

TRAIN_FILE = DATA_DIR / "train" / "train.jsonl"
VAL_FILE = DATA_DIR / "val" / "val.jsonl"
GOLDEN_FILE = DATA_DIR / "golden" / "golden_test.jsonl"
DATASET_CARD_FILE = PROJECT_ROOT / "DATASET_CARD.md"


def upload_dataset(
    repo_id: str,
    token: str = None,
    private: bool = True,
    dry_run: bool = False
) -> None:
    print("=" * 65)
    print("HUGGING FACE HUB DATASET PUBLISHING")
    print("=" * 65)
    print(f"Target Repository : {repo_id}")
    print(f"Visibility        : {'Private' if private else 'Public'}")
    print(f"Dry Run Mode      : {dry_run}")

    # Verify local artifacts exist
    files_to_upload = [
        (TRAIN_FILE, "data/train.jsonl"),
        (VAL_FILE, "data/val.jsonl"),
        (GOLDEN_FILE, "data/golden_test.jsonl"),
        (DATASET_CARD_FILE, "README.md")
    ]

    for local_path, remote_path in files_to_upload:
        if not local_path.exists():
            raise FileNotFoundError(f"Required artifact not found: {local_path}. Please complete pipeline tasks first.")
        size_kb = local_path.stat().st_size / 1024
        print(f"  * [READY] {local_path.name} ({size_kb:.1f} KB) -> {remote_path}")

    if dry_run:
        print("\n[INFO] Dry-run completed successfully. All artifacts are verified and staged for publishing.")
        print(f"[INFO] To execute live upload, specify your token via HF_TOKEN or --token and run without --dry-run.")
        print("=" * 65)
        return

    # Authentication resolution
    hf_token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        print("\n[ERROR] Hugging Face token not provided.")
        print("Please provide it via --token <YOUR_HF_TOKEN> or set the HF_TOKEN environment variable.")
        print("Example: set HF_TOKEN=hf_xxxxxxxxxxxxxxxxx")
        sys.exit(1)

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("[ERROR] huggingface_hub package is not installed. Install via: pip install huggingface-hub")
        sys.exit(1)

    api = HfApi(token=hf_token)

    print(f"\n[INFO] Creating or verifying private dataset repo '{repo_id}'...")
    try:
        create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            private=private,
            token=hf_token,
            exist_ok=True
        )
        print(f"[SUCCESS] Repository '{repo_id}' ready on Hugging Face Hub.")
    except Exception as e:
        print(f"[WARNING] Repository creation check notice: {e}")

    print(f"[INFO] Uploading dataset splits and dataset card to '{repo_id}'...")
    for local_path, remote_path in files_to_upload:
        print(f"  Uploading {local_path.name} -> {remote_path}...")
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=remote_path,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"Upload {remote_path} (Day 1 Pipeline Release)",
            token=hf_token
        )

    repo_url = f"https://huggingface.co/datasets/{repo_id}"
    print("\n" + "=" * 65)
    print("DATASET PUBLISHED SUCCESSFULLY")
    print("=" * 65)
    print(f"Dataset URL: {repo_url}")
    print(f"Access     : Private repository accessible to authorized client personnel")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload Zarya Banking Dataset to Hugging Face Hub")
    parser.add_argument("--repo-id", type=str, required=True, help="HF Repo ID (e.g., 'your-username/zarya-banking-dataset')")
    parser.add_argument("--token", type=str, default=None, help="Hugging Face access token with write permissions")
    parser.add_argument("--public", action="store_true", help="Set repository to public (defaults to private)")
    parser.add_argument("--dry-run", action="store_true", help="Validate files and staging without performing actual network upload")

    args = parser.parse_args()
    upload_dataset(
        repo_id=args.repo_id,
        token=args.token,
        private=not args.public,
        dry_run=args.dry_run
    )

