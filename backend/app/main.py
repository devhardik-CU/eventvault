"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .db_objects import init_db
from .routers import analytics, auth, events, registrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("eventvault")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_for_runtime()
    if settings.environment != "production":  # in production run `python -m app.db_objects` once instead
        init_db()
    yield


app = FastAPI(title="EventVault API", version="1.0.0", description="Event registration & management platform.", lifespan=lifespan)

_s = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_s.cors_origin_list,
    allow_credentials=False,  # we use Bearer tokens, not cookies
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if get_settings().environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:] if not isinstance(p, int)) or "body", "message": e["msg"].removeprefix("Value error, ")} for e in exc.errors()]
    return JSONResponse({"detail": "Validation failed.", "errors": errors}, status_code=422)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)  # details go to the log only
    return JSONResponse({"detail": "Internal server error."}, status_code=500)


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}


for r in (auth.router, events.router, registrations.router, analytics.router):
    app.include_router(r)
