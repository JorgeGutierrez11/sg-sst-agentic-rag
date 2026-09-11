"""Data contracts for business context."""

from typing import Literal, TypedDict

class BusinessProfile(TypedDict, total=False):
    """Relatively stable information about the company."""

    economic_activity: str
    ciiu_code: str
    worker_count: int
    risk_class: str
    

ProfileField = Literal[
    "economic_activity",
    "ciiu_code",
    "worker_count",
    "risk_class",
]


class BusinessProfileExtractionResult(TypedDict):
    """Explicit business-profile information extracted from a user message."""

    updates: BusinessProfile
    evidence: dict[ProfileField, str]


class ConversationTurn(TypedDict):
    """One complete interaction between the user and the agent."""

    user: str
    assistant: str

class RetrievedBusinessMemory(TypedDict):
    """Conversation memory recovered through semantic search."""

    memory_id: str
    user: str
    assistant: str
    score: float | None


class BusinessContext(TypedDict, total=False):
    """Business information available to downstream graph stages."""

    profile: BusinessProfile
    history: list[ConversationTurn]

    # Summarization-Based Memory
    history_summary: str
    summarized_turns: int

    # Retrieval-Based Long-Term Memory
    retrieved_memories: list[RetrievedBusinessMemory]


    current_context: str

"""
BusinessContext
│
├── profile
│   └── datos empresariales explícitos del usuario
│
├── history
│   └── historial completo de preguntas y respuestas
│
├── history_summary
│   └── resumen acumulado de turnos antiguos
│
├── summarized_turns
│   └── cantidad de turnos ya incluidos en el resumen
│
└── current_context
    └── contexto que la técnica actual entrega al resto del agente
"""