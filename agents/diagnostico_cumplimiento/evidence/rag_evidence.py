from dataclasses import dataclass

from agents.consulta_normativa.langchain_rag.main import (
    RagRuntime,
    build_runtime,
)
from agents.diagnostico_cumplimiento.catalog.schemas import (
    RequirementDefinition,
)
from agents.diagnostico_cumplimiento.domain.models import (
    CompanyProfile,
)


@dataclass(frozen=True)
class RequirementRagEvidence:
    """
    Evidencia normativa recuperada por el RAG para un requisito.

    Esta estructura no contiene ni modifica el estado de cumplimiento.
    """

    requirement_id: str
    query: str
    answer: str
    references: list[str]
    context: str
    chunks: list[str]


class RagEvidenceService:
    """
    Adaptador entre el Agente 2 y el RAG existente del Agente 1.

    El runtime se construye una única vez y se reutiliza durante
    todo el diagnóstico.
    """

    def __init__(
        self,
        runtime: RagRuntime | None = None,
    ) -> None:
        self._runtime = runtime or build_runtime(
            write_graph_image=False,
        )

    def retrieve_requirement_evidence(
        self,
        *,
        requirement: RequirementDefinition,
        profile: CompanyProfile,
    ) -> RequirementRagEvidence:
        query = build_requirement_evidence_query(
            requirement=requirement,
            profile=profile,
        )

        result = self._runtime.answer_with_langgraph(
            query,
            self._runtime.graph,
            thread_id=self._runtime.thread_id,
        )

        return RequirementRagEvidence(
            requirement_id=requirement.id,
            query=query,
            answer=result.answer,
            references=list(result.references),
            context=result.context,
            chunks=list(result.chunks),
        )


def build_requirement_evidence_query(
    *,
    requirement: RequirementDefinition,
    profile: CompanyProfile,
) -> str:
    """
    Construye una consulta orientada exclusivamente a recuperar
    fundamento normativo para un requisito previamente identificado.

    El RAG no debe decidir si la empresa cumple o no.
    """

    return (
        "Recupera y explica el fundamento normativo aplicable al "
        "siguiente requisito del SG-SST. "
        "No determines si la empresa cumple o incumple; únicamente "
        "identifica qué exige la normativa y cómo se verifica.\n\n"
        f"Perfil de referencia:\n"
        f"- Clase de riesgo: {profile.risk_class.value}\n"
        f"- Número de trabajadores: {profile.worker_count}\n\n"
        f"Requisito:\n"
        f"- Nombre: {requirement.criterion.name}\n"
        f"- Norma catalogada: {requirement.source.regulation}\n"
        f"- Ubicación: {requirement.source.article}\n"
        f"- Criterio catalogado: "
        f"{requirement.criterion.official_text}\n"
        f"- Método de verificación catalogado: "
        f"{requirement.criterion.verification_method}\n\n"
        "Devuelve el fundamento utilizando únicamente la evidencia "
        "normativa disponible en el corpus."
    )