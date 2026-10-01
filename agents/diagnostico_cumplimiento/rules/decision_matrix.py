from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents.diagnostico_cumplimiento.domain.models import (
    NormativeSource,
)


class DecisionRuleValidationStatus(StrEnum):
    """
    Estado de validación de una regla de decisión.

    DRAFT:
        Regla propuesta por el proyecto y todavía no validada
        por el experto SST.

    EXPERT_VALIDATED:
        Regla revisada y aceptada mediante el proceso formal
        de validación experta.
    """

    DRAFT = "draft"
    EXPERT_VALIDATED = "expert_validated"


class RequirementDecisionRule(BaseModel):
    """
    Fila de la matriz de decisión para un requisito.

    Describe qué respuestas utilizaría el agente y qué lógica
    se propone aplicar para obtener un resultado declarativo.

    La existencia de una regla no autoriza su ejecución como
    conclusión final mientras permanezca en estado DRAFT.
    """

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)

    regime_id: str = Field(min_length=1)

    criterion_name: str = Field(min_length=1)

    source: NormativeSource

    required_question_ids: list[str] = Field(
        min_length=1,
    )

    positive_rule: str = Field(
        min_length=1,
        description=(
            "Regla propuesta para obtener un resultado "
            "positivo según las declaraciones."
        ),
    )

    negative_rule: str = Field(
        min_length=1,
        description=(
            "Regla propuesta para obtener un resultado "
            "negativo según las declaraciones."
        ),
    )

    validation_status: DecisionRuleValidationStatus = (
        DecisionRuleValidationStatus.DRAFT
    )

    validation_notes: str | None = None

    @model_validator(mode="after")
    def validate_questions(self):
        if len(set(self.required_question_ids)) != len(
            self.required_question_ids
        ):
            raise ValueError(
                "La matriz contiene preguntas requeridas duplicadas."
            )

        return self


class DecisionMatrix(BaseModel):
    """
    Matriz versionada de reglas de decisión del Agente 2.
    """

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)

    rules: list[RequirementDecisionRule] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_rules(self):
        keys = [
            (rule.requirement_id, rule.regime_id)
            for rule in self.rules
        ]

        if len(keys) != len(set(keys)):
            raise ValueError(
                "Existen reglas duplicadas para el mismo "
                "requisito y régimen."
            )

        return self


AFFILIATION_ART3_RULE = RequirementDecisionRule(
    requirement_id="res0312_art3_afiliacion_1_10",
    regime_id="res0312_art3_risk_i_1_10",
    criterion_name=(
        "Afiliación al Sistema de Seguridad Social Integral"
    ),
    source=NormativeSource(
        regulation="Resolución 0312 de 2019",
        article="Artículo 3",
        official_url=(
            "https://www.suin-juriscol.gov.co/clp/"
            "contenidos.dll/Resolucion/30036681"
            "?fn=document-frame.htm%24f%3Dtemplates%243.0"
        ),
    ),
    required_question_ids=[
        "q_health_affiliation",
        "q_health_affiliation_support",
        "q_health_payment_support",
        "q_pension_affiliation",
        "q_pension_affiliation_support",
        "q_pension_payment_support",
        "q_occupational_risk_affiliation",
        "q_occupational_risk_affiliation_support",
        "q_occupational_risk_payment_support",
    ],
    positive_rule=(
        "Propuesta: todas las preguntas requeridas deben estar "
        "resueltas afirmativamente para producir "
        "'cumple según declaración'."
    ),
    negative_rule=(
        "Propuesta: una respuesta negativa relevante puede producir "
        "'no cumple según declaración', sujeto a las reglas de "
        "aplicabilidad y dependencia correspondientes."
    ),
    validation_status=DecisionRuleValidationStatus.DRAFT,
    validation_notes=(
        "La suficiencia de las preguntas y las reglas positiva "
        "y negativa están pendientes de validación por un experto SST."
    ),
)

PLAN_ANUAL_ART3_RULE = RequirementDecisionRule(
    requirement_id="res0312_art3_plan_anual_1_10",
    regime_id="res0312_art3_risk_i_1_10",
    criterion_name="Plan Anual de Trabajo",
    source=NormativeSource(
        regulation="Resolución 0312 de 2019",
        article="Artículo 3",
        official_url=(
            "https://www.suin-juriscol.gov.co/clp/"
            "contenidos.dll/Resolucion/30036681"
            "?fn=document-frame.htm%24f%3Dtemplates%243.0"
        ),
    ),
    required_question_ids=[
        "q_plan_exists",
        "q_employer_signature",
        "q_plan_objectives",
        "q_plan_targets",
        "q_plan_responsibilities",
        "q_plan_resources",
        "q_annual_schedule",
    ],
    positive_rule=(
        "Propuesta: el Plan Anual de Trabajo debe existir y las "
        "condiciones evaluadas mediante las preguntas requeridas "
        "deben estar resueltas afirmativamente para producir "
        "'cumple según declaración'."
    ),
    negative_rule=(
        "Propuesta: la inexistencia del Plan Anual de Trabajo o "
        "una respuesta negativa en una condición requerida puede "
        "producir 'no cumple según declaración'."
    ),
    validation_status=DecisionRuleValidationStatus.DRAFT,
    validation_notes=(
        "La suficiencia de las preguntas y las reglas positiva "
        "y negativa están pendientes de validación por un experto SST."
    ),
)

