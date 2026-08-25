"""
Answer Generation — Task 2, RAG Pipeline (step 5/5)

Takes the user's query + retrieved chunks and generates a grounded
UrduLish answer. The system prompt below forces the model to say it
doesn't know rather than invent property details — this is the main
lever against hallucination, measured later in evaluation/evaluate.py.

Swap ANTHROPIC or OPENAI depending on which LLM the voice agent uses
(Day 1 picked the LLM; this file is provider-agnostic at the call site).
"""

SYSTEM_PROMPT = """Aap ek professional real estate sales assistant hain jo UrduLish mein baat karte hain.

STRICT RULES:
1. Sirf neeche diye gaye CONTEXT mein maujood information use karein.
2. Agar context mein answer nahi hai, to saaf keh dein: "Is baare mein mujhe confirm karke aapko bataana hoga" — kabhi guess ya invent na karein.
3. Prices, sizes, ya availability KABHI bhi context ke bghair na batayein.
4. Tone: warm, professional, patient — jaisa ek human sales rep baat karta hai.
"""


def build_prompt(query, retrieved_chunks):
    context = "\n\n".join(f"[{c['chunk_id']}] {c['text']}" for c in retrieved_chunks)
    user_prompt = f"""CONTEXT:
{context}

CUSTOMER QUESTION: {query}

Answer only using the CONTEXT above, in UrduLish."""
    return SYSTEM_PROMPT, user_prompt


def generate_answer_anthropic(query, retrieved_chunks, client=None, model="claude-sonnet-4-6"):
    """Requires: pip install anthropic, ANTHROPIC_API_KEY set."""
    system_prompt, user_prompt = build_prompt(query, retrieved_chunks)
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def generate_answer_openai(query, retrieved_chunks, client=None, model="gpt-4o-mini"):
    """Requires: pip install openai, OPENAI_API_KEY set."""
    system_prompt, user_prompt = build_prompt(query, retrieved_chunks)
    if client is None:
        from openai import OpenAI
        client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=400,
    )
    return response.choices[0].message.content


def generate_answer_no_context_fallback(query, retrieved_chunks, min_score=0.05):
    """Offline stand-in for grading/demo without any API key: if nothing
    relevant was retrieved, refuses; otherwise returns the best matching
    chunk verbatim as the 'answer' (a stand-in for an LLM rewrite)."""
    if not retrieved_chunks or retrieved_chunks[0]["score"] < min_score:
        return "Is baare mein mujhe confirm karke aapko bataana hoga."
    return retrieved_chunks[0]["text"]
