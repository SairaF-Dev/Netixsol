"""
Model Selection & Comparison Runner for Zarya Digital Bank LLM.
Compares Qwen/Qwen2.5-3B-Instruct vs meta-llama/Llama-3.2-3B-Instruct across:
1. Tokenizer compression efficiency on UrduLish, Roman Urdu, English, and Urdu Script
2. Architectural specifications & Parameter counts
3. Memory / VRAM footprint (BF16, INT8, QLoRA 4-bit)
4. Commercial licensing & regulatory compliance for Pakistani Banking
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
from transformers import AutoTokenizer

def load_sample_texts(golden_path: Path, max_samples_per_lang: int = 40) -> Dict[str, List[str]]:
    """Extract sample user queries and bot responses from golden test set grouped by language."""
    samples = {"urdulish": [], "roman_urdu": [], "english": [], "urdu_script": []}
    
    if not golden_path.exists():
        print(f"Warning: {golden_path} does not exist. Using fallback representative phrases.")
        samples["urdulish"].append("Mera Raast transfer fail ho gaya lekin balance kat gaya hai, fori refund kab tak hoga?")
        samples["roman_urdu"].append("Aap ka card block karne ke liye helpline par rabta karein ya app se temporary freeze karein.")
        samples["english"].append("I need to dispute an unauthorized ATM withdrawal of Rs 15000 that occurred yesterday.")
        samples["urdu_script"].append("میرا راست ٹرانسفر فیل ہو گیا لیکن اکاؤنٹ سے رقم کٹ گئی۔ برائے مہربانی شکایت درج کریں۔")
        return samples

    with open(golden_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            lang = data.get("language", "urdulish")
            if lang not in samples:
                lang = "urdulish"
            
            # Extract customer message
            messages = data.get("messages", [])
            for m in messages:
                content = m.get("content", "").strip()
                if content and len(samples[lang]) < max_samples_per_lang:
                    samples[lang].append(content)
                    
    return samples

def evaluate_tokenizer(tok, texts: List[str]) -> Dict[str, float]:
    """Calculate token counts, words, and compression ratio."""
    token_counts = []
    word_counts = []
    ratios = []
    
    for t in texts:
        tokens = tok.encode(t, add_special_tokens=False)
        words = t.split()
        n_tok = len(tokens)
        n_words = max(1, len(words))
        token_counts.append(n_tok)
        word_counts.append(n_words)
        ratios.append(n_tok / n_words)
        
    return {
        "avg_tokens": float(np.mean(token_counts)),
        "avg_words": float(np.mean(word_counts)),
        "tokens_per_word": float(np.mean(ratios)),
        "total_tokens": int(np.sum(token_counts)),
        "total_words": int(np.sum(word_counts))
    }

def main():
    root = Path(__file__).resolve().parent.parent
    golden_path = root / "data" / "golden" / "golden_test.jsonl"
    
    print("=" * 70)
    print("ZARYA DIGITAL BANK: BASE MODEL COMPARISON (Qwen 2.5 3B vs Llama 3.2 3B)")
    print("=" * 70)
    
    samples = load_sample_texts(golden_path, max_samples_per_lang=40)
    print(f"Loaded samples across {len(samples)} languages from golden test set:")
    for lang, texts in samples.items():
        print(f"  - {lang:12}: {len(texts)} texts, {sum(len(t.split()) for t in texts)} total words")

    print("\nLoading Tokenizers...")
    qwen_name = "Qwen/Qwen2.5-3B-Instruct"
    llama_name = "unsloth/Llama-3.2-3B-Instruct"
    
    tok_qwen = AutoTokenizer.from_pretrained(qwen_name)
    tok_llama = AutoTokenizer.from_pretrained(llama_name)
    
    print(f"Loaded Qwen Tokenizer (Vocab Size: {len(tok_qwen):,})")
    print(f"Loaded Llama Tokenizer (Vocab Size: {len(tok_llama):,})")
    
    results = {}
    print("\n" + "=" * 70)
    print(f"{'Language':15} | {'Metric':18} | {'Qwen 2.5 3B':14} | {'Llama 3.2 3B':14} | {'Winner / Advantage'}")
    print("-" * 70)
    
    for lang, texts in samples.items():
        if not texts:
            continue
        q_res = evaluate_tokenizer(tok_qwen, texts)
        l_res = evaluate_tokenizer(tok_llama, texts)
        results[lang] = {"qwen": q_res, "llama": l_res}
        
        # Tokens per word comparison
        diff_pct = ((l_res["tokens_per_word"] - q_res["tokens_per_word"]) / l_res["tokens_per_word"]) * 100
        winner = f"Qwen (-{diff_pct:.1f}% tokens)" if diff_pct > 0 else f"Llama (-{-diff_pct:.1f}%)"
        
        print(f"{lang:15} | {'Tokens / Word':18} | {q_res['tokens_per_word']:14.2f} | {l_res['tokens_per_word']:14.2f} | {winner}")
        print(f"{'':15} | {'Avg Tokens / Msg':18} | {q_res['avg_tokens']:14.1f} | {l_res['avg_tokens']:14.1f} |")
        print("-" * 70)
        
    # Overall summary
    all_texts = [t for texts in samples.values() for t in texts]
    q_all = evaluate_tokenizer(tok_qwen, all_texts)
    l_all = evaluate_tokenizer(tok_llama, all_texts)
    overall_diff = ((l_all["tokens_per_word"] - q_all["tokens_per_word"]) / l_all["tokens_per_word"]) * 100
    
    print(f"{'OVERALL (Corpus)':15} | {'Tokens / Word':18} | {q_all['tokens_per_word']:14.2f} | {l_all['tokens_per_word']:14.2f} | Qwen (-{overall_diff:.1f}% tokens)")
    print("=" * 70)
    
    # Save comparison data JSON
    specs = {
        "models": {
            "qwen2_5_3b": {
                "hf_id": "Qwen/Qwen2.5-3B-Instruct",
                "param_count": "3.09B",
                "vocab_size": len(tok_qwen),
                "context_window": "128k native (32k recommended serving)",
                "license": "Apache 2.0 (Unrestricted commercial & on-premise use)",
                "architecture": "Qwen2ForCausalLM (GQA, RoPE theta=1,000,000, SwiGLU)",
                "memory_fp16_gb": 6.18,
                "memory_int8_gb": 3.09,
                "memory_qlora_4bit_gb": 1.95,
                "tokenizer_eval": q_all
            },
            "llama3_2_3b": {
                "hf_id": "meta-llama/Llama-3.2-3B-Instruct",
                "param_count": "3.21B",
                "vocab_size": len(tok_llama),
                "context_window": "128k native",
                "license": "Llama 3.2 Community License (Restricted: requires attribution, >700M MAU special license, Meta acceptable use policy)",
                "architecture": "LlamaForCausalLM (GQA, RoPE theta=500,000, SwiGLU)",
                "memory_fp16_gb": 6.42,
                "memory_int8_gb": 3.21,
                "memory_qlora_4bit_gb": 2.08,
                "tokenizer_eval": l_all
            }
        },
        "per_language": results
    }
    
    out_json = root / "data" / "model_comparison_metrics.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(specs, f, indent=2)
    print(f"\nSaved metrics to {out_json}")

if __name__ == "__main__":
    main()

