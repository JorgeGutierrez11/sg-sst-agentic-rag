from dataclasses import dataclass, field
from io import BytesIO
from threading import RLock
from uuid import uuid4

from agents.diagnostico_cumplimiento.api.schemas import (
    CompleteDiagnosticResponse,
    CreateDiagnosticRequest,
    CreateDiagnosticResponse,
    DiagnosticProgressResponse,
    DiagnosticSummaryResponse,
    QuestionResponse,
    RequirementAssessmentResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from agents.diagnostico_cumplimiento.catalog.loader import (
    load_catalog_for_profile,
)
from agents.diagnostico_cumplimiento.catalog.schemas import (
    AssessmentCatalog,
    CatalogRequirementDefinition,
    CatalogQuestionDefinition,
)
from agents.diagnostico_cumplimiento.domain.answers import (
    QuestionAnswer,
)
from agents.diagnostico_cumplimiento.domain.enums import RiskClass
from agents.diagnostico_cumplimiento.domain.interpretation import (
    InterpretationStatus,
)
from agents.diagnostico_cumplimiento.domain.models import (
    CompanyProfile,
)
from agents.diagnostico_cumplimiento.preliminary_diagnosis import (
    run_preliminary_diagnosis,
)
from agents.diagnostico_cumplimiento.reporting.art27_scoring_matrix import (
    Article27ScoringMatrix,
)
from agents.diagnostico_cumplimiento.reporting.art27_table_pdf import (
    build_article27_table_pdf,
)
from agents.diagnostico_cumplimiento.reporting.scoring_matrix import (
    build_scoring_matrix,
)
from agents.diagnostico_cumplimiento.questionnaire.answer_interpreter import (
    interpret_boolean_answer_hybrid,
)
from agents.diagnostico_cumplimiento.questionnaire.requirement_answer_processor import (
    process_requirement_answers,
)
from agents.diagnostico_cumplimiento.rules.applicability import (
    select_applicable_requirements,
)


@dataclass
class DiagnosticSession:
    diagnosis_id: str
    profile: CompanyProfile
    catalog: AssessmentCatalog
    requirements: list[CatalogRequirementDefinition]
    answers: list[QuestionAnswer] = field(default_factory=list)


class DiagnosticService:
    """
    Servicio de aplicación para el diagnóstico declarativo de SG-SST.

    La lógica normativa permanece en el núcleo del agente. Esta clase
    únicamente administra sesiones, coordina el flujo de preguntas y
    expone resultados mediante los contratos de la API.

    Las sesiones se almacenan temporalmente en memoria.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, DiagnosticSession] = {}
        self._lock = RLock()

    def create_diagnostic(
        self,
        payload: CreateDiagnosticRequest,
    ) -> CreateDiagnosticResponse:
        profile = self._build_company_profile(payload)

        catalog = load_catalog_for_profile(profile)

        requirements = select_applicable_requirements(
            profile=profile,
            catalog=catalog,
        )

        diagnosis_id = str(uuid4())

        session = DiagnosticSession(
            diagnosis_id=diagnosis_id,
            profile=profile,
            catalog=catalog,
            requirements=requirements,
        )

        with self._lock:
            self._sessions[diagnosis_id] = session

        next_question = self._find_next_question(session)
        progress = self._build_progress(
            session=session,
            next_question=next_question,
        )

        return CreateDiagnosticResponse(
            diagnosis_id=diagnosis_id,
            catalog_id=catalog.catalog_id,
            catalog_name=catalog.name,
            progress=progress,
            next_question=next_question,
        )

    def submit_answer(
        self,
        diagnosis_id: str,
        payload: SubmitAnswerRequest,
    ) -> SubmitAnswerResponse:
        with self._lock:
            session = self._get_session(diagnosis_id)

            expected_question = self._find_next_question(
                session
            )

            if expected_question is None:
                raise ValueError(
                    "The diagnostic has no pending questions."
                )

            if (
                payload.requirement_id
                != expected_question.requirement_id
                or payload.question_id
                != expected_question.question_id
            ):
                raise ValueError(
                    "The submitted answer does not correspond "
                    "to the current diagnostic question."
                )

            if self._answer_exists(
                session=session,
                requirement_id=payload.requirement_id,
                question_id=payload.question_id,
            ):
                raise ValueError(
                    "This question has already been answered."
                )

            requirement = next(
                requirement
                for requirement in session.requirements
                if requirement.id
                == payload.requirement_id
            )

            original_answer = QuestionAnswer(
                requirement_id=payload.requirement_id,
                question_id=payload.question_id,
                raw_answer=payload.answer,
            )

            if isinstance(payload.answer, bool):
                evaluation_answer = original_answer

                interpretation_status = (
                    InterpretationStatus.AFFIRMATIVE
                    if payload.answer
                    else InterpretationStatus.NEGATIVE
                )

            else:
                interpretation = (
                    interpret_boolean_answer_hybrid(
                        requirement,
                        original_answer,
                    )
                )

                interpretation_status = (
                    interpretation.status
                )

                if (
                    interpretation.status
                    == InterpretationStatus.AFFIRMATIVE
                ):
                    evaluation_answer = QuestionAnswer(
                        requirement_id=(
                            payload.requirement_id
                        ),
                        question_id=payload.question_id,
                        raw_answer=True,
                    )

                elif (
                    interpretation.status
                    == InterpretationStatus.NEGATIVE
                ):
                    evaluation_answer = QuestionAnswer(
                        requirement_id=(
                            payload.requirement_id
                        ),
                        question_id=payload.question_id,
                        raw_answer=False,
                    )

                elif (
                    interpretation.status
                    == InterpretationStatus.INSUFFICIENT_INFORMATION
                ):
                    evaluation_answer = original_answer

                elif (
                    interpretation.status
                    == InterpretationStatus.NEEDS_CLARIFICATION
                ):
                    progress = self._build_progress(
                        session=session,
                        next_question=expected_question,
                    )

                    return SubmitAnswerResponse(
                        diagnosis_id=diagnosis_id,
                        progress=progress,
                        next_question=expected_question,
                        interpretation_status=(
                            interpretation.status.value
                        ),
                        clarification_message=(
                            interpretation.explanation
                        ),
                    )

                else:
                    raise ValueError(
                        "The answer could not be interpreted."
                    )

            session.answers.append(
                evaluation_answer
            )

            next_question = self._find_next_question(
                session
            )

            progress = self._build_progress(
                session=session,
                next_question=next_question,
            )

        return SubmitAnswerResponse(
            diagnosis_id=diagnosis_id,
            progress=progress,
            next_question=next_question,
            interpretation_status=(
                interpretation_status.value
            ),
            clarification_message=None,
        )

    def complete_diagnostic(
        self,
        diagnosis_id: str,
    ) -> CompleteDiagnosticResponse:
        with self._lock:
            session = self._get_session(diagnosis_id)

            next_question = self._find_next_question(session)

            if next_question is not None:
                raise ValueError(
                    "The diagnostic still has pending questions."
                )

            result = run_preliminary_diagnosis(
                profile=session.profile,
                answers=list(session.answers),
            )

        requirement_names = {
            requirement.requirement_id: requirement.name
            for requirement in result.questionnaire.requirements
        }

        applicability_by_requirement = {
            decision.requirement_id: decision
            for decision in result.applicability
        }

        assessments: list[RequirementAssessmentResponse] = []

        summary_values = {
            "complies_as_declared": 0,
            "does_not_comply_as_declared": 0,
            "insufficient_information": 0,
            "not_applicable": 0,
        }

        for assessment in result.assessments:
            status = assessment.status.value

            if status in summary_values:
                summary_values[status] += 1

            applicability = applicability_by_requirement[
                assessment.requirement_id
            ]

            assessments.append(
                RequirementAssessmentResponse(
                    requirement_id=assessment.requirement_id,
                    requirement_name=requirement_names[
                        assessment.requirement_id
                    ],
                    applicability_status=applicability.status.value,
                    assessment_status=status,
                    explanation=assessment.explanation,
                    missing_information=list(
                        assessment.missing_information
                    ),
                )
            )

        summary = DiagnosticSummaryResponse(
            total_requirements=len(result.assessments),
            **summary_values,
        )

        return CompleteDiagnosticResponse(
            diagnosis_id=diagnosis_id,
            assessments=assessments,
            summary=summary,
            scope_note=result.report.scope_note,
        )

    def generate_report_pdf(
        self,
        diagnosis_id: str,
    ) -> bytes:
        """
        Genera en memoria el informe PDF de un diagnóstico
        completado.

        El PDF no se almacena en disco. Después de generarlo
        correctamente, la sesión asociada al diagnóstico se
        elimina de la memoria del servicio.
        """

        with self._lock:
            session = self._get_session(diagnosis_id)

            next_question = self._find_next_question(session)

            if next_question is not None:
                raise ValueError(
                    "The diagnostic still has pending questions."
                )

            result = run_preliminary_diagnosis(
                profile=session.profile,
                answers=list(session.answers),
            )

            matrix = build_scoring_matrix(
                result.report
            )

            if not isinstance(
                matrix,
                Article27ScoringMatrix,
            ):
                raise TypeError(
                    "The selected diagnostic does not use "
                    "the Article 27 scoring matrix."
                )

            buffer = BytesIO()

            build_article27_table_pdf(
                matrix,
                buffer,
            )

            pdf_bytes = buffer.getvalue()

            if not pdf_bytes.startswith(b"%PDF-"):
                raise RuntimeError(
                    "The generated report is not a valid PDF."
                )

            del self._sessions[diagnosis_id]

        return pdf_bytes

    def _get_session(
        self,
        diagnosis_id: str,
    ) -> DiagnosticSession:
        session = self._sessions.get(diagnosis_id)

        if session is None:
            raise KeyError(
                f"Diagnostic session not found: {diagnosis_id}"
            )

        return session

    def _build_company_profile(
        self,
        payload: CreateDiagnosticRequest,
    ) -> CompanyProfile:
        """
        Construye el perfil interno usado por el agente.

        El diagnóstico expuesto por la API está limitado a
        empresas clasificadas en riesgo I y no contempla el
        flujo especial para Unidades de Producción Agropecuaria.

        La única información solicitada al usuario para
        seleccionar el paquete normativo es el número de
        trabajadores.
        """

        return CompanyProfile(
            economic_activity="No especificada",
            ciiu_code=None,
            worker_count=payload.worker_count,
            risk_class=RiskClass("I"),
            is_agricultural_production_unit=False,
            permanent_worker_count=None,
        )

    def _find_next_question(
        self,
        session: DiagnosticSession,
    ) -> QuestionResponse | None:
        total_requirements = len(session.requirements)

        for requirement_number, requirement in enumerate(
            session.requirements,
            start=1,
        ):
            requirement_answers = [
                answer
                for answer in session.answers
                if answer.requirement_id == requirement.id
            ]

            processing = process_requirement_answers(
                requirement=requirement,
                answers=requirement_answers,
            )

            if not processing.unanswered_question_ids:
                continue

            unanswered_ids = set(
                processing.unanswered_question_ids
            )

            question = next(
                question
                for question in requirement.questions
                if question.id in unanswered_ids
            )

            return self._build_question_response(
                requirement=requirement,
                question=question,
                requirement_number=requirement_number,
                total_requirements=total_requirements,
            )

        return None

    def _build_question_response(
        self,
        *,
        requirement: CatalogRequirementDefinition,
        question: CatalogQuestionDefinition,
        requirement_number: int,
        total_requirements: int,
    ) -> QuestionResponse:
        question_type = getattr(
            question.type,
            "value",
            question.type,
        )

        return QuestionResponse(
            requirement_id=requirement.id,
            requirement_name=requirement.name,
            question_id=question.id,
            text=question.text,
            role=question.role,
            question_type=str(question_type),
            requirement_number=requirement_number,
            total_requirements=total_requirements,
        )

    def _build_progress(
        self,
        *,
        session: DiagnosticSession,
        next_question: QuestionResponse | None,
    ) -> DiagnosticProgressResponse:
        completed_requirements = 0

        for requirement in session.requirements:
            requirement_answers = [
                answer
                for answer in session.answers
                if answer.requirement_id == requirement.id
            ]

            processing = process_requirement_answers(
                requirement=requirement,
                answers=requirement_answers,
            )

            if not processing.unanswered_question_ids:
                completed_requirements += 1

        if next_question is None:
            return DiagnosticProgressResponse(
                completed_requirements=completed_requirements,
                total_requirements=len(session.requirements),
                completed=True,
            )

        return DiagnosticProgressResponse(
            completed_requirements=completed_requirements,
            total_requirements=len(session.requirements),
            current_requirement_number=(
                next_question.requirement_number
            ),
            current_requirement_id=(
                next_question.requirement_id
            ),
            completed=False,
        )

    def _answer_exists(
        self,
        *,
        session: DiagnosticSession,
        requirement_id: str,
        question_id: str,
    ) -> bool:
        return any(
            answer.requirement_id == requirement_id
            and answer.question_id == question_id
            for answer in session.answers
        )
