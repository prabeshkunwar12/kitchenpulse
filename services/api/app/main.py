import os
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.db import engine
from app.inventory.routes import router
from app.inventory.service import InventoryError

app = FastAPI(title="KitchenPulse", version="0.2.0")
app.include_router(router)

preview_origin = os.environ.get("WEB_PREVIEW_ORIGIN", "")
if preview_origin:
    if not re.fullmatch(r"http://(127\.0\.0\.1|localhost):[0-9]{1,5}", preview_origin):
        raise RuntimeError("WEB_PREVIEW_ORIGIN must be an explicit HTTP loopback origin.")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[preview_origin],
        allow_methods=["GET", "PATCH", "POST"],
        allow_headers=["Content-Type"],
    )


def error_response(status: int, code: str, message: str, **details):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, **details}},
    )


@app.exception_handler(InventoryError)
async def inventory_error(_request: Request, error: InventoryError):
    return error_response(error.status, error.code, str(error))


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, error: RequestValidationError):
    fields = [{"path": list(entry["loc"]), "message": entry["msg"]} for entry in error.errors()]
    return error_response(422, "invalid_request", "Check the supplied values.", fields=fields)


@app.exception_handler(HTTPException)
async def http_error(_request: Request, error: HTTPException):
    response = error_response(error.status_code, "http_error", str(error.detail))
    if error.headers:
        response.headers.update(error.headers)
    return response


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM stock_transactions LIMIT 1"))
    except SQLAlchemyError:
        return error_response(503, "database_unavailable", "The inventory database is unavailable.")
    return {"status": "ok"}
