from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any


# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from agents.consulta_normativa.api.routes import router
from agents.consulta_normativa.api.service import QueryService
from agents.consulta_normativa.langchain_rag.main import build_runtime

ALLOWED_ORIGINS = ["http://localhost:3000"]


def create_app(runtime_builder: Callable[[], Any] | None = None) -> FastAPI:
    builder = runtime_builder or (lambda: build_runtime(write_graph_image=False)) # Cargamos dependecias de lang

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = builder()
        app.state.query_service = QueryService(runtime)
        yield

    app = FastAPI(title="SG-SST Normative RAG API", lifespan=lifespan)
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
