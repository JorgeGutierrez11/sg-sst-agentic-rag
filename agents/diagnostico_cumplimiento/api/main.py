from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from agents.diagnostico_cumplimiento.api.routes import router
from agents.diagnostico_cumplimiento.api.service import (
    DiagnosticService,
)


ALLOWED_ORIGINS = ["http://localhost:3000"]


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.diagnostic_service = DiagnosticService()
        yield

    app = FastAPI(
        title="SG-SST Diagnostic API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
