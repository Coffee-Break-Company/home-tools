"""ASGI entry point: builds the FastAPI app and wires the routers together.

The actual logic lives under the `app` package — `app.routers` for endpoints,
`app.services` for Drive/Telegram/payment logic, `app.config` for settings.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, bills, cron, health


def create_app() -> FastAPI:
    app = FastAPI(title="Home Tools API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(bills.router)
    app.include_router(cron.router)

    return app


app = create_app()
