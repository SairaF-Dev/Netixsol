# LangGraph Stateful, Multi-Step & Cyclical Agent Workflows

## Overview

This project demonstrates how to build a **stateful, multi-step, and cyclical AI agent workflow using LangGraph**.

The workflow goes beyond a simple linear agent loop by using:

- Shared graph state
- Multiple graph nodes
- Linear and conditional edges
- Self-correction and retry loops
- Retry limits to prevent infinite cycles
- Human-in-the-loop approval
- Interrupts
- Persistent state with `MemorySaver`
- State history and checkpoint-based debugging
- Mermaid workflow visualization

The implementation uses **LangGraph**, **Groq**, and **Tavily**.

---

## Objectives

The main objectives of this exercise are to:

1. Understand LangGraph's core graph concepts.
2. Design and manage shared state between nodes.
3. Build a simple linear graph.
4. Add conditional routing and cyclical workflows.
5. Implement a self-correction loop.
6. Prevent infinite retries using a retry cap.
7. Add human approval before a risky action.
8. Pause and resume a graph using interrupts.
9. Persist graph state using a checkpointer.
10. Inspect state history and replay previous checkpoints.
11. Compare LangGraph with LangChain's `AgentExecutor`.

---

## Project Workflow

The final workflow consists of the following stages:

```text
START
  ↓
Plan
  ↓
Retrieve
  ↓
Generate
  ↓
Critique
  ↓
Quality Check
  ├── Quality >= 7 ─────→ Format
  │
  └── Quality < 7
          ↓
      Retry Check
       ├── Retries remain ──→ Generate
       │                         ↓
       │                      Critique
       │                         ↓
       │                   Quality Check
       │
       └── Max retries reached → Format
                                  ↓
                           Human Approval
                            ├── Rejected → END
                            │
                            └── Approved
                                  ↓
                         Simulated Send Email
                                  ↓
                                 END                            
```

   *Author: Saira Fatima | DevSquad '26 Internship at NetixSol*
                         