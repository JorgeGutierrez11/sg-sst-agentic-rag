import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents.diagnostico_cumplimiento.api import service as service_module
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
from agents.diagnostico_cumplimiento.catalog import loader as catalog_loader
from agents.diagnostico_cumplimiento.catalog.loader import CatalogLoadError
from agents.diagnostico_cumplimiento.catalog.selector import CATALOG_FILES

CATALOG_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "valid_catalog.json"


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

    def get_diagnostic(self, diagnosis_id: str):
        raise KeyError(diagnosis_id)

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
                "revision": 0,
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
                "revision": 0,
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


class DiagnosticServiceCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.valid_path = Path(self.temp_dir.name) / "valid.json"
        shutil.copyfile(CATALOG_FIXTURE_PATH, self.valid_path)

    def write_catalog(self, name: str, content: str) -> Path:
        path = Path(self.temp_dir.name) / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_invalid_json_catalog_prevents_service_construction(self) -> None:
        broken_path = self.write_catalog("broken.json", "{not json")

        with self.assertRaisesRegex(CatalogLoadError, "invalid JSON"):
            DiagnosticService(catalog_paths=(self.valid_path, broken_path))

    def test_schema_invalid_catalog_prevents_service_construction(self) -> None:
        invalid_path = self.write_catalog("invalid.json", "{}")

        with self.assertRaisesRegex(CatalogLoadError, "expected schema"):
            DiagnosticService(catalog_paths=(self.valid_path, invalid_path))

    def test_broken_agricultural_catalog_does_not_prevent_construction(self) -> None:
        agricultural_path = CATALOG_FILES["risk_i_1_10_agricultural"]
        real_load_catalog = service_module.load_catalog

        def load_catalog_except_agricultural(path: Path) -> object:
            if Path(path) == agricultural_path:
                raise CatalogLoadError("broken agricultural catalog")
            return real_load_catalog(path)

        with patch.object(
            service_module,
            "load_catalog",
            side_effect=load_catalog_except_agricultural,
        ):
            DiagnosticService()

    def test_create_diagnostic_does_not_read_catalog_files(self) -> None:
        service = DiagnosticService()

        with patch.object(
            catalog_loader,
            "load_catalog",
            side_effect=AssertionError("catalog read during a request"),
        ), patch.object(
            service_module,
            "load_catalog",
            side_effect=AssertionError("catalog read during a request"),
        ):
            response = service.create_diagnostic(
                CreateDiagnosticRequest(worker_count=5)
            )

        self.assertEqual(response.catalog_id, "res0312_riesgo_i_1_10_general")

    def test_each_worker_tier_keeps_catalog_and_first_question(self) -> None:
        service = DiagnosticService()
        expected = {
            1: ("res0312_riesgo_i_1_10_general", "q_designer_assigned", 7),
            10: ("res0312_riesgo_i_1_10_general", "q_designer_assigned", 7),
            11: ("res0312_riesgo_i_11_50", "q_sgsst_designer_assigned", 21),
            50: ("res0312_riesgo_i_11_50", "q_sgsst_designer_assigned", 21),
            51: ("res0312_riesgo_i_51_plus", "q_111_primary", 60),
        }

        for worker_count, (catalog_id, question_id, total) in expected.items():
            with self.subTest(worker_count=worker_count):
                response = service.create_diagnostic(
                    CreateDiagnosticRequest(worker_count=worker_count)
                )

                self.assertEqual(response.catalog_id, catalog_id)
                self.assertEqual(response.next_question.question_id, question_id)
                self.assertEqual(response.progress.total_requirements, total)


if __name__ == "__main__":
    unittest.main()
