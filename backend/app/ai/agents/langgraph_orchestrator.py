"""
LangGraph-based chat orchestrator for NirovaAI.

This module keeps the orchestration deterministic and auditable for
health assistant workflows while preserving safe fallbacks.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Awaitable, Callable, Dict, List, Tuple, TypedDict
import logging

log = logging.getLogger(__name__)


class ChatGraphState(TypedDict, total=False):
    question: str
    mode: str
    client_context: str

    context: str
    sources: List[str]
    has_external_evidence: bool

    page_instruction: str
    format_instruction: str
    lang_instruction: str
    grounding_instruction: str

    messages: List[Dict[str, str]]
    raw_response: str
    final_response: str


@dataclass
class ChatGraphDeps:
    system_prompt: str
    get_context: Callable[[str, str], Awaitable[Tuple[str, List[str], bool]]]
    get_page_instruction: Callable[[str], str]
    get_format_instruction: Callable[[], str]
    get_language_instruction: Callable[[str], str]
    get_grounding_instruction: Callable[[bool], str]
    llm_respond: Callable[[List[Dict[str, str]]], Awaitable[str]]
    enforce_output_language: Callable[[str, str], Awaitable[str]]
    ensure_structured_response: Callable[[str], str]
    safe_context_text: Callable[[str], str]


async def _retrieve_context_node(state: ChatGraphState, deps: ChatGraphDeps) -> ChatGraphState:
    mode = (state.get("mode") or "general").strip().lower()
    context, sources, has_external_evidence = await deps.get_context(
        state.get("question", ""),
        mode,
    )
    state["context"] = deps.safe_context_text(context)
    state["sources"] = sources
    state["has_external_evidence"] = has_external_evidence
    return state


async def _instructions_node(state: ChatGraphState, deps: ChatGraphDeps) -> ChatGraphState:
    mode = (state.get("mode") or "general").strip().lower()
    question = state.get("question", "")
    has_external = bool(state.get("has_external_evidence", False))
    state["page_instruction"] = deps.get_page_instruction(mode)
    state["format_instruction"] = deps.get_format_instruction()
    state["lang_instruction"] = deps.get_language_instruction(question)
    state["grounding_instruction"] = deps.get_grounding_instruction(has_external)
    return state


async def _prompt_node(state: ChatGraphState, deps: ChatGraphDeps) -> ChatGraphState:
    context = state.get("context", "")
    client_context = deps.safe_context_text((state.get("client_context") or "").strip())
    question = state.get("question", "")
    page_instruction = state.get("page_instruction", "")
    format_instruction = state.get("format_instruction", "")
    lang_instruction = state.get("lang_instruction", "")
    grounding_instruction = state.get("grounding_instruction", "")

    state["messages"] = [
        {"role": "system", "content": deps.system_prompt},
        {
            "role": "user",
            "content": (
                "Medical Context from Bangladesh Health Guidelines:\n"
                f"{context}\n\n"
                "Immediate Page Context (latest analysis):\n"
                f"{client_context or 'None provided'}\n\n"
                f"Patient Question: {question}\n\n"
                f"Assistant Focus: {page_instruction}\n\n"
                f"{format_instruction}\n\n"
                f"Language Rule: {lang_instruction}\n\n"
                f"{grounding_instruction}\n\n"
                "Please provide helpful, accurate guidance based on the above context and focus area."
            ),
        },
    ]
    return state


async def _llm_node(state: ChatGraphState, deps: ChatGraphDeps) -> ChatGraphState:
    raw = await deps.llm_respond(state.get("messages") or [])
    state["raw_response"] = raw
    return state


async def _postprocess_node(state: ChatGraphState, deps: ChatGraphDeps) -> ChatGraphState:
    raw = state.get("raw_response", "")
    lang_instruction = state.get("lang_instruction", "")
    enforced = await deps.enforce_output_language(raw, lang_instruction)
    state["final_response"] = deps.ensure_structured_response(enforced)
    return state


async def _run_sequential_fallback(state: ChatGraphState, deps: ChatGraphDeps) -> ChatGraphState:
    state = await _retrieve_context_node(state, deps)
    state = await _instructions_node(state, deps)
    state = await _prompt_node(state, deps)
    state = await _llm_node(state, deps)
    state = await _postprocess_node(state, deps)
    return state


async def run_langgraph_chat(
    state: ChatGraphState,
    deps: ChatGraphDeps,
    *,
    enable_graph: bool = True,
) -> ChatGraphState:
    """Run chat orchestration using LangGraph if available; otherwise use safe sequential fallback."""

    # Try true graph orchestration first.
    if enable_graph:
        try:
            langgraph_module = import_module("langgraph.graph")
            END = langgraph_module.END
            StateGraph = langgraph_module.StateGraph

            async def retrieve_context(s: ChatGraphState) -> ChatGraphState:
                return await _retrieve_context_node(s, deps)

            async def instructions(s: ChatGraphState) -> ChatGraphState:
                return await _instructions_node(s, deps)

            async def prompt(s: ChatGraphState) -> ChatGraphState:
                return await _prompt_node(s, deps)

            async def llm(s: ChatGraphState) -> ChatGraphState:
                return await _llm_node(s, deps)

            async def postprocess(s: ChatGraphState) -> ChatGraphState:
                return await _postprocess_node(s, deps)

            graph = StateGraph(ChatGraphState)
            graph.add_node("retrieve_context", retrieve_context)
            graph.add_node("instructions", instructions)
            graph.add_node("prompt", prompt)
            graph.add_node("llm", llm)
            graph.add_node("postprocess", postprocess)

            graph.set_entry_point("retrieve_context")
            graph.add_edge("retrieve_context", "instructions")
            graph.add_edge("instructions", "prompt")
            graph.add_edge("prompt", "llm")
            graph.add_edge("llm", "postprocess")
            graph.add_edge("postprocess", END)

            app = graph.compile()
            return await app.ainvoke(state)

        except Exception as exc:
            # Keep API stable even when langgraph import/runtime fails.
            log.warning(f"LangGraph orchestration unavailable, using sequential fallback: {exc}")

    return await _run_sequential_fallback(state, deps)
