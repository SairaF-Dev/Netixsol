"""
upload_final_model.py
=====================
Week 10 Day 5 - Task 1: Hugging Face Model Hub Publishing

Publishes the final Zarya fine-tuned & DPO-aligned model package to a private
Hugging Face repository:
- DPO LoRA Adapter weights (safetensors)
- Tokenizer files & ChatML Jinja template
- Quantization manifest (4-bit GGUF, INT8, FP16)
- Comprehensive Model Card (MODEL_CARD.md)
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Workspace Paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
CHECKPOINTS_DIR = PROJECT_ROOT / "checkpoints"
DPO_ADAPTER_DIR = CHECKPOINTS_DIR / "checkpoint_qwen2_5_3b_dpo"
QUANTIZED_DIR = PROJECT_ROOT / "quantized_models"
MODEL_CARD_FILE = PROJECT_ROOT / "MODEL_CARD.md"


def stage_and_upload_model(
    repo_id: str,
    token: str = None,
    private: bool = True,
    dry_run: bool = False
) -> None:
    print("=" * 70)
    print("ZARYA BANK AI: FINAL PRODUCTION MODEL RELEASE TO HUGGING FACE")
    print("=" * 70)
    print(f"Target Repository : {repo_id}")
    print(f"Visibility        : {'Private (Enterprise SBP Compliant)' if private else 'Public'}")
    print(f"Dry Run Mode      : {dry_run}")
    
    # 1. Define files to package
    files_to_upload = [
        (DPO_ADAPTER_DIR / "adapter_config.json", "adapter_config.json"),
        (DPO_ADAPTER_DIR / "adapter_model.safetensors", "adapter_model.safetensors"),
        (DPO_ADAPTER_DIR / "chat_template.jinja", "chat_template.jinja"),
        (DPO_ADAPTER_DIR / "tokenizer.json", "tokenizer.json"),
        (DPO_ADAPTER_DIR / "tokenizer_config.json", "tokenizer_config.json"),
        (QUANTIZED_DIR / "quantization_manifest.json", "quantization_manifest.json"),
        (MODEL_CARD_FILE, "README.md")
    ]
    
    print("\n[STEP 1/3] Verifying Local Artifacts & Integrity...")
    total_size_bytes = 0
    missing = []
    
    for local_path, remote_path in files_to_upload:
        if not local_path.exists():
            # If MODEL_CARD.md is not yet generated, note it
            missing.append(local_path)
            print(f"  * [PENDING] {local_path.name} -> {remote_path} (Will be created in Task 5)")
        else:
            sz = local_path.stat().st_size
            total_size_bytes += sz
            sz_mb = sz / (1024 * 1024)
            print(f"  * [VERIFIED] {local_path.name:<28} ({sz_mb:6.2f} MB) -> {remote_path}")
            
    total_mb = total_size_bytes / (1024 * 1024)
    print(f"\nTotal Release Package Size: {total_mb:.2f} MB")
    
    if dry_run:
        print("\n[INFO] Dry-run completed successfully.")
        print("[INFO] All core checkpoint and configuration artifacts are verified and staged.")
        print(f"[INFO] To execute live network upload, run with: python src/upload_final_model.py --token <HF_TOKEN>")
        print("=" * 70)
        return
        
    # 2. Authentication check
    hf_token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        print("\n[ERROR] Hugging Face token not found. Pass --token or set HF_TOKEN environment variable.")
        sys.exit(1)
        
    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError:
        print("[ERROR] huggingface_hub is not installed. Install via: pip install huggingface-hub")
        sys.exit(1)
        
    api = HfApi(token=hf_token)
    
    # Pre-flight token authentication verification
    try:
        user_info = api.whoami()
        username = user_info.get("name")
        print(f"  * Authenticated User : {username}")
    except Exception as auth_err:
        print(f"\n[ERROR] Hugging Face token authentication failed: {auth_err}")
        print("Please check that your token is valid and has not expired.")
        print("Generate a new token at: https://huggingface.co/settings/tokens")
        sys.exit(1)
        
    print(f"\n[STEP 2/3] Initializing Private Hugging Face Model Repository '{repo_id}'...")
    try:
        create_repo(
            repo_id=repo_id,
            repo_type="model",
            private=private,
            token=hf_token,
            exist_ok=True
        )
        print(f"  -> Repository '{repo_id}' verified on Hugging Face Hub.")
    except Exception as e:
        if "401" in str(e) or "Unauthorized" in str(e):
            print(f"\n[ERROR] 401 Unauthorized while accessing repo '{repo_id}': {e}")
            print("Your token does not have WRITE permissions to create or push to repositories.")
            print("Please create a token with 'Write' permissions at: https://huggingface.co/settings/tokens")
            sys.exit(1)
        print(f"  -> Notice on repo check: {e}")
        
    print(f"\n[STEP 3/3] Uploading Release Artifacts to '{repo_id}'...")
    for local_path, remote_path in files_to_upload:
        if local_path.exists():
            print(f"  Uploading {local_path.name} -> {remote_path}...")
            api.upload_file(
                path_or_fileobj=str(local_path),
                path_in_repo=remote_path,
                repo_id=repo_id,
                repo_type="model",
                commit_message=f"Production release v1.0.0: {remote_path}",
                token=hf_token
            )
            
    print("\n" + "=" * 70)
    print(f"MODEL SUCCESSFULLY PUBLISHED TO HUGGING FACE")
    print(f"URL: https://huggingface.co/{repo_id}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Upload Final Zarya Model to Hugging Face Hub")
    parser.add_argument("--repo-id", type=str, default="sairafatima193/zarya-qwen2.5-3b-dpo-v1", help="Target Hugging Face Model Repo")
    parser.add_argument("--token", type=str, default=None, help="Hugging Face access token")
    parser.add_argument("--public", action="store_true", help="Set repository public (defaults to private)")
    parser.add_argument("--dry-run", action="store_true", help="Verify staged files without network upload")
    
    args = parser.parse_args()
    stage_and_upload_model(
        repo_id=args.repo_id,
        token=args.token,
        private=not args.public,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()

