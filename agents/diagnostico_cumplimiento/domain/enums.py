from enum import StrEnum


class AssessmentStatus(StrEnum):
    """
    Estado resultante de la evaluación de un requisito del SG-SST.

    Los estados representan conclusiones obtenidas a partir de información
    declarada por el usuario. No implican verificación documental,
    auditoría ni certificación de cumplimiento.
    """

    DECLARED_COMPLIANT = "declared_compliant"
    DECLARED_NON_COMPLIANT = "declared_non_compliant"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    NOT_APPLICABLE = "not_applicable"


class QuestionType(StrEnum):
    """
    Tipos de respuesta soportados por las preguntas del diagnóstico.
    """

    BOOLEAN = "boolean"
    INTEGER = "integer"
    TEXT = "text"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"


class RiskClass(StrEnum):
    """
    Clases de riesgo del Sistema General de Riesgos Laborales.

    El Agente 2 únicamente realiza diagnósticos para empresas
    clasificadas en riesgo I, pero el modelo debe permitir
    identificar empresas que se encuentran fuera de su alcance.
    """

    I = "I"
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"