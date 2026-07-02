from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

class NotFoundError(Exception):
    pass

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse: # type: ignore -> Decorator registers the handler internally — the function itself doesn't need to be referenced
        return JSONResponse(status_code=404, content={"detail": str(exc)})