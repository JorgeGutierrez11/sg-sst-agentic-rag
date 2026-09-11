"""Tests for LangGraph thread-scoped persistence."""

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph


class PersistenceTestState(TypedDict, total=False):
    """Minimal state used only to verify thread persistence."""

    value: int


def increment_node(
    state: PersistenceTestState,
) -> PersistenceTestState:
    """Increment the persisted value."""

    current_value = state.get("value", 0)

    return {
        "value": current_value + 1,
    }


def build_test_graph():
    """Build a minimal graph with an in-memory checkpointer."""

    workflow = StateGraph(PersistenceTestState)

    workflow.add_node(
        "increment",
        increment_node,
    )

    workflow.set_entry_point("increment")
    workflow.add_edge("increment", END)

    checkpointer = InMemorySaver()

    return workflow.compile(
        checkpointer=checkpointer,
    )


def test_same_thread_preserves_previous_state() -> None:
    graph = build_test_graph()

    config = {
        "configurable": {
            "thread_id": "company-001",
        }
    }

    first_result = graph.invoke(
        {},
        config,
    )

    second_result = graph.invoke(
        {},
        config,
    )

    assert first_result["value"] == 1
    assert second_result["value"] == 2


def test_different_threads_keep_independent_state() -> None:
    graph = build_test_graph()

    company_1_config = {
        "configurable": {
            "thread_id": "company-001",
        }
    }

    company_2_config = {
        "configurable": {
            "thread_id": "company-002",
        }
    }

    company_1_first = graph.invoke(
        {},
        company_1_config,
    )

    company_1_second = graph.invoke(
        {},
        company_1_config,
    )

    company_2_first = graph.invoke(
        {},
        company_2_config,
    )

    assert company_1_first["value"] == 1
    assert company_1_second["value"] == 2

    assert company_2_first["value"] == 1