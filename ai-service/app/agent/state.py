from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    patient_id: str
    patient_context: dict[str, Any]
    retrieval: dict[str, Any]
    escalation: dict[str, Any]
    guardrails: dict[str, Any]
    guardrail_feedback: list[str]
    llm_calls: int
    attempts: int
