import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, Request
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from agents.api.config import get_cors_allowed_origins
from agents.consulta_normativa.api.routes import router as query_router
from agents.consulta_normativa.api.service import QueryService
from agents.consulta_normativa.langchain_rag.main import build_runtime
from agents.diagnostico_cumplimiento.api.routes import router as diagnostic_router
from agents.diagnostico_cumplimiento.api.service import DiagnosticService

logger = logging.getLogger(__name__)

def create_app(
    runtime_builder: Callable[[], Any] | None = None,
    diagnostic_service_builder: Callable[[], DiagnosticService] | None = None,
) -> FastAPI:
    """Create the shared API without initializing services before startup."""
    build_rag_runtime = runtime_builder or (
        lambda: build_runtime(write_graph_image=False)
    )
    build_diagnostic_service = diagnostic_service_builder or DiagnosticService

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.is_ready = False
        try:
            runtime = build_rag_runtime()
            application.state.query_service = QueryService(runtime)
            application.state.diagnostic_service = build_diagnostic_service()
        except Exception:
            logger.exception("API startup failed; the service will not report readiness.")
            raise

        application.state.is_ready = True
        try:
            yield
        finally:
            application.state.is_ready = False

    application = FastAPI(
        title="SG-SST Agent API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready")
    def readiness(request: Request) -> dict[str, str]:
        state = request.app.state
        if not (
            getattr(state, "is_ready", False)
            and hasattr(state, "query_service")
            and hasattr(state, "diagnostic_service")
        ):
            raise HTTPException(
                status_code=503,
                detail="Service unavailable.",
            )

        return {"status": "ready"}

    application.include_router(query_router)
    application.include_router(diagnostic_router)
    return application


app = create_app()
