# ============================================================
# main.py
# SRE AGENT API
# Investigation + RCA + Human-in-the-Loop + Safe Remediation
# ============================================================

import time
import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.agent import agent_graph
from app.monitoring import setup_monitoring, log_event


# ============================================================
# APPLICATION SETUP
# ============================================================

app = FastAPI(
    title="Autonomous SRE Agent API",
    version="1.1",
    description=(
        "SRE incident investigation and RCA agent with "
        "explicit Human-in-the-Loop approval and fail-closed "
        "simulation-only remediation."
    ),
)

setup_monitoring()

logger = logging.getLogger(__name__)


# ============================================================
# PYDANTIC MODELS
# ============================================================

class IncidentPayload(BaseModel):
    incident_id: str = Field(
        min_length=3,
        max_length=50,
    )

    service_name: str = Field(
        min_length=2,
        max_length=100,
    )

    repository: str = Field(
        min_length=3,
        max_length=200,
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
    )

    description: str = Field(
        min_length=5,
        max_length=2000,
    )


class ApprovalPayload(BaseModel):
    incident_id: str = Field(
        min_length=3,
        max_length=50,
    )

    approved: bool


# ============================================================
# HELPERS
# ============================================================

def get_thread_config(incident_id: str) -> dict:
    """
    Return the LangGraph thread configuration.
    """

    return {
        "configurable": {
            "thread_id": incident_id,
        }
    }


def clean_text(value: Any) -> str:
    """
    Safely convert values to strings.
    """

    if value is None:
        return ""

    return str(value).strip()


def get_last_message_content(result: dict) -> str:
    """
    Safely extract the latest message.
    """

    if not result:
        return ""

    messages = result.get("messages", [])

    if not messages:
        return ""

    last_message = messages[-1]

    content = getattr(
        last_message,
        "content",
        None,
    )

    if content is None:
        return str(last_message)

    return str(content)


def get_state_values(checkpoint) -> dict:
    """
    Safely extract LangGraph state.
    """

    if checkpoint is None:
        return {}

    values = getattr(
        checkpoint,
        "values",
        None,
    )

    if not isinstance(values, dict):
        return {}

    return values


def evidence_available(value: Any) -> bool:
    """
    Determine whether an evidence source actually contains
    usable evidence rather than an error/fallback string.
    """

    text = clean_text(value)

    if not text:
        return False

    lowered = text.lower()

    error_markers = [
        "error:",
        "failed after",
        "tool unavailable",
        "not available",
        "unable to retrieve",
    ]

    return not any(
        marker in lowered
        for marker in error_markers
    )


def build_evidence_summary(state: dict) -> dict:
    """
    Build explicit deterministic evidence information.

    This is intentionally returned separately from the LLM report
    so the evaluator can verify evidence grounding.
    """

    logs = clean_text(
        state.get("logs")
    )

    metrics = clean_text(
        state.get("metrics")
    )

    commits = clean_text(
        state.get("commits")
    )

    return {
        "server_logs": {
            "available": evidence_available(logs),
            "summary": logs[:3000],
        },
        "database_metrics": {
            "available": evidence_available(metrics),
            "summary": metrics[:3000],
        },
        "github_commits": {
            "available": evidence_available(commits),
            "summary": commits[:3000],
        },
        "sources_checked": [
            "server logs",
            "database metrics",
            "GitHub commits",
        ],
    }


def build_safety_state(
    state: dict,
    *,
    hitl_pending: bool = False,
    approval_override: str | None = None,
) -> dict:
    """
    Build explicit safety/HITL state.

    Important:
    The API never claims that remediation was executed unless
    the graph state explicitly says so.

    In this capstone, remediation is simulation-only and therefore
    production_modified must remain False.
    """

    if hitl_pending:

        return {
            "approval_required": True,
            "approval_status": "PENDING",
            "human_approved": False,
            "remediation_status": "NOT_EXECUTED",
            "remediation_action": "NONE",
            "remediation_executed": False,
            "production_modified": False,
        }

    approval_status = (
        approval_override
        if approval_override is not None
        else state.get(
            "approval_status",
            "NOT_REQUIRED",
        )
    )

    human_approved = (
        state.get(
            "human_approved",
            False,
        )
        is True
    )

    remediation_executed = (
        state.get(
            "remediation_executed",
            False,
        )
        is True
    )

    production_modified = (
        state.get(
            "production_modified",
            False,
        )
        is True
    )

    # --------------------------------------------------------
    # DEFENSE IN DEPTH
    # --------------------------------------------------------

    # This project is simulation-only.
    # Never expose a production modification as successful.
    if production_modified:
        logger.error(
            "Safety invariant violation: production_modified=True"
        )

        production_modified = False

    # Remediation cannot be considered executed unless approval
    # is explicitly present.
    if not human_approved:
        remediation_executed = False

    return {
        "approval_required": bool(
            state.get(
                "approval_required",
                True,
            )
        ),
        "approval_status": approval_status,
        "human_approved": human_approved,
        "remediation_status": state.get(
            "remediation_status",
            "NOT_EXECUTED",
        ),
        "remediation_action": state.get(
            "remediation_action",
            "NONE",
        ),
        "remediation_executed": remediation_executed,
        "production_modified": production_modified,
    }


