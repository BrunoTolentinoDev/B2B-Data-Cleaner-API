import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def _validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for err in exc.errors():
        item: dict[str, Any] = {
            "loc": err.get("loc", []),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        details.append(item)
    return details


def register_exception_handlers(app: FastAPI) -> None:
    from app.services.cleaning_service import AIResponseError

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Erro de validação da requisição.",
                "errors": _validation_details(exc),
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        # Pydantic ValidationError (fallback para casos fora do RequestValidationError)
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Erro de validação de dados.",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(AIResponseError)
    async def ai_response_error_handler(
        request: Request,
        exc: AIResponseError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "detail": "Falha ao padronizar nome com a IA.",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(json.JSONDecodeError)
    async def json_decode_error_handler(
        request: Request,
        exc: json.JSONDecodeError,
    ) -> JSONResponse:
        # Evita vazar detalhes internos quando a IA retorna conteúdo inválido.
        return JSONResponse(
            status_code=502,
            content={"detail": "Resposta inválida recebida da IA."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        # Importante: não vaza stacktrace/erros internos em produção.
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Erro interno inesperado.",
            },
        )

