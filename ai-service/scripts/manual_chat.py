"""
Manual REPL for exercising the LangGraph chat agent end to end.

Not a test -- it loops forever reading stdin and calls the real LLM.
Requires GROQ_API_KEY (or the configured LLM_PROVIDER's key) and a built
faiss_index/ (see `python -m app.retrieval.ingest`).

Run from the ai-service/ directory:
    uv run python scripts/manual_chat.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import HumanMessage

from app.agent.graph import agent


def main():
    while True:
        question = input("You: ")

        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(content=question)
                ],
                "llm_calls": 0,
                "handoff_required": False
            },
            config={
                "configurable": {
                    "thread_id": "manual-test-1"
                }
            }
        )

        print("\n--- Agent Response ---\n")

        for message in result["messages"]:

            if message.type == "ai" and message.content:
                print(message.content)


if __name__ == "__main__":
    main()
