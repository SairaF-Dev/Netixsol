from __future__ import annotations
import json, time
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from day5_graph import run_query

app = FastAPI(title="AFL Assistant API", version="1.0.0")
LOG = Path("monitoring.jsonl")

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    intent: str | None = None
    prediction: dict | None = None
    latency_ms: float | None = None

@app.get("/health")
def health():
    return {"status":"ok","service":"afl-assistant"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    started=time.perf_counter()
    result=run_query(req.message, req.conversation_id)
    latency=round((time.perf_counter()-started)*1000,2)
    event={
        "timestamp":time.time(),
        "conversation_id":req.conversation_id,
        "query":req.message,
        "intent":result.get("intent"),
        "tools_called":result.get("tools_called",[]),
        "latency_ms":latency,
        "error":result.get("error",""),
    }
    with LOG.open("a",encoding="utf-8") as f:
        f.write(json.dumps(event,default=str)+"\n")
    return ChatResponse(
        response=result.get("final_response",""),
        conversation_id=req.conversation_id,
        intent=result.get("intent"),
        prediction=result.get("prediction_metadata"),
        latency_ms=latency,
    )
