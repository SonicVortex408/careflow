"""Agent graph + checkpointer (conversation memory).

    START -> retrieve -> llm_call <-> tool_node
                         llm_call -> check -> (retry) llm_call
                                           -> finalize -> END

CHECKPOINTER=auto  Redis (langgraph-checkpoint-redis, needs Redis Stack modules)
                   when reachable, otherwise in-memory with a warning.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentState
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_checkpointer():
    s = get_settings()
    mode = s.checkpointer.lower()
    if mode in ("auto", "redis"):
        try:
            from langgraph.checkpoint.redis import RedisSaver

            saver = RedisSaver(redis_url=s.redis_url, ttl={"default_ttl": 60 * 24 * 30})
            saver.setup()
            logger.info("Conversation memory: Redis")
            return saver
        except Exception as exc:  # noqa: BLE001
            if mode == "redis":
                raise
            logger.warning(
                "Redis checkpointer unavailable (%s); using in-memory", type(exc).__name__
            )
    return InMemorySaver()


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("llm_call", nodes.llm_call)
    g.add_node("tool_node", nodes.tool_node)
    g.add_node("check", nodes.check)
    g.add_node("finalize", nodes.finalize)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "llm_call")
    g.add_conditional_edges(
        "llm_call", nodes.route_after_llm, {"tool_node": "tool_node", "check": "check"}
    )
    g.add_edge("tool_node", "llm_call")
    g.add_conditional_edges(
        "check", nodes.route_after_check, {"llm_call": "llm_call", "finalize": "finalize"}
    )
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer if checkpointer is not None else get_checkpointer())


@lru_cache(maxsize=1)
def get_agent():
    return build_graph()
