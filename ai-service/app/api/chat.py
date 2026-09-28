from fastapi import APIRouter
from pydantic import BaseModel

from langchain_core.messages import HumanMessage

from app.agent.graph import agent


router = APIRouter(
    prefix="/api/chat",
    tags=["chat"]
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    patient_id: str


class ChatResponse(BaseModel):
    response: str


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):

    result = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=request.message
                )
            ],
            "llm_calls": 0,
            "handoff_required": False,

            # Patient whose medical documents
            # should be available to the agent.
            "patient_id": request.patient_id
        },

        config={
            "configurable": {
                "thread_id": request.thread_id
            }
        }
    )

    response = result["messages"][-1].content

    return {
        "response": response
    }
