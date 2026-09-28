from app.agent.graph import agent
from langchain_core.messages import HumanMessage


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
                "thread_id": "test-user-1"
            }
        }
    )

    print("\n--- Agent Response ---\n")

 
    for message in result["messages"]:

        if message.type == "ai" and message.content:
            print(message.content)


if __name__ == "__main__":
    main()