CAPACITACION_ART3_RULE = RequirementDecisionRule(
    requirement_id="res0312_art3_capacitacion_1_10",
    regime_id="res0312_art3_risk_i_1_10",
    criterion_name="Capacitación en SST",
    source=NormativeSource(
        regulation="Resolución 0312 de 2019",
        article="Artículo 3",
        official_url=(
            "https://www.suin-juriscol.gov.co/clp/"
            "contenidos.dll/Resolucion/30036681"
            "?fn=document-frame.htm%24f%3Dtemplates%243.0"
        ),
    ),
    required_question_ids=[
        "q_training_preparation",
        "q_training_execution",
        "q_priority_risks_training",
        "q_prevention_control_training",
        "q_training_records",
    ],
    positive_rule=(
        "Propuesta: las condiciones requeridas relacionadas con "
        "la preparación, ejecución, contenido y soportes de las "
        "actividades de capacitación deben estar resueltas "
        "afirmativamente para producir 'cumple según declaración'."
    ),
    negative_rule=(
        "Propuesta: una respuesta negativa en una condición "
        "requerida puede producir 'no cumple según declaración', "
        "considerando las dependencias entre las preguntas."
    ),
    validation_status=DecisionRuleValidationStatus.DRAFT,
    validation_notes=(
        "La suficiencia de las preguntas y las reglas positiva "
        "y negativa están pendientes de validación por un experto SST."
    ),
)

IDENTIFICACION_PELIGROS_ART3_RULE = RequirementDecisionRule(
    requirement_id="res0312_art3_identificacion_peligros_1_10",
    regime_id="res0312_art3_risk_i_1_10",
    criterion_name=(
        "Identificación de peligros, evaluación y valoración de riesgos"
    ),
    source=NormativeSource(
        regulation="Resolución 0312 de 2019",
        article="Artículo 3",
        official_url=(
            "https://www.suin-juriscol.gov.co/clp/"
            "contenidos.dll/Resolucion/30036681"
            "?fn=document-frame.htm%24f%3Dtemplates%243.0"
        ),
    ),
    required_question_ids=[
        "q_hazard_identification",
        "q_risk_evaluation",
        "q_risk_valuation",
        "q_arl_accompaniment",
        "q_risk_document_available",
        "q_arl_support_available",
    ],
    positive_rule=(
        "Propuesta: las condiciones requeridas relacionadas con "
        "la identificación de peligros, evaluación y valoración "
        "de riesgos, acompañamiento de la ARL y disponibilidad "
        "de los soportes deben estar resueltas afirmativamente "
        "para producir 'cumple según declaración'."
    ),
    negative_rule=(
        "Propuesta: una respuesta negativa en una condición "
        "requerida puede producir 'no cumple según declaración', "
        "considerando las dependencias entre las preguntas."
    ),
    validation_status=DecisionRuleValidationStatus.DRAFT,
    validation_notes=(
        "La suficiencia de las preguntas y las reglas positiva "
        "y negativa están pendientes de validación por un experto SST."
    ),
)

MEDIDAS_PREVENCION_CONTROL_ART3_RULE = RequirementDecisionRule(
    requirement_id=(
        "res0312_art3_medidas_prevencion_control_1_10"
    ),
    regime_id="res0312_art3_risk_i_1_10",
    criterion_name=(
        "Medidas de prevención y control frente a peligros "
        "y riesgos identificados"
    ),
    source=NormativeSource(
        regulation="Resolución 0312 de 2019",
        article="Artículo 3",
        official_url=(
            "https://www.suin-juriscol.gov.co/clp/"
            "contenidos.dll/Resolucion/30036681"
            "?fn=document-frame.htm%24f%3Dtemplates%243.0"
        ),
    ),
    required_question_ids=[
        "q_prevention_measures_execution",
        "q_prevention_measures_risk_based",
        "q_prevention_measures_support",
    ],
    positive_rule=(
        "Propuesta: la empresa debe declarar que ha ejecutado "
        "medidas de prevención y control, que estas se definieron "
        "considerando los peligros y riesgos identificados y que "
        "dispone de los soportes correspondientes para producir "
        "'cumple según declaración'."
    ),
    negative_rule=(
        "Propuesta: una respuesta negativa en una condición "
        "requerida puede producir 'no cumple según declaración', "
        "considerando las dependencias entre las preguntas."
    ),
    validation_status=DecisionRuleValidationStatus.DRAFT,
    validation_notes=(
        "La suficiencia de las preguntas y las reglas positiva "
        "y negativa están pendientes de validación por un experto SST."
    ),
)

DECISION_MATRIX_V1 = DecisionMatrix(
    version="agent2-decision-matrix-v1",
    rules=[
        AFFILIATION_ART3_RULE,
        PLAN_ANUAL_ART3_RULE,
        CAPACITACION_ART3_RULE,
        IDENTIFICACION_PELIGROS_ART3_RULE,
        MEDIDAS_PREVENCION_CONTROL_ART3_RULE,
    ],
)


def get_decision_rule(
    *,
    requirement_id: str,
    regime_id: str,
    matrix: DecisionMatrix = DECISION_MATRIX_V1,
) -> RequirementDecisionRule:
    """
    Recupera una regla exacta de la matriz.

    No intenta inferir una regla aproximada ni utilizar
    reglas de otro régimen.
    """

    matches = [
        rule
        for rule in matrix.rules
        if rule.requirement_id == requirement_id
        and rule.regime_id == regime_id
    ]

    if not matches:
        raise LookupError(
            "No existe una regla de decisión para "
            f"requirement_id='{requirement_id}' y "
            f"regime_id='{regime_id}'."
        )

    if len(matches) > 1:
        raise RuntimeError(
            "La matriz contiene más de una regla para "
            "el mismo requisito y régimen."
        )

    return matches[0]