from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from agents.diagnostico_cumplimiento.domain.enums import QuestionType
from agents.diagnostico_cumplimiento.domain.models import (
    ApplicabilityRule,
    NormativeSource,
)


# ============================================================
# LEGACY MODELS
# ============================================================
#
# Se conservan temporalmente porque otras partes del Agente 2
# todavía pueden importarlos.
#
# No representan el nuevo schema 2.1 de los catálogos.
# ============================================================


class ConditionDefinition(BaseModel):
    """
    Modelo legado de condición evaluable.
    """

    id: str = Field(min_length=1)

    description: str = Field(min_length=1)

    required: bool = True


class QuestionDefinition(BaseModel):
    """
    Modelo legado de pregunta asociada a una condición.
    """

    id: str = Field(min_length=1)

    condition_id: str = Field(min_length=1)

    text: str = Field(min_length=1)

    type: QuestionType

    options: list[str] | None = None

    @model_validator(mode="after")
    def validate_options(self) -> "QuestionDefinition":
        selection_types = {
            QuestionType.SINGLE_CHOICE,
            QuestionType.MULTIPLE_CHOICE,
        }

        if self.type in selection_types:
            if not self.options or len(self.options) < 2:
                raise ValueError(
                    "Selection questions must define at least two options."
                )

        elif self.options is not None:
            raise ValueError(
                "Options are only allowed for selection questions."
            )

        return self


class CriterionDefinition(BaseModel):
    """
    Modelo legado del criterio normativo.
    """

    name: str = Field(min_length=1)

    official_text: str = Field(min_length=1)

    verification_method: str = Field(min_length=1)


class RequirementDefinition(BaseModel):
    """
    Modelo legado de requisito.

    Se conserva durante la migración del Agente 2 al schema 2.1.
    """

    id: str = Field(min_length=1)

    requirement_group_id: str = Field(min_length=1)

    official_item_id: str | None = None

    source: NormativeSource

    applicability: ApplicabilityRule

    criterion: CriterionDefinition

    conditions: list[ConditionDefinition] = Field(min_length=1)

    questions: list[QuestionDefinition] = Field(min_length=1)

    official_weight: float | None = Field(
        default=None,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_requirement_structure(
        self,
    ) -> "RequirementDefinition":
        condition_ids = [
            condition.id
            for condition in self.conditions
        ]

        if len(condition_ids) != len(set(condition_ids)):
            raise ValueError(
                "Condition IDs must be unique within a requirement."
            )

        question_ids = [
            question.id
            for question in self.questions
        ]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Question IDs must be unique within a requirement."
            )

        known_conditions = set(condition_ids)

        for question in self.questions:
            if question.condition_id not in known_conditions:
                raise ValueError(
                    f"Question '{question.id}' references "
                    f"unknown condition "
                    f"'{question.condition_id}'."
                )

        return self


# ============================================================
# SCHEMA 2.1
# ============================================================


PhvaCycle = Literal[
    "PLANEAR",
    "HACER",
    "VERIFICAR",
    "ACTUAR",
]


QuestionRole = Literal[
    "primary",
    "clarification",
    "evidence",
    "applicability_screening",
    "event_screening",
]


ApplicabilityMode = Literal[
    "always",
    "conditional",
    "event_dependent",
]

# ------------------------------------------------------------
# Scope
# ------------------------------------------------------------


class WorkerCountScope(BaseModel):
    """
    Rango de trabajadores cubierto por un paquete normativo.
    """

    min: int = Field(
        ge=0,
    )

    max: int | None = Field(
        default=None,
        ge=0,
    )

    count_type: Literal[
        "total",
        "permanent",
    ] = "total"

    @model_validator(mode="after")
    def validate_range(self) -> "WorkerCountScope":
        if self.max is not None and self.max < self.min:
            raise ValueError(
                "worker_count.max cannot be lower than "
                "worker_count.min."
            )

        return self


class CatalogScope(BaseModel):
    """
    Alcance empresarial del paquete normativo.
    """

    risk_classes: list[str] = Field(
        min_length=1,
    )

    worker_count: WorkerCountScope

    company_types: list[str] = Field(
        default_factory=list,
    )

    excluded_company_types: list[str] = Field(
        default_factory=list,
    )


# ------------------------------------------------------------
# Catalog applicability
# ------------------------------------------------------------


class CatalogApplicabilityRule(BaseModel):
    """
    Regla utilizada para seleccionar un paquete normativo.
    """

    field: str = Field(min_length=1)

    operator: str = Field(min_length=1)

    value: Any | None = None

    min: int | float | None = None

    max: int | float | None = None


class CatalogApplicability(BaseModel):
    """
    Reglas de selección del catálogo.
    """

    priority: int = 50

    rules: list[CatalogApplicabilityRule] = Field(
        min_length=1,
    )


# ------------------------------------------------------------
# Requirement applicability
# ------------------------------------------------------------


