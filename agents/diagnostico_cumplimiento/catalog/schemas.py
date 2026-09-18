from pydantic import BaseModel, Field, model_validator

from agents.diagnostico_cumplimiento.domain.enums import QuestionType
from agents.diagnostico_cumplimiento.domain.models import (
    ApplicabilityRule,
    NormativeSource,
)


class ConditionDefinition(BaseModel):
    """
    Condición concreta que debe evaluarse dentro de un requisito normativo.

    Un requisito puede requerir varias condiciones para considerarse
    cumplido según la información declarada por el usuario.
    """

    id: str = Field(
        min_length=1,
        description="Identificador único de la condición dentro del requisito.",
    )

    description: str = Field(
        min_length=1,
        description="Descripción de la condición que debe evaluarse.",
    )

    required: bool = Field(
        default=True,
        description=(
            "Indica si la condición es obligatoria para considerar "
            "cumplido el requisito."
        ),
    )


class QuestionDefinition(BaseModel):
    """
    Pregunta conversacional utilizada para obtener información
    asociada a una condición del requisito.
    """

    id: str = Field(
        min_length=1,
        description="Identificador único de la pregunta.",
    )

    condition_id: str = Field(
        min_length=1,
        description="Condición del requisito que esta pregunta alimenta.",
    )

    text: str = Field(
        min_length=1,
        description="Texto de la pregunta presentada al usuario.",
    )

    type: QuestionType = Field(
        description="Tipo de respuesta esperada.",
    )

    options: list[str] | None = Field(
        default=None,
        description=(
            "Opciones disponibles cuando la pregunta es de selección."
        ),
    )

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
    Representación estructurada del criterio normativo y su
    mecanismo oficial de verificación.
    """

    name: str = Field(
        min_length=1,
        description="Nombre corto del criterio.",
    )

    official_text: str = Field(
        min_length=1,
        description="Texto del criterio tomado de la fuente normativa.",
    )

    verification_method: str = Field(
        min_length=1,
        description="Modo de verificación definido por la fuente oficial.",
    )


class RequirementDefinition(BaseModel):
    """
    Variante evaluable de un requisito normativo.

    Un mismo ítem oficial puede tener diferentes criterios,
    preguntas o reglas según el perfil empresarial.
    """

    id: str = Field(
        min_length=1,
        description=(
            "Identificador interno único de esta variante del requisito."
        ),
    )

    official_item_id: str = Field(
        min_length=1,
        description=(
            "Identificador del ítem en la tabla oficial de "
            "Estándares Mínimos."
        ),
    )

    source: NormativeSource

    applicability: ApplicabilityRule

    criterion: CriterionDefinition

    conditions: list[ConditionDefinition] = Field(
        min_length=1,
        description="Condiciones que componen la evaluación del requisito.",
    )

    questions: list[QuestionDefinition] = Field(
        min_length=1,
        description="Preguntas asociadas a las condiciones del requisito.",
    )

    official_weight: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Peso oficial del ítem cuando haya sido validado "
            "contra la fuente normativa."
        ),
    )

    @model_validator(mode="after")
    def validate_requirement_structure(self) -> "RequirementDefinition":
        condition_ids = [condition.id for condition in self.conditions]

        if len(condition_ids) != len(set(condition_ids)):
            raise ValueError(
                "Condition IDs must be unique within a requirement."
            )

        question_ids = [question.id for question in self.questions]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Question IDs must be unique within a requirement."
            )

        known_conditions = set(condition_ids)

        for question in self.questions:
            if question.condition_id not in known_conditions:
                raise ValueError(
                    f"Question '{question.id}' references unknown condition "
                    f"'{question.condition_id}'."
                )

        return self


class AssessmentCatalog(BaseModel):
    """
    Catálogo versionado de requisitos utilizados por el Agente 2.
    """

    catalog_version: str = Field(
        min_length=1,
        description="Versión del catálogo normativo.",
    )

    regulation: str = Field(
        min_length=1,
        description="Norma principal sobre la que se construye el catálogo.",
    )

    requirements: list[RequirementDefinition] = Field(
        min_length=1,
        description="Requisitos disponibles en esta versión del catálogo.",
    )

    @model_validator(mode="after")
    def validate_unique_requirement_ids(self) -> "AssessmentCatalog":
        requirement_ids = [
            requirement.id
            for requirement in self.requirements
        ]

        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError(
                "Requirement IDs must be unique within the catalog."
            )

        return self