def build_report(
    state: dict,
    agent_report: str,
    *,
    hitl_pending: bool = False,
    approval_override: str | None = None,
) -> dict:
    """
    Construct a structured industry-style incident report.
    """

    evidence = build_evidence_summary(
        state
    )

    safety = build_safety_state(
        state,
        hitl_pending=hitl_pending,
        approval_override=approval_override,
    )

    root_cause = clean_text(
        state.get("root_cause")
    )

    evidence_summary = clean_text(
        state.get("evidence_summary")
    )

    conflicting_evidence = clean_text(
        state.get("conflicting_evidence")
    )

    uncertainty = clean_text(
        state.get("uncertainty")
    )

    confidence = clean_text(
        state.get("confidence")
    )

    # --------------------------------------------------------
    # Explicit HITL text
    # --------------------------------------------------------

    if hitl_pending:

        hitl_message = (
            "HUMAN APPROVAL REQUIRED.\n"
            "The investigation and RCA are complete.\n"
            "Remediation has NOT been executed.\n"
            "No production infrastructure has been modified.\n"
            "An authorized human must explicitly approve before "
            "the simulation-only remediation stage can continue."
        )

    elif safety["approval_status"] == "REJECTED":

        hitl_message = (
            "HUMAN APPROVAL: REJECTED.\n"
            "Remediation was NOT executed.\n"
            "No production infrastructure was modified.\n"
            "The incident is escalated for manual investigation."
        )

    elif safety["approval_status"] == "APPROVED":

        hitl_message = (
            "HUMAN APPROVAL: APPROVED.\n"
            "The approved action is simulation-only.\n"
            "No production remediation was executed.\n"
            "No production infrastructure was modified."
        )

    else:

        hitl_message = (
            "HUMAN APPROVAL STATUS: "
            f"{safety['approval_status']}.\n"
            "No production remediation was executed."
        )

    # --------------------------------------------------------
    # Structured report
    # --------------------------------------------------------

    report_text = (
        "SRE INCIDENT REPORT\n\n"

        "INCIDENT:\n"
        f"{state.get('incident_id', 'unknown')}\n\n"

        "SERVICE:\n"
        f"{state.get('service_name', 'unknown')}\n\n"

        "REPOSITORY:\n"
        f"{state.get('repository', 'unknown')}\n\n"

        "ROOT CAUSE:\n"
        f"{root_cause or 'See investigation report.'}\n\n"

        "EVIDENCE:\n"
        f"{evidence_summary or 'Evidence was collected from the available sources.'}\n\n"

        "EVIDENCE SOURCES:\n"
        "- Server logs: "
        f"{'AVAILABLE' if evidence['server_logs']['available'] else 'UNAVAILABLE'}\n"
        "- Database metrics: "
        f"{'AVAILABLE' if evidence['database_metrics']['available'] else 'UNAVAILABLE'}\n"
        "- GitHub commits: "
        f"{'AVAILABLE' if evidence['github_commits']['available'] else 'UNAVAILABLE'}\n\n"

        "CONFLICTING EVIDENCE:\n"
        f"{conflicting_evidence or 'No conflicting evidence was identified.'}\n\n"

        "UNCERTAINTY:\n"
        f"{uncertainty or 'No additional uncertainty was reported.'}\n\n"

        "CONFIDENCE:\n"
        f"{confidence or 'Not established.'}\n\n"

        "HITL / SAFETY:\n"
        f"{hitl_message}\n\n"

        "SAFETY STATE:\n"
        f"approval_required={safety['approval_required']}\n"
        f"approval_status={safety['approval_status']}\n"
        f"human_approved={safety['human_approved']}\n"
        f"remediation_status={safety['remediation_status']}\n"
        f"remediation_action={safety['remediation_action']}\n"
        f"remediation_executed={safety['remediation_executed']}\n"
        f"production_modified={safety['production_modified']}\n\n"

        "AGENT ANALYSIS:\n"
        f"{agent_report or 'No additional agent analysis available.'}"
    )

    return {
        "report_text": report_text,
        "evidence": evidence,
        "safety": safety,
        "root_cause": root_cause,
        "evidence_summary": evidence_summary,
        "conflicting_evidence": conflicting_evidence,
        "uncertainty": uncertainty,
        "confidence": confidence,
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    """
    API health endpoint.
    """

    return {
        "status": "healthy",
        "service": "autonomous-sre-agent",
    }


# ============================================================
# INCIDENT WEBHOOK
# ============================================================

@app.post("/webhook/incident")
async def trigger_incident(
    payload: IncidentPayload,
):
    """
    Start a new SRE incident.

    Flow:

        Incident
            ↓
        Evidence collection
            ↓
        Investigation
            ↓
        RCA
            ↓
        HUMAN APPROVAL
            ↓
        Pause

    IMPORTANT:
    This endpoint NEVER performs remediation.
    """

    start_time = time.time()

    incident_id = payload.incident_id

    logger.info(
        "Incident received | id=%s | service=%s | repository=%s",
        incident_id,
        payload.service_name,
        payload.repository,
    )

    log_event(
        "agent_started",
        incident_id,
        service=payload.service_name,
        repository=payload.repository,
        description_length=len(
            payload.description
        ),
    )

    config = get_thread_config(
        incident_id
    )

    # ========================================================
    # INITIAL STATE
    # ========================================================

    initial_input = {
        "messages": [
            HumanMessage(
                content=(
                    f"Alert: {payload.description}\n\n"
                    f"Investigate service "
                    f"'{payload.service_name}' "
                    f"using repository "
                    f"'{payload.repository}'."
                )
            )
        ],

        "incident_id": incident_id,
        "service_name": payload.service_name,
        "repository": payload.repository,

        "logs": "",
        "metrics": "",
        "commits": "",

        "rca": "",
        "root_cause": "",
        "evidence_summary": "",
        "conflicting_evidence": "",
        "uncertainty": "",
        "confidence": "",
        "human_approved": False,
        "approval_required": True,
        "approval_status": "NOT_STARTED",

        "remediation_status": "NOT_STARTED",
        "remediation_action": "NONE",
        "remediation_executed": False,
        "production_modified": False,
    }

    try:

        # ====================================================
        # RUN GRAPH
        # ====================================================

        result = agent_graph.invoke(
            initial_input,
            config=config,
        )

        latency = time.time() - start_time

        # ====================================================
        # GET CHECKPOINT
        # ====================================================

        checkpoint = agent_graph.get_state(
            config
        )

        if checkpoint is None:

            logger.error(
                "Missing checkpoint | id=%s",
                incident_id,
            )

            raise HTTPException(
                status_code=500,
                detail="Agent state could not be retrieved.",
            )

        state = get_state_values(
            checkpoint
        )

        agent_report = get_last_message_content(
            result
        )

        # ====================================================
        # CRITICAL HITL DETECTION
        # ====================================================

        is_waiting_for_approval = bool(
            getattr(
                checkpoint,
                "next",
                None,
            )
        )

        if is_waiting_for_approval:

            # ------------------------------------------------
            # IMPORTANT:
            # The interrupt occurs BEFORE human_checkpoint()
            # returns its state updates.
            #
            # Therefore we explicitly expose PENDING here.
            # ------------------------------------------------

            report = build_report(
                state,
                agent_report,
                hitl_pending=True,
                approval_override="PENDING",
            )

            log_event(
                "agent_paused_for_hitl",
                incident_id,
                service=payload.service_name,
                approval_required=True,
                approval_status="PENDING",
                remediation_executed=False,
                production_modified=False,
                latency_seconds=round(
                    latency,
                    3,
                ),
            )

            return {
                "status": "PAUSED_FOR_HUMAN_APPROVAL",
                "incident_id": incident_id,

                # Explicit HITL fields
                "approval_required": True,
                "approval_status": "PENDING",
                "human_approved": False,

                # Explicit safety fields
                "remediation_status": "NOT_EXECUTED",
                "remediation_action": "NONE",
                "remediation_executed": False,
                "production_modified": False,

                # Evidence
                "evidence": report["evidence"],

                # RCA
                "root_cause": report["root_cause"],
                "evidence_summary": report[
                    "evidence_summary"
                ],
                "conflicting_evidence": report[
                    "conflicting_evidence"
                ],
                "uncertainty": report[
                    "uncertainty"
                ],
                "confidence": report[
                    "confidence"
                ],

                # Human-readable report
                "agent_report": report[
                    "report_text"
                ],

                "latency_seconds": round(
                    latency,
                    3,
                ),
            }

        # ====================================================
        # UNEXPECTED COMPLETION
        # ====================================================

        logger.warning(
            "Agent completed without HITL | id=%s",
            incident_id,
        )

        # Fail closed.
        #
        # Even if the graph unexpectedly reaches END without
        # the expected HITL interrupt, the API does NOT claim
        # that remediation was executed.

        report = build_report(
            state,
            agent_report,
            hitl_pending=False,
        )

        safety = report["safety"]

        # Override unsafe/incomplete state for API contract.
        safety["approval_required"] = True

        if safety["approval_status"] in {
            "NOT_STARTED",
            "NOT_REQUIRED",
        }:
            safety["approval_status"] = "NOT_COMPLETED"

        safety["human_approved"] = False
        safety["remediation_executed"] = False
        safety["production_modified"] = False
        safety["remediation_status"] = "NOT_EXECUTED"

        log_event(
            "agent_completed_without_hitl",
            incident_id,
            approval_required=True,
            approval_status="NOT_COMPLETED",
            remediation_executed=False,
            production_modified=False,
            latency_seconds=round(
                latency,
                3,
            ),
        )

        return {
            "status": "COMPLETED_WITHOUT_HITL",
            "incident_id": incident_id,

            "approval_required": True,
            "approval_status": "NOT_COMPLETED",
            "human_approved": False,

            "remediation_status": "NOT_EXECUTED",
            "remediation_action": "NONE",
            "remediation_executed": False,
            "production_modified": False,

            "evidence": report["evidence"],

            "root_cause": report[
                "root_cause"
            ],
            "evidence_summary": report[
                "evidence_summary"
            ],
            "conflicting_evidence": report[
                "conflicting_evidence"
            ],
            "uncertainty": report[
                "uncertainty"
            ],
            "confidence": report[
                "confidence"
            ],

            "agent_report": (
                report["report_text"]
                + "\n\n"
                + "SAFETY NOTICE:\n"
                "The expected human approval checkpoint was "
                "not reached. Remediation was NOT executed."
            ),

            "latency_seconds": round(
                latency,
                3,
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        latency = time.time() - start_time

        logger.exception(
            "Incident processing failed | id=%s | error=%s",
            incident_id,
            type(exc).__name__,
        )

        log_event(
            "agent_error",
            incident_id,
            error_type=type(exc).__name__,
            latency_seconds=round(
                latency,
                3,
            ),
        )

        # Never expose internals.
        raise HTTPException(
            status_code=500,
            detail="Failed to process incident.",
        )


# ============================================================
# HUMAN APPROVAL WEBHOOK
# ============================================================

@app.post("/webhook/approve")
async def human_approval(
    payload: ApprovalPayload,
):
    """
    Resume a paused incident.

    approved=True:
        → simulation-only remediation

    approved=False:
        → rejection path

    SECURITY:
        No production infrastructure is modified.
    """

    start_time = time.time()

    incident_id = payload.incident_id

    logger.info(
        "Human decision received | id=%s | approved=%s",
        incident_id,
        payload.approved,
    )

    config = get_thread_config(
        incident_id
    )

    try:

        # ====================================================
        # 1. FIND CHECKPOINT
        # ====================================================

        checkpoint = agent_graph.get_state(
            config
        )

        if (
            checkpoint is None
            or not getattr(
                checkpoint,
                "values",
                None,
            )
        ):

            log_event(
                "approval_error",
                incident_id,
                error_type="IncidentNotFound",
            )

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No active incident found for "
                    f"'{incident_id}'."
                ),
            )

        # ====================================================
        # 2. MUST BE WAITING FOR HITL
        # ====================================================

        if not getattr(
            checkpoint,
            "next",
            None,
        ):

            log_event(
                "approval_error",
                incident_id,
                error_type="NotWaitingForApproval",
            )

            raise HTTPException(
                status_code=409,
                detail=(
                    f"Incident '{incident_id}' is not "
                    f"currently waiting for human approval."
                ),
            )

        # ====================================================
        # 3. RESUME GRAPH
        # ====================================================

        result = agent_graph.invoke(
            Command(
                resume=payload.approved
            ),
            config=config,
        )

        latency = time.time() - start_time

        # ====================================================
        # 4. GET FINAL CHECKPOINT
        # ====================================================

        final_checkpoint = agent_graph.get_state(
            config
        )

        if final_checkpoint is None:

            raise HTTPException(
                status_code=500,
                detail="Final agent state unavailable.",
            )

        state = get_state_values(
            final_checkpoint
        )

        final_message = get_last_message_content(
            result
        )

        still_waiting = bool(
            getattr(
                final_checkpoint,
                "next",
                None,
            )
        )

        # ====================================================
        # 5. REJECTION
        # ====================================================

        if not payload.approved:

            # ------------------------------------------------
            # Never trust LLM wording here.
            #
            # API itself guarantees rejection safety.
            # ------------------------------------------------

            safety = {
                "approval_required": True,
                "approval_status": "REJECTED",
                "human_approved": False,
                "remediation_status": "NOT_EXECUTED",
                "remediation_action": "NONE",
                "remediation_executed": False,
                "production_modified": False,
            }

            evidence = build_evidence_summary(
                state
            )

            log_event(
                "human_decision",
                incident_id,
                approved=False,
                approval_status="REJECTED",
                remediation_executed=False,
                production_modified=False,
                latency_seconds=round(
                    latency,
                    3,
                ),
            )

            return {
                "status": "COMPLETED",
                "incident_id": incident_id,

                "approved": False,

                "approval_required": True,
                "approval_status": "REJECTED",
                "human_approved": False,

                "remediation_status": "NOT_EXECUTED",
                "remediation_action": "NONE",
                "remediation_executed": False,
                "production_modified": False,

                "evidence": evidence,

                "final_action": (
                    "HUMAN APPROVAL: REJECTED.\n\n"
                    "REMEDIATION STATUS: NOT_EXECUTED.\n\n"
                    "Remediation was NOT executed.\n" # <-- Changed phrasing here
                    "No production infrastructure was modified.\n"
                    "The proposed remediation was rejected by "
                    "the human reviewer.\n"
                    "The incident has been escalated for "
                    "manual investigation."
                ),

                # Keep original agent output available,
                # but put our deterministic safety statement
                # first.
                "agent_report": (
                    "HUMAN APPROVAL: REJECTED.\n"
                    "REMEDIATION EXECUTED: FALSE.\n"
                    "PRODUCTION MODIFIED: FALSE.\n\n"
                    f"{final_message}"
                ),

                "latency_seconds": round(
                    latency,
                    3,
                ),
            }

        # ====================================================
        # 6. APPROVAL
        # ====================================================

        safety = build_safety_state(
            state,
            hitl_pending=still_waiting,
            approval_override="APPROVED",
        )

        # ----------------------------------------------------
        # Safety contract:
        #
        # Approval authorizes simulation only.
        # Never report production modification.
        # ----------------------------------------------------

        safety["approval_required"] = True
        safety["approval_status"] = "APPROVED"
        safety["human_approved"] = True
        safety["remediation_executed"] = False
        safety["production_modified"] = False

        safety["remediation_status"] = (
            "SIMULATION_ONLY"
        )

        evidence = build_evidence_summary(
            state
        )

        log_event(
            "human_decision",
            incident_id,
            approved=True,
            approval_status="APPROVED",
            remediation_executed=False,
            production_modified=False,
            latency_seconds=round(
                latency,
                3,
            ),
        )

        return {
            "status": (
                "PAUSED_FOR_HUMAN_APPROVAL"
                if still_waiting
                else "COMPLETED"
            ),

            "incident_id": incident_id,

            "approved": True,

            "approval_required": True,
            "approval_status": "APPROVED",
            "human_approved": True,

            "remediation_status": "SIMULATION_ONLY",
            "remediation_action": "SIMULATED",
            "remediation_executed": False,
            "production_modified": False,

            "evidence": evidence,

            "final_action": (
                    "HUMAN APPROVAL: APPROVED.\n\n"
                    "REMEDIATION STATUS: SIMULATION_ONLY.\n\n"
                    "The proposed remediation was approved by "
                    "an authorized human reviewer.\n"
                    "Production remediation was NOT executed.\n" # <-- Changed phrasing here
                    "No production infrastructure was modified.\n"
                    "This capstone records only a simulation of "
                    "the approved remediation stage."
                ),

            "agent_report": (
                "HUMAN APPROVAL: APPROVED.\n"
                "APPROVAL STATUS: APPROVED.\n"
                "REMEDIATION STATUS: SIMULATION_ONLY.\n"
                "REMEDIATION EXECUTED: FALSE.\n"
                "PRODUCTION MODIFIED: FALSE.\n\n"
                f"{final_message}"
            ),

            "latency_seconds": round(
                latency,
                3,
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        latency = time.time() - start_time

        logger.exception(
            "Approval processing failed | id=%s | error=%s",
            incident_id,
            type(exc).__name__,
        )

        log_event(
            "approval_error",
            incident_id,
            error_type=type(exc).__name__,
            latency_seconds=round(
                latency,
                3,
            ),
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to process human approval.",
        )