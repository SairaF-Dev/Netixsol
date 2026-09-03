"""Optional n8n webhook publisher with bounded retries."""
from __future__ import annotations
import asyncio
from typing import Any
from uuid import uuid4
import httpx

class WorkflowPublishError(RuntimeError): pass

class N8NPublisher:
    def __init__(self, webhook_url: str | None, api_key: str | None = None, timeout_seconds: float = 8, max_attempts: int = 3) -> None:
        self.webhook_url, self.api_key, self.timeout_seconds, self.max_attempts = webhook_url, api_key, timeout_seconds, max(1, max_attempts)
    async def publish(self, event_type: str, payload: dict[str, Any]) -> str | None:
        if not self.webhook_url: return None
        event_id = uuid4().hex
        headers = {"X-Workflow-Event-Id": event_id}
        if self.api_key: headers["Authorization"] = f"Bearer {self.api_key}"
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for attempt in range(self.max_attempts):
                try:
                    response = await client.post(self.webhook_url, json={"event_id": event_id, "event_type": event_type, "payload": payload}, headers=headers)
                    response.raise_for_status(); return event_id
                except (httpx.HTTPError, OSError) as exc:
                    last_error = exc
                    if attempt + 1 < self.max_attempts: await asyncio.sleep(0.25 * (2 ** attempt))
        raise WorkflowPublishError(f"n8n publish failed after {self.max_attempts} attempts: {last_error}")

class InMemoryWorkflowPublisher:
    def __init__(self) -> None: self.events: list[dict] = []
    async def publish(self, event_type: str, payload: dict) -> str:
        event_id = uuid4().hex; self.events.append({"event_id": event_id, "event_type": event_type, "payload": payload}); return event_id
