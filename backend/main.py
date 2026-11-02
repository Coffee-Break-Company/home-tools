"""ASGI entry point: builds the FastAPI app and wires the routers together.

The actual logic lives under the `app` package — `app.routers` for endpoints,
`app.services` for Drive/Telegram/payment logic, `app.config` for settings.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, bills, cron, expenses, health

# Uvicorn only configures its own loggers; without this the app's INFO logs
# (e.g. each expense registered by the Shortcut) never reach Render's log view.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)


async def log_ingest_validation_error(request: Request, exc: RequestValidationError):
    """The Shortcut runs unattended, so log why a request it sent was rejected.

    Rejections elsewhere are answered as usual; only the ingest route, whose
    failures would otherwise go unnoticed, gets its errors and body logged.
    """
    if request.url.path == "/api/expenses/ingest":
        logger.warning(
            "Requisição do atalho rejeitada (422): erros=%s corpo=%r",
            exc.errors(), exc.body,
        )
    return await request_validation_exception_handler(request, exc)


def create_app() -> FastAPI:
    app = FastAPI(title="Home Tools API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, log_ingest_validation_error)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(bills.router)
    app.include_router(cron.router)
    app.include_router(expenses.router)

    return app


app = create_app()
