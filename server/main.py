"""Remote wallpaper server - FastAPI application.

This is the server-side component that provides:
- Wallpaper catalog API (public)
- User authentication (register, login, JWT)
- Premium wallpaper access control
- Download tracking
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tux_wallpaper.server.api import router as api_router
from tux_wallpaper.server.core.config import ServerConfig, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    settings.ensure_directories()
    yield


app = FastAPI(
    title="Tux Wallpaper Server",
    version="0.1.0",
    description="Remote wallpaper service API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "tux_wallpaper.server.main:app",
        host="0.0.0.0",
        port=18420,
        reload=True,
    )