class RequirementApplicability(BaseModel):
    """
    Define cómo se comporta la aplicabilidad de un requisito.

    - always:
        el requisito se evalúa normalmente.

    - conditional:
        el requisito puede convertirse en No aplica cuando una
        condición normativa explícita resulte falsa.

    - event_dependent:
        la evaluación depende de que exista un evento o antecedente,
        pero su ausencia no genera automáticamente No aplica.
    """

    mode: ApplicabilityMode = "always"

    screening_question_id: str | None = None

    applies_when: Any | None = None

    not_applicable_when: Any | None = None

    not_applicable_reason: str | None = None

    not_applicable_allowed: bool = False

    not_applicable_scoring: str | None = None

    note: str | None = None

    @model_validator(mode="after")
    def validate_applicability_rule(
        self,
    ) -> "RequirementApplicability":

        # Solo "conditional" necesita obligatoriamente una pregunta
        # que determine si el requisito aplica o no.
        if self.mode == "conditional":
            if not self.screening_question_id:
                raise ValueError(
                    "Conditional requirement applicability must "
                    "define screening_question_id."
                )

        # Un requisito dependiente de eventos no debe convertirse
        # automáticamente en No aplica.
        if self.mode == "event_dependent":
            if self.not_applicable_allowed:
                raise ValueError(
                    "event_dependent requirements cannot automatically "
                    "generate a 'not_applicable' result."
                )

        return self


# ------------------------------------------------------------
# Questions
# ------------------------------------------------------------


class QuestionDependency(BaseModel):
    """
    Dependencia entre preguntas del mismo requisito.
    """

    question_id: str = Field(min_length=1)

    value: Any


class CatalogQuestionDefinition(BaseModel):
    """
    Pregunta diagnóstica del schema 2.1.

    No representa por sí sola un requisito normativo.
    Es un mecanismo para recopilar información declarada.
    """

    id: str = Field(min_length=1)

    role: QuestionRole

    text: str = Field(min_length=1)

    type: QuestionType

    source_type: Literal[
        "derived_from_criterion",
        "derived_from_verification_method",
    ]

    depends_on: QuestionDependency | None = None


# ------------------------------------------------------------
# PHVA
# ------------------------------------------------------------


class PhvaDefinition(BaseModel):
    """
    Clasificación PHVA utilizada para organizar el diagnóstico
    y posteriormente el informe.
    """

    cycle: PhvaCycle

    section: str = Field(min_length=1)

    mapping_source: str = Field(min_length=1)


# ------------------------------------------------------------
# Scoring
# ------------------------------------------------------------


class RequirementScoring(BaseModel):
    """
    Información de calificación asociada al requisito.

    Puede permanecer sin mapear en catálogos donde no se haya
    establecido una equivalencia oficial con el artículo 27.
    """

    item_value: float | None = Field(
        default=None,
        ge=0,
    )

    section_weight_percent: float | None = Field(
        default=None,
        ge=0,
    )

    mapping_status: str = Field(
        min_length=1,
    )


# ------------------------------------------------------------
# Source
# ------------------------------------------------------------


class RequirementSource(BaseModel):
    """
    Fuente normativa del requisito.
    """

    norm: str = Field(min_length=1)

    requirements_article: int = Field(
        ge=1,
    )

    scoring_article: int | None = Field(
        default=None,
        ge=1,
    )


# ------------------------------------------------------------
# Requirement
# ------------------------------------------------------------


class CatalogRequirementDefinition(BaseModel):
    """
    Requisito normativo ejecutable dentro del catálogo 2.1.
    """

    id: str = Field(min_length=1)

    official_item_id: str | None = None

    name: str = Field(min_length=1)

    phva: PhvaDefinition

    scoring: RequirementScoring

    official_criterion: str = Field(
        min_length=1,
    )

    official_verification_method: str | None = None

    verification_method_source: str = Field(
        min_length=1,
    )

    applicability: RequirementApplicability

    questions: list[CatalogQuestionDefinition] = Field(
        min_length=1,
    )

    source: RequirementSource

    @model_validator(mode="after")
    def validate_requirement_structure(
        self,
    ) -> "CatalogRequirementDefinition":
        question_ids = [
            question.id
            for question in self.questions
        ]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                f"Question IDs must be unique within "
                f"requirement '{self.id}'."
            )

        known_questions = set(question_ids)

        for question in self.questions:
            dependency = question.depends_on

            if dependency is None:
                continue

            if dependency.question_id not in known_questions:
                raise ValueError(
                    f"Question '{question.id}' references "
                    f"unknown question "
                    f"'{dependency.question_id}' "
                    f"inside requirement '{self.id}'."
                )

            if dependency.question_id == question.id:
                raise ValueError(
                    f"Question '{question.id}' cannot depend "
                    f"on itself."
                )

        if self.applicability.mode == "conditional":
            screening_question_id = (
                self.applicability.screening_question_id
            )

            if screening_question_id not in known_questions:
                raise ValueError(
                    f"Requirement '{self.id}' references "
                    f"unknown applicability screening question "
                    f"'{screening_question_id}'."
                )

        return self


# ------------------------------------------------------------
# Sections
# ------------------------------------------------------------


