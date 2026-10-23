"""
monitoring.py
=============
Week 10 Day 5 - Task 2: Production Telemetry & PII-Masked Logging Engine

Handles:
1. Structured JSON logging of user prompts, assistant outputs, latency, and guardrail triggers.
2. Automated PII masking before writing to persistent disk storage (data/audit_logs.jsonl).
3. Telemetry metrics calculation (average latency, throughput, guardrail trigger frequency).
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Workspace Paths
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_FILE = DATA_DIR / "audit_logs.jsonl"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.guardrails import ZaryaGuardrailsPipeline


class ProductionLogger:
    """
    Enterprise audit logger for banking interactions ensuring zero PII persistence.
    """
    def __init__(self, log_file: Path = LOGS_FILE):
        self.log_file = log_file
        self.guardrails = ZaryaGuardrailsPipeline()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_turn(
        self,
        customer_id: str,
        user_query: str,
        assistant_response: str,
        latency_ms: float,
        guardrail_status: str,
        action: str = "PROCESSED",
        ticket_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Masks PII and writes a single structured interaction log.
        """
        masked_query, query_pii_counts = self.guardrails.mask_pii_for_logging(user_query)
        masked_resp, _ = self.guardrails.mask_pii_for_logging(assistant_response)

        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "customer_id": customer_id,
            "query": masked_query,
            "response": masked_resp,
            "latency_ms": round(latency_ms, 2),
            "guardrail_status": guardrail_status,
            "action": action,
            "ticket_id": ticket_id,
            "pii_detected": sum(query_pii_counts.values()) > 0,
            "pii_breakdown": query_pii_counts
        }

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        return log_entry

    def get_telemetry_summary(self, max_records: int = 500) -> Dict[str, Any]:
        """
        Computes operational telemetry from recent audit logs.
        """
        if not self.log_file.exists():
            return {"total_records": 0, "avg_latency_ms": 0.0, "guardrail_interceptions": 0}

        records = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

        records = records[-max_records:]
        if not records:
            return {"total_records": 0, "avg_latency_ms": 0.0, "guardrail_interceptions": 0}

        latencies = [r["latency_ms"] for r in records]
        interceptions = sum(1 for r in records if r["guardrail_status"] != "PASSED")
        pii_maskings = sum(1 for r in records if r.get("pii_detected", False))

        return {
            "total_records": len(records),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
            "guardrail_interceptions": interceptions,
            "pii_redactions": pii_maskings,
            "interception_rate": round(interceptions / len(records) * 100.0, 1)
        }


def main():
    print("=" * 70)
    print("ZARYA BANK AI: AUDIT LOGGING & TELEMETRY VERIFICATION")
    print("=" * 70)
    logger = ProductionLogger()

    # Log 3 sample production events
    print("[TEST 1/2] Logging customer interaction with sensitive PII...")
    raw_query = "Mera CNIC 42201-1234567-1 hai, card 4532-1234-5678-9012 gum ho gaya block karein."
    raw_resp = "Ji, aap ki card block request darj kar li gayi hai."
    entry1 = logger.log_turn("CUST-1092", raw_query, raw_resp, 42.5, "PASSED", "AUTO_TICKET_CREATED", "ZAR-20261022-1092")
    print("  * Raw Input    :", raw_query)
    print("  * Stored Input :", entry1["query"])
    print("  * PII Masked   :", entry1["pii_detected"], entry1["pii_breakdown"])

    print("\n[TEST 2/2] Reading Operational Telemetry Summary...")
    telemetry = logger.get_telemetry_summary()
    print(json.dumps(telemetry, indent=2))
    print("\n" + "=" * 70)
    print("MONITORING MODULE OPERATIONAL")
    print("=" * 70)


if __name__ == "__main__":
    main()

