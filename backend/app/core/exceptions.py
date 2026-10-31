from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from jwt import ExpiredSignatureError, InvalidTokenError
from starlette.status import HTTP_401_UNAUTHORIZED


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(ExpiredSignatureError)
    async def expired_token_handler(_request: Request, _exc: ExpiredSignatureError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content={"detail": "Token has expired", "code": "token_expired"},
        )

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(_request: Request, _exc: InvalidTokenError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid token", "code": "invalid_token"},
        )