class CatalogSection(BaseModel):
    """
    Agrupación de requisitos por ciclo PHVA.
    """

    id: str = Field(min_length=1)

    name: str = Field(min_length=1)

    cycle: PhvaCycle

    requirements: list[CatalogRequirementDefinition] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_requirement_cycles(
        self,
    ) -> "CatalogSection":
        for requirement in self.requirements:
            if requirement.phva.cycle != self.cycle:
                raise ValueError(
                    f"Requirement '{requirement.id}' belongs "
                    f"to PHVA cycle "
                    f"'{requirement.phva.cycle}' but is inside "
                    f"section '{self.cycle}'."
                )

        return self


# ------------------------------------------------------------
# Reporting
# ------------------------------------------------------------


class ReportingDefinition(BaseModel):
    """
    Configuración común utilizada para construir la salida
    diagnóstica y posteriormente el PDF.
    """

    group_by_phva: bool = True

    show_all_requirements: bool = True

    show_not_applicable_requirements: bool = True

    include_official_criterion: bool = True

    include_official_verification_method: bool = True

    include_question_trace: bool = True

    status_values: list[str] = Field(
        min_length=1,
    )


# ------------------------------------------------------------
# No aplica policy
# ------------------------------------------------------------


class NonApplicabilityPolicy(BaseModel):
    """
    Política común para el estado No aplica.
    """

    package_default: str = Field(min_length=1)

    requirement_not_applicable_only_when: str = Field(
        min_length=1,
    )

    unanswered_is_not_not_applicable: bool = True

    not_applicable_reason_required: bool = True

    show_not_applicable_requirements_in_report: bool = True

    not_applicable_scoring: str = Field(
        min_length=1,
    )


# ------------------------------------------------------------
# Metadata
# ------------------------------------------------------------


class CatalogValidationMetadata(BaseModel):
    """
    Diferencia información normativa oficial de las decisiones
    de diseño construidas para el agente.
    """

    normative_source: str = Field(min_length=1)

    normative_requirements_require_expert_validation: bool

    derived_questions_require_expert_review: bool

    routing_rules_require_expert_review: bool

    assessment_rules_require_expert_review: bool

    non_applicability_rules_require_expert_review: bool


class CatalogMetadata(BaseModel):
    """
    Metadatos metodológicos del catálogo.
    """

    question_origin: str = Field(min_length=1)

    phva_mapping_source: str = Field(min_length=1)

    declarative_assessment: bool

    documentary_verification: bool

    validation: CatalogValidationMetadata

    notes: list[str] = Field(
        default_factory=list,
    )


# ============================================================
# ASSESSMENT CATALOG — SCHEMA 2.1
# ============================================================


class AssessmentCatalog(BaseModel):
    """
    Catálogo normativo ejecutable utilizado por el Agente 2.

    Todos los paquetes normativos deben compartir esta estructura
    para permitir que el motor cambie de catálogo sin cambiar la
    lógica de ejecución.
    """

    schema_version: str = Field(
        min_length=1,
    )

    catalog_id: str = Field(
        min_length=1,
    )

    name: str = Field(
        min_length=1,
    )

    norm: str = Field(
        min_length=1,
    )

    requirements_article: int = Field(
        ge=1,
    )

    scoring_article: int | None = Field(
        default=None,
        ge=1,
    )

    scope: CatalogScope

    applicability: CatalogApplicability

    non_applicability_policy: NonApplicabilityPolicy

    reporting: ReportingDefinition

    sections: list[CatalogSection] = Field(
        min_length=1,
    )

    metadata: CatalogMetadata

    @model_validator(mode="after")
    def validate_catalog_structure(
        self,
    ) -> "AssessmentCatalog":
        expected_cycles = [
            "PLANEAR",
            "HACER",
            "VERIFICAR",
            "ACTUAR",
        ]

        cycles = [
            section.cycle
            for section in self.sections
        ]

        if cycles != expected_cycles:
            raise ValueError(
                "Catalog sections must be ordered exactly as: "
                "PLANEAR, HACER, VERIFICAR, ACTUAR."
            )

        requirement_ids: list[str] = []

        question_ids: list[str] = []

        for section in self.sections:
            for requirement in section.requirements:
                requirement_ids.append(requirement.id)

                question_ids.extend(
                    question.id
                    for question in requirement.questions
                )

        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError(
                "Requirement IDs must be unique within the catalog."
            )

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Question IDs must be unique within the catalog."
            )

        return self

    # --------------------------------------------------------
    # Temporary compatibility helpers
    # --------------------------------------------------------

    @property
    def requirements(
        self,
    ) -> list[CatalogRequirementDefinition]:
        """
        Devuelve todos los requisitos del catálogo como una lista
        plana.

        Facilita la migración del código antiguo que utilizaba
        catalog.requirements.
        """

        return [
            requirement
            for section in self.sections
            for requirement in section.requirements
        ]

    @property
    def catalog_version(self) -> str:
        """
        Alias temporal del antiguo atributo catalog_version.
        """

        return self.schema_version

    @property
    def regulation(self) -> str:
        """
        Alias temporal del antiguo atributo regulation.
        """

        return self.norm