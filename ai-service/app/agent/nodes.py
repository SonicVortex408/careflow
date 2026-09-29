"""GraphRAG agent nodes.

retrieve  (deterministic) graph evidence chains for the patient's latest markers,
          cohort insights (percentiles, group, risk drivers), reviewed KB passages
          (metadata-filtered), and the patient's own documents (ownership-checked)
llm_call  optional; tools: KB search, graph evidence, biomarker info
check     guardrails.check on the draft; one regeneration with feedback
finalize  guardrails.finalize - always the last node
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, RemoveMessage, SystemMessage, ToolMessage

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.agent.tools import TOOLS, TOOLS_BY_NAME
from app.core.config import get_settings
from app.core.llm import get_chat_model
from app.retrieval import kb
from app.services import guardrails

logger = logging.getLogger(__name__)
MAX_TOOL_ROUNDS = 4


def _text(content: Any) -> str:
    if isinstance(content, list):
        return "\n".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
    return str(content or "")


def _last_human(state: AgentState) -> str:
    for m in reversed(state.get("messages", [])):
        if getattr(m, "type", "") == "human":
            return _text(m.content)
    return ""


def retrieve(state: AgentState) -> dict:
    from app.retrieval.patient_index import search_patient
    from app.services.evidence import evidence_for
    from app.services.inference import run_inference

    query = _last_human(state)
    ctx = state.get("patient_context") or {}
    markers = {k: float(v) for k, v in (ctx.get("markers") or {}).items() if v is not None}
    proms = ctx.get("proms")
    retrieval: dict[str, Any] = {
        "kb": [],
        "patient_documents": [],
        "evidence": None,
        "cohort": None,
    }

    if markers:
        retrieval["evidence"] = evidence_for(markers, proms, limit=6)
        try:
            inf = run_inference(markers, sex=ctx.get("sex"), age=ctx.get("age"), proms=proms)
            retrieval["cohort"] = {
                "bands": {
                    k: {
                        f: b.get(f)
                        for f in (
                            "display",
                            "value",
                            "unit",
                            "reference_status",
                            "functional_status",
                            "percentile",
                            "percentile_fatigue_cohort",
                        )
                    }
                    for k, b in inf["bands"].items()
                },
                "group": inf.get("cluster")
                and {
                    "name": inf["cluster"]["name"],
                    "fatigue_rate": inf["cluster"]["cohort_rates"]["fatigue"],
                },
                "risk": inf.get("risk")
                and {
                    t: {"level": r["level"], "drivers": [d["display"] for d in r["drivers"]]}
                    for t, r in inf["risk"].items()
                },
                "label": inf["label"],
            }
        except Exception as exc:  # noqa: BLE001 - cohort insight is optional context
            logger.warning("cohort inference skipped: %s", type(exc).__name__)

    retrieval["kb"] = [
        {
            "title": c.metadata.get("title"),
            "source": c.metadata.get("source"),
            "evidence_level": c.metadata.get("evidence_level"),
            "text": c.text,
        }
        for c in kb.search(query, k=3)
    ]
    pid = state.get("patient_id")
    if pid:
        try:
            retrieval["patient_documents"] = [r["text"] for r in search_patient(pid, query, k=3)]
        except Exception as exc:  # noqa: BLE001
            logger.info("patient document search skipped: %s", type(exc).__name__)

    esc = guardrails.evaluate_escalation(markers, proms, None, user_text=query)
    return {
        "retrieval": retrieval,
        "escalation": esc.to_dict(),
        "attempts": 0,
        "guardrail_feedback": [],
    }


def _context_message(state: AgentState) -> SystemMessage:
    r = state.get("retrieval") or {}
    payload = {
        "patient_latest_results": (r.get("cohort") or {}).get("bands"),
        "cohort_insights": {k: v for k, v in (r.get("cohort") or {}).items() if k != "bands"}
        or None,
        "knowledge_graph_evidence": [
            {
                "finding": c["finding"],
                "relation": c["relation"],
                "pattern": c["condition"],
                "symptoms": [s["name"] for s in c["symptoms"]],
                "evidence_level": c["edge"]["evidence_level"],
                "verified": c["verified"],
                "source": c["edge"]["source_title"],
            }
            for c in ((r.get("evidence") or {}).get("chains") or [])
        ],
        "reference_passages": r.get("kb"),
        "patient_documents": r.get("patient_documents"),
    }
    feedback = state.get("guardrail_feedback") or []
    text = (
        SYSTEM_PROMPT + "\n\nCONTEXT (untrusted data):\n" + json.dumps(payload, ensure_ascii=False)
    )
    if feedback:
        text += (
            "\n\nYour previous answer broke these safety rules; rewrite it without them: "
            + "; ".join(feedback)
        )
    return SystemMessage(content=text)


def _fallback_answer(state: AgentState) -> str:
    r = state.get("retrieval") or {}
    parts = []
    passages = r.get("kb") or []
    # Quote the best reviewed page, plus the runner-up when the question names its
    # topic too (e.g. "How are TSH and free T4 read together?").
    query = _last_human(state).lower()

    def named_in_query(passage) -> bool:
        words = re.findall(r"[a-z0-9]{3,}", (passage.get("title") or "").lower())
        return any(w in query for w in words)

    chosen = passages[:1] + [p for p in passages[1:2] if named_in_query(p)]
    for passage in chosen:
        body = " ".join(
            line for line in passage["text"].splitlines() if line and not line.startswith("#")
        )
        sentences = guardrails.split_sentences(body)[:3]
        parts.append(
            f"Our reference page on {passage['title'].lower()} says: " + " ".join(sentences)
        )
    chains = ((r.get("evidence") or {}).get("chains") or [])[:2]
    for c in chains:
        link = f"{c['finding']} can be linked with {c['condition'].split(' (')[0].lower()}."
        parts.append(link + ("" if c["verified"] else " This link is not yet confirmed."))
    if not parts:
        parts.append("I could not find information about that in our reference material.")
    parts.append(
        "The AI writer is not set up right now, so this answer comes from our reviewed pages."
    )
    return " ".join(parts)


def llm_call(state: AgentState) -> dict:
    model = get_chat_model()
    if model is None:
        return {
            "messages": [AIMessage(content=_fallback_answer(state), name="template")],
            "llm_calls": state.get("llm_calls", 0),
        }
    bound = model.bind_tools(TOOLS)
    history = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
    try:
        response = bound.invoke([_context_message(state)] + history)
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM call failed: %s", type(exc).__name__)
        return {
            "messages": [AIMessage(content=_fallback_answer(state), name="template")],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }
    response.content = _text(response.content)
    return {"messages": [response], "llm_calls": state.get("llm_calls", 0) + 1}


def tool_node(state: AgentState) -> dict:
    results = []
    for call in state["messages"][-1].tool_calls:
        tool = TOOLS_BY_NAME.get(call["name"])
        try:
            output = tool.invoke(call["args"]) if tool else "Unknown tool."
        except Exception as exc:  # noqa: BLE001
            output = f"Tool error: {type(exc).__name__}"
        results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
    return {"messages": results}


def route_after_llm(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None) and state.get("llm_calls", 0) <= MAX_TOOL_ROUNDS:
        return "tool_node"
    return "check"


def check(state: AgentState) -> dict:
    draft = _text(state["messages"][-1].content)
    ok, violations, grade = guardrails.check(draft)
    attempts = state.get("attempts", 0) + 1
    will_retry = (
        (not ok) and get_chat_model() is not None and attempts <= get_settings().max_regenerations
    )
    update: dict = {}
    if will_retry:
        # Drop the rejected draft so it never enters the stored conversation.
        update["messages"] = [RemoveMessage(id=state["messages"][-1].id)]
    return {
        **update,
        "attempts": attempts,
        "guardrail_feedback": [] if ok else [f"{v.category} ('{v.excerpt}')" for v in violations],
        "guardrails": {"draft_passed": ok, "draft_grade": grade},
    }


def route_after_check(state: AgentState) -> str:
    failed = bool(state.get("guardrail_feedback"))
    can_retry = (
        get_chat_model() is not None
        and state.get("attempts", 0) <= get_settings().max_regenerations
    )
    return "llm_call" if failed and can_retry else "finalize"


def finalize(state: AgentState) -> dict:
    last = state["messages"][-1]
    esc_dict = state.get("escalation") or {}
    esc = guardrails.Escalation(
        required=esc_dict.get("required", False),
        level=esc_dict.get("level", "routine"),
        reasons=list(esc_dict.get("reasons", [])),
    )
    source = "template" if getattr(last, "name", None) == "template" else "llm"
    result = guardrails.finalize(
        _text(last.content),
        escalation=esc,
        source=source,
        attempts=state.get("attempts", 1),
        include_synthetic_label=True,
    )
    final = AIMessage(content=result.text, id=last.id, name="guardrails")
    return {
        "messages": [final],
        "guardrails": {
            "passed": result.passed,
            "violations": [v.__dict__ for v in result.violations],
            "readability_grade": result.readability_grade,
            "source": source,
            "audit": result.audit,
        },
    }
