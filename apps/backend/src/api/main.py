from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import auth as auth_routes
from src.api.routes import documents as documents_routes
from src.utils.config import settings

app = FastAPI(
    title="Lexitor API",
    description="AI asistent za usklađenost dokumentacije javne nabave",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"name": "Lexitor", "version": "0.0.1"}
