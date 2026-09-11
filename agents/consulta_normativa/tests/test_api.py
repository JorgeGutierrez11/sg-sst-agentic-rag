import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agents.consulta_normativa.api import main as api_main
from agents.consulta_normativa.api.dependencies import get_query_service
from agents.consulta_normativa.api.main import create_app
from agents.consulta_normativa.api.routes import router
from agents.consulta_normativa.api.schemas import QueryRequest, QueryResponse
from agents.consulta_normativa.api.service import QueryService


class ApiSchemaTests(unittest.TestCase):
    def test_query_request_rejects_blank_question(self) -> None:
        with self.assertRaises(ValidationError):
            QueryRequest(question="   ")

    def test_query_request_trims_question(self) -> None:
        request = QueryRequest(question="  ¿Qué es SG-SST?  ")

        self.assertEqual(request.question, "¿Qué es SG-SST?")

    def test_query_response_shape(self) -> None:
        response = QueryResponse(
            answer="Respuesta",
            references=["Referencia"],
            chunks=["Fragmento"],
            conversation_id="abc",
        )

        self.assertEqual(response.answer, "Respuesta")
        self.assertEqual(response.references, ["Referencia"])
        self.assertEqual(response.chunks, ["Fragmento"])
        self.assertEqual(response.conversation_id, "abc")


class FakeRuntime:
    def __init__(self) -> None:
        self.graph = object()
        self.invocations: list[tuple[str, str]] = []

    def answer_with_langgraph(self, question: str, graph: object, *, thread_id: str) -> object:
        self.invocations.append((question, thread_id))
        return SimpleNamespace(
            answer="Respuesta",
            references=["Ref"],
            chunks=["Fragmento"],
            context="ctx",
            prompt="prompt",
        )


class QueryServiceTests(unittest.TestCase):
    def test_ask_returns_response_with_given_conversation_id(self) -> None:
        runtime = FakeRuntime()
        service = QueryService(runtime)

        response = service.ask("¿Qué es el SG-SST?", conversation_id="abc")

        self.assertEqual(response.answer, "Respuesta")
        self.assertEqual(response.references, ["Ref"])
        self.assertEqual(response.chunks, ["Fragmento"])
        self.assertEqual(response.conversation_id, "abc")
        self.assertEqual(runtime.invocations, [("¿Qué es el SG-SST?", "abc")])

    def test_ask_generates_conversation_id_when_missing(self) -> None:
        runtime = FakeRuntime()
        service = QueryService(runtime)

        response = service.ask("¿Qué es el SG-SST?")

        UUID(response.conversation_id)
        self.assertEqual(runtime.invocations, [("¿Qué es el SG-SST?", response.conversation_id)])

    def test_conversation_ids_preserve_continuity_and_isolation(self) -> None:
        runtime = FakeRuntime()
        service = QueryService(runtime)

        first = service.ask("Primera pregunta", conversation_id="conversation-a")
        follow_up = service.ask("Pregunta de seguimiento", conversation_id=first.conversation_id)
        separate = service.ask("Otra empresa", conversation_id="conversation-b")

        self.assertEqual(follow_up.conversation_id, "conversation-a")
        self.assertEqual(separate.conversation_id, "conversation-b")
        self.assertEqual(
            runtime.invocations,
            [
                ("Primera pregunta", "conversation-a"),
                ("Pregunta de seguimiento", "conversation-a"),
                ("Otra empresa", "conversation-b"),
            ],
        )


class ApiDependencyTests(unittest.TestCase):
    def test_get_query_service_fails_when_service_missing(self) -> None:
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

        with self.assertRaises(RuntimeError):
            get_query_service(request)


class FailingQueryService(QueryService):
    def __init__(self) -> None:
        super().__init__(FakeRuntime())

    def ask(self, question: str, conversation_id: str | None = None) -> QueryResponse:
        raise RuntimeError("secret details")


def create_test_app(service: QueryService) -> FastAPI:
    app = FastAPI()
    app.state.query_service = service
    app.include_router(router)
    return app


class ApiRouteTests(unittest.TestCase):
    def test_health_returns_ok(self) -> None:
        app = create_test_app(QueryService(FakeRuntime()))
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_query_returns_answer(self) -> None:
        app = create_test_app(QueryService(FakeRuntime()))
        client = TestClient(app)

        response = client.post(
            "/api/v1/query",
            json={"question": "¿Qué es SG-SST?", "conversation_id": "abc"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Respuesta")
        self.assertEqual(response.json()["references"], ["Ref"])
        self.assertEqual(response.json()["chunks"], ["Fragmento"])
        self.assertEqual(response.json()["conversation_id"], "abc")

    def test_query_rejects_blank_question(self) -> None:
        app = create_test_app(QueryService(FakeRuntime()))
        client = TestClient(app)

        response = client.post("/api/v1/query", json={"question": "   "})

        self.assertEqual(response.status_code, 422)

    def test_query_failure_returns_sanitized_error(self) -> None:
        app = create_test_app(FailingQueryService())
        client = TestClient(app)

        with self.assertLogs("agents.consulta_normativa.api.routes", level="ERROR"):
            response = client.post(
                "/api/v1/query",
                json={"question": "¿Qué es SG-SST?", "conversation_id": "abc"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "The normative consultation service is temporarily unavailable."})
        self.assertNotIn("secret details", response.text)


class ApiAppTests(unittest.TestCase):
    def test_default_lifespan_suppresses_graph_image_generation(self) -> None:
        with patch.object(api_main, "build_runtime", return_value=FakeRuntime()) as build_runtime:
            app = create_app()

            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        build_runtime.assert_called_once_with(write_graph_image=False)

    def test_app_lifespan_builds_query_service_once(self) -> None:
        calls = []

        def runtime_builder() -> FakeRuntime:
            calls.append("built")
            return FakeRuntime()

        app = create_app(runtime_builder=runtime_builder)

        with TestClient(app) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, ["built"])

    def test_app_allows_localhost_frontend_origin(self) -> None:
        app = create_app(runtime_builder=FakeRuntime)

        with TestClient(app) as client:
            response = client.options(
                "/api/v1/query",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")


if __name__ == "__main__":
    unittest.main()
