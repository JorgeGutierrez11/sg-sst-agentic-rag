import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

with (
    patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "https://test.example"}),
    patch("dotenv.load_dotenv"),
):
    from agents.api import main as api_main
    from agents.api.main import create_app
    from agents.consulta_normativa.api.service import QueryService
    from agents.diagnostico_cumplimiento.api.service import DiagnosticService


class FakeRuntime:
    def __init__(self) -> None:
        self.graph = object()

    def answer_with_langgraph(
        self,
        question: str,
        graph: object,
        *,
        thread_id: str,
    ) -> object:
        return SimpleNamespace(
            answer="Answer",
            references=[],
            chunks=[],
        )


class UnifiedApiAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(
            os.environ,
            {"CORS_ALLOWED_ORIGINS": "http://localhost:3000"},
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()

    def test_lifespan_builds_and_exposes_each_service_once(self) -> None:
        runtime = FakeRuntime()
        diagnostic_service = DiagnosticService()
        runtime_calls: list[str] = []
        diagnostic_calls: list[str] = []

        def build_runtime() -> FakeRuntime:
            runtime_calls.append("built")
            return runtime

        def build_diagnostic_service() -> DiagnosticService:
            diagnostic_calls.append("built")
            return diagnostic_service

        application = create_app(
            runtime_builder=build_runtime,
            diagnostic_service_builder=build_diagnostic_service,
        )

        with TestClient(application) as client:
            liveness_response = client.get("/health")
            readiness_response = client.get("/health/ready")
            query_service = application.state.query_service
            stored_diagnostic_service = application.state.diagnostic_service
            self.assertTrue(application.state.is_ready)

        self.assertEqual(liveness_response.status_code, 200)
        self.assertEqual(liveness_response.json(), {"status": "ok"})
        self.assertEqual(readiness_response.status_code, 200)
        self.assertEqual(readiness_response.json(), {"status": "ready"})
        self.assertFalse(application.state.is_ready)
        self.assertEqual(runtime_calls, ["built"])
        self.assertEqual(diagnostic_calls, ["built"])
        self.assertIsInstance(query_service, QueryService)
        self.assertIs(query_service.runtime, runtime)
        self.assertIs(stored_diagnostic_service, diagnostic_service)

    def test_default_runtime_builder_suppresses_graph_image_generation(self) -> None:
        with patch.object(
            api_main,
            "build_runtime",
            return_value=FakeRuntime(),
        ) as build_runtime:
            application = create_app()

            with TestClient(application) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        build_runtime.assert_called_once_with(write_graph_image=False)

    def test_startup_propagates_service_builder_failures(self) -> None:
        def fail_runtime() -> FakeRuntime:
            raise RuntimeError("runtime unavailable")

        def fail_diagnostic_service() -> DiagnosticService:
            raise RuntimeError("diagnostic unavailable")

        cases = (
            create_app(
                runtime_builder=fail_runtime,
                diagnostic_service_builder=DiagnosticService,
            ),
            create_app(
                runtime_builder=FakeRuntime,
                diagnostic_service_builder=fail_diagnostic_service,
            ),
        )

        for application in cases:
            with self.subTest(application=application):
                with self.assertRaises(RuntimeError):
                    with TestClient(application):
                        pass
                self.assertFalse(application.state.is_ready)

    def test_startup_failure_is_logged_and_readiness_stays_false(self) -> None:
        def fail_runtime() -> FakeRuntime:
            raise RuntimeError("runtime unavailable")

        application = create_app(
            runtime_builder=fail_runtime,
            diagnostic_service_builder=DiagnosticService,
        )

        with self.assertLogs("agents.api.main", level="ERROR") as logs:
            with self.assertRaises(RuntimeError):
                with TestClient(application):
                    pass

        self.assertFalse(application.state.is_ready)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("API startup failed", logs.output[0])
        self.assertIn("runtime unavailable", logs.output[0])

    def test_liveness_ignores_readiness_and_missing_services(self) -> None:
        application = create_app(
            runtime_builder=lambda: self.fail("runtime builder called"),
            diagnostic_service_builder=lambda: self.fail(
                "diagnostic service builder called"
            ),
        )
        application.state.is_ready = True

        client = TestClient(application)
        response = client.get("/health")
        client.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_does_not_build_or_call_services(self) -> None:
        builder_calls: list[str] = []

        def build_runtime() -> FakeRuntime:
            builder_calls.append("runtime")
            return FakeRuntime()

        def build_diagnostic_service() -> DiagnosticService:
            builder_calls.append("diagnostic")
            return DiagnosticService()

        application = create_app(
            runtime_builder=build_runtime,
            diagnostic_service_builder=build_diagnostic_service,
        )

        client = TestClient(application)
        response = client.get("/health/ready")
        client.close()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Service unavailable."})
        self.assertEqual(builder_calls, [])

    def test_readiness_requires_both_service_attributes(self) -> None:
        application = create_app(
            runtime_builder=lambda: self.fail("runtime builder called"),
            diagnostic_service_builder=lambda: self.fail(
                "diagnostic service builder called"
            ),
        )
        application.state.is_ready = True

        client = TestClient(application)
        missing_both_response = client.get("/health/ready")
        application.state.query_service = object()
        missing_diagnostic_response = client.get("/health/ready")
        client.close()

        self.assertEqual(missing_both_response.status_code, 503)
        self.assertEqual(missing_diagnostic_response.status_code, 503)

    def test_registers_exact_functional_route_inventory(self) -> None:
        application = create_app(
            runtime_builder=FakeRuntime,
            diagnostic_service_builder=DiagnosticService,
        )
        route_inventory = {
            (method.upper(), path)
            for path, operations in application.openapi()["paths"].items()
            for method in operations
        }

        self.assertEqual(
            route_inventory,
            {
                ("GET", "/health"),
                ("GET", "/health/ready"),
                ("POST", "/api/v1/query"),
                ("POST", "/api/v1/diagnostics"),
                ("POST", "/api/v1/diagnostics/{diagnosis_id}/answers"),
                ("POST", "/api/v1/diagnostics/{diagnosis_id}/complete"),
                ("GET", "/api/v1/diagnostics/{diagnosis_id}/report"),
            },
        )

    def test_configures_cors_once_for_environment_origin(self) -> None:
        configured_origin = "https://frontend.example.test"
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": configured_origin}):
            application = create_app(
                runtime_builder=FakeRuntime,
                diagnostic_service_builder=DiagnosticService,
            )
            cors_middleware = [
                middleware
                for middleware in application.user_middleware
                if middleware.cls is CORSMiddleware
            ]

            with TestClient(application) as client:
                response = client.options(
                    "/api/v1/query",
                    headers={
                        "Origin": configured_origin,
                        "Access-Control-Request-Method": "POST",
                    },
                )

        self.assertEqual(len(cors_middleware), 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            configured_origin,
        )
        self.assertEqual(
            response.headers["access-control-allow-credentials"],
            "true",
        )

    def test_agent_specific_entrypoints_reexport_unified_objects(self) -> None:
        from agents.consulta_normativa.api import main as query_main
        from agents.diagnostico_cumplimiento.api import main as diagnostic_main

        self.assertIs(query_main.app, api_main.app)
        self.assertIs(diagnostic_main.app, api_main.app)
        self.assertIs(query_main.create_app, api_main.create_app)
        self.assertIs(diagnostic_main.create_app, api_main.create_app)


if __name__ == "__main__":
    unittest.main()
