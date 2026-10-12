import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents.diagnostico_cumplimiento.api.routes import router
from agents.diagnostico_cumplimiento.api.schemas import (
    CompleteDiagnosticResponse,
    CreateDiagnosticRequest,
    CreateDiagnosticResponse,
    DiagnosticProgressResponse,
    DiagnosticSummaryResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from agents.diagnostico_cumplimiento.api.service import DiagnosticService


class FakeDiagnosticService(DiagnosticService):
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def create_diagnostic(
        self,
        payload: CreateDiagnosticRequest,
    ) -> CreateDiagnosticResponse:
        self.calls.append(("create", payload))
        return CreateDiagnosticResponse(
            diagnosis_id="diagnosis-1",
            catalog_id="catalog-1",
            catalog_name="Risk I",
            progress=DiagnosticProgressResponse(
                completed_requirements=0,
                total_requirements=1,
                current_requirement_number=1,
                current_requirement_id="requirement-1",
                completed=False,
            ),
            next_question=None,
        )

    def submit_answer(
        self,
        diagnosis_id: str,
        payload: SubmitAnswerRequest,
    ) -> SubmitAnswerResponse:
        self.calls.append(("answer", (diagnosis_id, payload)))
        return SubmitAnswerResponse(
            diagnosis_id=diagnosis_id,
            progress=DiagnosticProgressResponse(
                completed_requirements=1,
                total_requirements=1,
                completed=True,
            ),
            next_question=None,
            interpretation_status="affirmative",
            clarification_message=None,
        )

    def complete_diagnostic(
        self,
        diagnosis_id: str,
    ) -> CompleteDiagnosticResponse:
        self.calls.append(("complete", diagnosis_id))
        return CompleteDiagnosticResponse(
            diagnosis_id=diagnosis_id,
            assessments=[],
            summary=DiagnosticSummaryResponse(total_requirements=0),
            scope_note="Preliminary result.",
        )

    def generate_report_pdf(self, diagnosis_id: str) -> bytes:
        self.calls.append(("report", diagnosis_id))
        return b"%PDF-1.4 fake"


class MissingDiagnosticService(FakeDiagnosticService):
    def submit_answer(
        self,
        diagnosis_id: str,
        payload: SubmitAnswerRequest,
    ) -> SubmitAnswerResponse:
        raise KeyError(diagnosis_id)


class PendingDiagnosticService(FakeDiagnosticService):
    def complete_diagnostic(
        self,
        diagnosis_id: str,
    ) -> CompleteDiagnosticResponse:
        raise ValueError("The diagnostic still has pending questions.")


def create_test_app(service: DiagnosticService) -> FastAPI:
    application = FastAPI()
    application.state.diagnostic_service = service
    application.include_router(router)
    return application


class DiagnosticApiRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FakeDiagnosticService()
        self.client = TestClient(create_test_app(self.service))

    def test_create_diagnostic_preserves_contract(self) -> None:
        response = self.client.post(
            "/api/v1/diagnostics",
            json={"worker_count": 5, "company_name": "Example"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["diagnosis_id"], "diagnosis-1")
        self.assertEqual(self.service.calls[0][0], "create")

    def test_submit_answer_preserves_contract(self) -> None:
        response = self.client.post(
            "/api/v1/diagnostics/diagnosis-1/answers",
            json={
                "requirement_id": "requirement-1",
                "question_id": "question-1",
                "answer": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["interpretation_status"], "affirmative")
        self.assertEqual(self.service.calls[0][0], "answer")

    def test_complete_diagnostic_preserves_contract(self) -> None:
        response = self.client.post(
            "/api/v1/diagnostics/diagnosis-1/complete"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scope_note"], "Preliminary result.")
        self.assertEqual(self.service.calls, [("complete", "diagnosis-1")])

    def test_report_preserves_pdf_contract(self) -> None:
        response = self.client.get(
            "/api/v1/diagnostics/diagnosis-1/report"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-1.4 fake")
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(
            response.headers["content-disposition"],
            'inline; filename="diagnostico_sgsst.pdf"',
        )
        self.assertEqual(
            response.headers["cache-control"],
            "private, no-store, max-age=0",
        )

    def test_missing_session_returns_not_found(self) -> None:
        client = TestClient(create_test_app(MissingDiagnosticService()))

        response = client.post(
            "/api/v1/diagnostics/missing/answers",
            json={
                "requirement_id": "requirement-1",
                "question_id": "question-1",
                "answer": False,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {"detail": "Diagnostic session not found."},
        )

    def test_pending_diagnostic_returns_conflict(self) -> None:
        client = TestClient(create_test_app(PendingDiagnosticService()))

        response = client.post("/api/v1/diagnostics/diagnosis-1/complete")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {"detail": "The diagnostic still has pending questions."},
        )

    def test_router_has_no_health_endpoint(self) -> None:
        response = self.client.get("/api/v1/diagnostics/health")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
