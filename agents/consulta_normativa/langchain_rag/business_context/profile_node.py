"""LangGraph node for business-profile extraction and update."""

from collections.abc import Callable
from typing import Any

from agents.consulta_normativa.langchain_rag.business_context.profile import (
    update_business_profile,
)
from agents.consulta_normativa.langchain_rag.business_context.profile_extractor import (
    extract_business_profile,
)
from agents.consulta_normativa.langchain_rag.core.state import RagGraphState


def business_profile_node(
    llm: Any,
) -> Callable[[RagGraphState], RagGraphState]:
    """Build a node that extracts and updates explicit business-profile data."""

    def run(state: RagGraphState) -> RagGraphState:
        business_context = dict(state.get("business_context", {}))
        current_profile = dict(business_context.get("profile", {}))

        extraction = extract_business_profile(
            llm=llm,
            question=state["question"],
        )

        updated_profile = update_business_profile(
            current_profile=current_profile,
            updates=extraction["updates"],
            source="user_explicit",
        )

        business_context["profile"] = updated_profile

        return {
            "business_context": business_context,
        }

    return run