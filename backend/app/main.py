from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import db
from .config import settings
from .errors import ApiError
from .routers import auth as auth_router
from .routers import dashboard as dashboard_router
from .routers import log_entries as log_entries_router
from .routers import snapshots as snapshots_router
from .routers import sync as sync_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_pool(settings.database_url)
    db.init_db()
    yield
    db.close_pool()


app = FastAPI(title="Torn Cashflow API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def api_error_handler(request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.message, "code": exc.code, "tornErrorCode": exc.torn_error_code}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": {"message": "Invalid request.", "code": "validation_error", "tornErrorCode": None}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": str(exc.detail), "code": "http_error", "tornErrorCode": None}},
    )


@app.get("/health")
def health() -> PlainTextResponse:
    return PlainTextResponse("ok")


app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(sync_router.router, prefix="/api/sync", tags=["sync"])
app.include_router(snapshots_router.router, prefix="/api/snapshots", tags=["snapshots"])
app.include_router(dashboard_router.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(log_entries_router.router, prefix="/api/log-entries", tags=["log-entries"])
