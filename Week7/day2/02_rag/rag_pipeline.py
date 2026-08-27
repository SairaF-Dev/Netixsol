
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from retriever import Retriever


load_dotenv()


SYSTEM_RULE = """
You are Sara, a real estate assistant.

Answer ONLY using the verified company context provided to you.

Rules:
1. Never invent property details.
2. Never invent prices or availability.
3. Never invent amenities or payment plans.
4. Never guarantee investment returns.
5. If the answer is not present in the verified context,
   say exactly:
   "Verified information is currently unavailable."
6. Clearly distinguish verified information from assumptions.
7. Do not use outside knowledge.
"""


class RAGPipeline:

    def __init__(
        self,
        documents_dir="documents",

        chunk_size=512,
        top_k=4,
    ):
        self.top_k = top_k

        self.retriever = Retriever(
            documents_dir=documents_dir,
            chunk_size=chunk_size,
        )

        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured."
            )

        self.llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=1000,
        )

    def retrieve_context(self, question):

        return self.retriever.retrieve(
            question,
            top_k=self.top_k,
        )

    def build_prompt(self, question, results):

        if not results:
            context = "No verified context was retrieved."

        else:
            context = "\n\n".join(
                (
                    f"[Source: {result['source']}]\n"
                    f"[Distance: {result['distance']:.4f}]\n"
                    f"{result['text']}"
                )
                for result in results
            )

        return f"""
{SYSTEM_RULE}

Verified Context:
{context}

User Question:
{question}

Answer using only the verified context above.
"""

    def answer(self, question):

        if not question or not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        question = question.strip()

        # 1. Retrieve relevant documents
        results = self.retrieve_context(question)

        # 2. Build grounded prompt
        prompt = self.build_prompt(
            question,
            results,
        )

        # 3. Send prompt to LLM
        response = self.llm.invoke(prompt)

        # 4. Extract final answer
        answer = response.content

        return {
            "question": question,
            "results": results,
            "prompt": prompt,
            "answer": answer,
        }


if __name__ == "__main__":

    pipeline = RAGPipeline(
        chunk_size=512,
        top_k=4,
    )

    # question = "What amenities are listed for Skyline Residences?"
    # question = "Who is the developer of Skyline Residences?"
    # question = "What is the payment plan for Skyline Residences?"
    # question = "What is the expected investment return for Skyline Residences?"
    question = "What is the nearest hospital to Skyline Residences?"

    result = pipeline.answer(question)

    print("\nRAG PIPELINE")
    print("=" * 60)

    print("\nQUESTION:")
    print(result["question"])

    print("\nRETRIEVED CONTEXT:")
    print("-" * 60)

    for item in result["results"]:

        print(
            f"\nDistance: {item['distance']:.4f}"
            f"\nSource: {item['source']}"
            f"\nChunk: {item['chunk_id']}"
            f"\n{item['text']}"
        )

    print("\nGENERATED ANSWER:")
    print("=" * 60)
    print(result["answer"])

