"""
Unit test for Observability & Tracing Engine.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from src.tools.observability import ObservabilityTracer

class TestObservabilityTracer(unittest.TestCase):
    def setUp(self):
        self.tracer = ObservabilityTracer()

    def test_full_trace_lifecycle(self):
        trace_id = self.tracer.start_trace(session_id="SESS-100", patient_id="PAT-0012", input_text="Severe chest pain")
        self.assertTrue(trace_id.startswith("TRC-"))

        self.tracer.log_agent_step(
            trace_id=trace_id,
            agent_name="TriageAgent",
            action="evaluate_symptoms",
            output="EMERGENCY_REDFLAG",
            latency_ms=120.5,
            tokens_used=150
        )

        self.tracer.log_tool_call(
            trace_id=trace_id,
            mcp_server="notifications",
            tool_name="send_emergency_alert",
            args={"patient_id": "PAT-0012", "symptom": "chest pain"},
            result={"status": "sent"}
        )

        self.tracer.log_escalation(
            trace_id=trace_id,
            level="EMERGENCY",
            reason="Red flag cardiac symptom detected: chest pain"
        )

        summary = self.tracer.end_trace(trace_id=trace_id, final_response="Emergency alert dispatched to 1122 and ER duty doctor.")
        self.assertEqual(summary["status"], "COMPLETED")
        self.assertEqual(summary["metrics"]["estimated_tokens"], 150)
        self.assertEqual(len(summary["escalations"]), 1)

        report = self.tracer.get_summary_report()
        self.assertEqual(report["total_traces"], 1)
        self.assertEqual(report["total_escalations"], 1)

if __name__ == "__main__":
    unittest.main()

