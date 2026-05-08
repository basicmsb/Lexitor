from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from src.api.routes import analyses as analyses_routes
from src.api.routes import auth as auth_routes
from src.api.routes import documents as documents_routes
from src.api.routes import knowledge as knowledge_routes
from src.api.routes import labels as labels_routes
from src.api.routes import projects as projects_routes
from src.db.session import SessionLocal
from src.models import Analysis, AnalysisStatus
from src.utils.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Mark *stale* PENDING/RUNNING analyses as ERROR — anything that has
    # not had progress in ≥5 minutes is almost certainly orphaned by a
    # previous uvicorn process. Recent analyses (likely just kicked off
    # in the same dev session) are left alone so the running asyncio
    # task can keep going across hot-reloads.
    async with SessionLocal() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        await session.execute(
            update(Analysis)
            .where(
                Analysis.status.in_([AnalysisStatus.PENDING, AnalysisStatus.RUNNING]),
                Analysis.updated_at < cutoff,
            )
            .values(
                status=AnalysisStatus.ERROR,
                error_message="Backend je restartan tijekom analize. Pokreni ponovno.",
            )
        )
        await session.commit()
    yield

app = FastAPI(
    title="Lexitor API",
    description="AI asistent za usklađenost dokumentacije javne nabave",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(documents_routes.router)
app.include_router(analyses_routes.router)
app.include_router(knowledge_routes.router)
app.include_router(projects_routes.router)
app.include_router(labels_routes.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"name": "Lexitor", "version": "0.0.1"}
