from __future__ import annotations

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.core.security import require_internal_key, validate_object_id

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=[Depends(require_internal_key)])


class PatientContext(BaseModel):
    """Latest clinician-approved results, supplied by the backend (never by the browser)."""

    markers: dict[str, float] = Field(default_factory=dict)
    proms: dict | None = None
    sex: str | None = None
    age: float | None = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    thread_id: str = Field(..., min_length=1, max_length=100)
    patient_id: str
    patient_context: PatientContext | None = None


class ChatResponse(BaseModel):
    response: str
    escalation: dict
    guardrails: dict


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):
    from app.agent.graph import get_agent

    patient_id = validate_object_id(request.patient_id)
    result = get_agent().invoke(
        {
            "messages": [HumanMessage(content=request.message)],
            "patient_id": patient_id,
            "patient_context": request.patient_context.model_dump()
            if request.patient_context
            else {},
            "llm_calls": 0,
        },
        # Thread ids are namespaced by patient so one patient can never load another's memory.
        config={"configurable": {"thread_id": f"{patient_id}:{request.thread_id}"}},
    )
    g = result.get("guardrails") or {}
    return {
        "response": result["messages"][-1].content,
        "escalation": result.get("escalation")
        or {"required": False, "level": "routine", "reasons": []},
        "guardrails": {
            k: g.get(k) for k in ("passed", "violations", "readability_grade", "source")
        },
    }
