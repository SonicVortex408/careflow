from typing import Literal

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.checkpoint.memory import InMemorySaver

from app.agent.state import MessagesState

from app.agent.nodes import (
    llm_call,
    tool_node,
    handoff_check,
    handoff_node
)


def should_continue(
    state: MessagesState
) -> Literal["tool_node", "__end__"]:

    last = state["messages"][-1]

    if hasattr(last, "tool_calls") and last.tool_calls:

        return "tool_node"

    return "__end__"


def route_after_handoff(
    state: MessagesState
) -> Literal["handoff", "__end__"]:

    if state.get("handoff_required", False):

        return "handoff"

    return "__end__"


checkpointer = InMemorySaver()

agent_builder = StateGraph(
    MessagesState
)


agent_builder.add_node(
    "llm_call",
    llm_call
)

agent_builder.add_node(
    "tool_node",
    tool_node
)

agent_builder.add_node(
    "handoff_check",
    handoff_check
)

agent_builder.add_node(
    "handoff",
    handoff_node
)


agent_builder.add_edge(
    START,
    "llm_call"
)


agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    {
        "tool_node": "tool_node",
        "__end__": "handoff_check"
    }
)


agent_builder.add_edge(
    "tool_node",
    "llm_call"
)


agent_builder.add_conditional_edges(
    "handoff_check",
    route_after_handoff,
    {
        "handoff": "handoff",
        "__end__": END
    }
)


agent_builder.add_edge(
    "handoff",
    END
)


agent = agent_builder.compile(
    checkpointer=checkpointer
)