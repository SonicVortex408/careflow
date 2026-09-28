from typing import TypedDict

from langchain_core.messages import AnyMessage


class MessagesState(TypedDict):
    messages: list[AnyMessage]
    llm_calls: int
    handoff_required: bool
    patient_id: str