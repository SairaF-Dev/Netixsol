from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from query_policy import requires_structured_source
from retriever import Retriever


load_dotenv()


FALLBACK_ANSWER = (
    "Verified information is currently unavailable."
)


SYSTEM_RULE = """
You are Sara's grounded real-estate knowledge layer.

Use ONLY the verified company context supplied in the prompt.
Never use outside knowledge or the user's claims as evidence.
Never invent missing information.
Never guarantee investment returns.

IMPORTANT:

1. If the retrieved context contains information relevant to the
   user's question, answer from that context.

2. If the user asks about a company policy or procedure, explain
   that policy from the verified context.

3. A policy statement containing the words
   "verified information is currently unavailable"
   is NOT automatically a reason to refuse the current question.
   Explain the policy when the user is asking what Sara should do.

4. If the user asks for a general project overview, summarize the
   semantic project information present in the retrieved document.

5. Do not refuse a general project-overview question merely because
   exact price, availability, bedrooms, amenities, payment plans,
   or other structured facts are not present. Those exact facts
   belong to PostgreSQL.

6. Only when the retrieved context genuinely contains no information
   that answers the user's question, respond exactly:
   "Verified information is currently unavailable."

Keep the answer concise and factual.
For FAQ questions, preserve the important verified policy meaning.
""".strip()


class RAGPipeline:

    def __init__(
        self,
        documents_dir="documents",
        chunk_size=None,
        top_k=None,
        distance_threshold=None,
        persist_directory="chroma_db",
    ):

        # -----------------------------------------
        # Retrieval settings
        # -----------------------------------------

        self.top_k = int(
            top_k
            or os.getenv(
                "RAG_TOP_K",
                "4",
            )
        )

        if self.top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0"
            )

        self.retriever = Retriever(
            documents_dir=documents_dir,
            persist_directory=persist_directory,
            chunk_size=chunk_size,
            distance_threshold=distance_threshold,
        )

        # -----------------------------------------
        # OpenRouter settings
        # -----------------------------------------

        key = os.getenv(
            "OPENROUTER_API_KEY"
        )

        if not key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured."
            )

        self.max_tokens = int(
            os.getenv(
                "RAG_MAX_TOKENS",
                "160",
            )
        )

        if self.max_tokens <= 0:
            raise ValueError(
                "RAG_MAX_TOKENS must be greater than 0"
            )

        self.llm = ChatOpenAI(
            model=os.getenv(
                "OPENROUTER_MODEL",
                "openai/gpt-4o-mini",
            ),
            temperature=0,
            api_key=key,
            base_url=os.getenv(
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1",
            ),
            max_tokens=self.max_tokens,

            # Do not keep retrying when credits/provider fails.
            max_retries=1,

            # Prevent hanging requests.
            timeout=float(
                os.getenv(
                    "RAG_LLM_TIMEOUT_SECONDS",
                    "30",
                )
            ),
        )

    # ---------------------------------------------
    # Retrieval
    # ---------------------------------------------

    def retrieve_context(
        self,
        question,
    ):
        return self.retriever.retrieve(
            question,
            top_k=self.top_k,
        )

    # ---------------------------------------------
    # Prompt
    # ---------------------------------------------

    def build_prompt(
        self,
        question,
        results,
    ):

        if not results:
            return None

        blocks = []

        for result in results:

            block = "\n".join(
                [
                    f"[Source: {result['source']}]",
                    (
                        "[Document type: "
                        f"{result.get('document_type', 'knowledge')}]"
                    ),
                    (
                        "[Distance: "
                        f"{result['distance']:.4f}]"
                    ),
                    result["text"],
                ]
            )

            blocks.append(
                block
            )

        context = "\n\n".join(
            blocks
        )

        return f"""
{SYSTEM_RULE}

VERIFIED COMPANY CONTEXT
========================
{context}

USER QUESTION
=============
{question}

ANSWER
======
Answer only from the verified company context.
""".strip()

    # ---------------------------------------------
    # Answer
    # ---------------------------------------------

    def answer(
        self,
        question,
    ):

        if not isinstance(
            question,
            str,
        ):
            raise TypeError(
                "question must be a string"
            )

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        # -----------------------------------------
        # Structured facts must use PostgreSQL
        # -----------------------------------------

        if requires_structured_source(
            question
        ):

            return {
                "question": question,
                "results": [],
                "prompt": None,
                "answer": FALLBACK_ANSWER,
                "reason": (
                    "structured_fact_requires_postgresql"
                ),
                "error": None,
            }

        # -----------------------------------------
        # Retrieve verified semantic context
        # -----------------------------------------

        results = self.retrieve_context(
            question
        )

        if not results:

            return {
                "question": question,
                "results": [],
                "prompt": None,
                "answer": FALLBACK_ANSWER,
                "reason": "no_relevant_context",
                "error": None,
            }

        prompt = self.build_prompt(
            question,
            results,
        )

        # -----------------------------------------
        # LLM generation
        # -----------------------------------------

        try:

            response = self.llm.invoke(
                prompt
            )

            answer = str(
                response.content
                or ""
            ).strip()

            if not answer:
                answer = (
                    FALLBACK_ANSWER
                )

            return {
                "question": question,
                "results": results,
                "prompt": prompt,
                "answer": answer,
                "reason": "grounded_context",
                "error": None,
            }

        except Exception as exc:

            # Important:
            # Provider/credit/network failure should
            # NOT crash the whole evaluation.

            return {
                "question": question,
                "results": results,
                "prompt": prompt,
                "answer": FALLBACK_ANSWER,
                "reason": "llm_provider_error",
                "error": str(exc),
            }