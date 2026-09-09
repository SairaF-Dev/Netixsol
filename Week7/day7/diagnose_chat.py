"""Probe chat understanding without printing credentials or customer data."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ("day7", "day3/src", "day2/03_structured_retrieval")]
import web_api.app  # Load the same configuration as the API.
from shared.sara_service import SaraService
from sara_agent.understanding import UserUnderstandingService

if __name__ == "__main__":
    try:
        service = UserUnderstandingService(deterministic_first=False)
        complete = service.client.chat.completions.create
        def probe(**kwargs):
            response = complete(**kwargs)
            for choice in response.choices or []:
                print("Provider response: finish_reason=", choice.finish_reason,
                      "content_characters=", len(choice.message.content or ""))
            print("Token usage:", response.usage)
            return response
        service.client.chat.completions.create = probe
        result = SaraService(service).understand(sys.argv[1] if len(sys.argv) > 1 else "Hello", {})
        print("Understanding succeeded:", result.intent)
    except Exception as exc:
        cause = exc.__cause__ or exc
        print("Understanding failed:", type(exc).__name__, type(cause).__name__,
              "status=", getattr(cause, "status_code", None))
        body = getattr(cause, "body", None)
        if isinstance(body, dict):
            error = body.get("error", body)
            if isinstance(error, dict):
                print("Provider message:", error.get("message", "Unavailable"))
        sys.exit(1)
