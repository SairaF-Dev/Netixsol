"""Prompt formatting utilities for Zarya Digital Bank assistant.

Provides unified system message generation across training, evaluation, and serving.
"""

def build_system_message(persona: str, context: str | None = None) -> str:
    """Builds a standardized system message combining bank persona and optional grounded context.

    Format rules:
    - If context is None or empty: returns persona text alone (no Documents section).
    - If context is provided: persona text, blank line, then 'Documents: ' + context text.
    - If context is 'koi document nahi mila': ends with 'Documents: koi document nahi mila'.
    """
    persona_clean = persona.strip()
    if not context or not str(context).strip():
        return persona_clean
    ctx_clean = str(context).strip()
    return f"{persona_clean}\n\nDocuments: {ctx_clean}"

