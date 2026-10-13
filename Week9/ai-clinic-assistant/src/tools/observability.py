"""
Observability & Tracing Engine for AI Clinic Assistant
Tracks execution steps, tool calls, latency, cost estimation, and emergency escalations.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClinicObservability")

class ObservabilityTracer:
    def __init__(self):
        self.traces: List[Dict[str, Any]] = []

    def start_trace(self, session_id: str, patient_id: str, input_text: str) -> str:
        trace_id = f"TRC-{int(time.time()*1000)}"
        trace_entry = {
            "trace_id": trace_id,
            "session_id": session_id,
            "patient_id": patient_id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "input_text": input_text,
            "steps": [],
            "tool_calls": [],
            "escalations": [],
            "metrics": {
                "total_latency_ms": 0,
                "estimated_tokens": 0,
                "estimated_cost_usd": 0.0
            },
            "status": "IN_PROGRESS"
        }
        self.traces.append(trace_entry)
        logger.info(f"[Trace {trace_id}] Started for Session {session_id}, Patient {patient_id}")
        return trace_id

    def log_agent_step(self, trace_id: str, agent_name: str, action: str, output: Any, latency_ms: float, tokens_used: int = 50):
        trace = self._get_trace(trace_id)
        if not trace:
            return
        
        step_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": agent_name,
            "action": action,
            "output": output,
            "latency_ms": round(latency_ms, 2),
            "tokens_used": tokens_used
        }
        trace["steps"].append(step_data)
        trace["metrics"]["total_latency_ms"] += latency_ms
        trace["metrics"]["estimated_tokens"] += tokens_used
        # Approx $0.0005 per 1k tokens benchmark
        trace["metrics"]["estimated_cost_usd"] += (tokens_used / 1000.0) * 0.0005
        
        logger.info(f"[Trace {trace_id}] Agent: {agent_name} | Action: {action} | Latency: {latency_ms:.1f}ms")

    def log_tool_call(self, trace_id: str, mcp_server: str, tool_name: str, args: Dict[str, Any], result: Any, status: str = "SUCCESS"):
        trace = self._get_trace(trace_id)
        if not trace:
            return

        tool_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mcp_server": mcp_server,
            "tool_name": tool_name,
            "args": args,
            "result": result,
            "status": status
        }
        trace["tool_calls"].append(tool_data)
        logger.info(f"[Trace {trace_id}] MCP Tool: {mcp_server}.{tool_name} [{status}]")

    def log_escalation(self, trace_id: str, level: str, reason: str):
        trace = self._get_trace(trace_id)
        if not trace:
            return

        escalation_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "reason": reason
        }
        trace["escalations"].append(escalation_data)
        logger.warning(f"[Trace {trace_id}] Escalation Triggered! Level: {level} | Reason: {reason}")

    def end_trace(self, trace_id: str, final_response: str, status: str = "COMPLETED") -> Dict[str, Any]:
        trace = self._get_trace(trace_id)
        if not trace:
            return {}

        trace["end_time"] = datetime.now(timezone.utc).isoformat()
        trace["final_response"] = final_response
        trace["status"] = status
        trace["metrics"]["total_latency_ms"] = round(trace["metrics"]["total_latency_ms"], 2)
        trace["metrics"]["estimated_cost_usd"] = round(trace["metrics"]["estimated_cost_usd"], 6)

        logger.info(f"[Trace {trace_id}] Completed. Total Latency: {trace['metrics']['total_latency_ms']}ms | Cost: ${trace['metrics']['estimated_cost_usd']}")
        return trace

    def get_summary_report(self) -> Dict[str, Any]:
        total_traces = len(self.traces)
        if total_traces == 0:
            return {"total_traces": 0}

        total_latency = sum(t["metrics"]["total_latency_ms"] for t in self.traces)
        total_tokens = sum(t["metrics"]["estimated_tokens"] for t in self.traces)
        total_cost = sum(t["metrics"]["estimated_cost_usd"] for t in self.traces)
        escalations_count = sum(len(t["escalations"]) for t in self.traces)

        return {
            "total_traces": total_traces,
            "avg_latency_ms": round(total_latency / total_traces, 2),
            "total_tokens_used": total_tokens,
            "total_estimated_cost_usd": round(total_cost, 6),
            "total_escalations": escalations_count,
            "traces": self.traces
        }

    def _get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        for t in self.traces:
            if t["trace_id"] == trace_id:
                return t
        return None

# Global tracer instance
tracer = ObservabilityTracer()
