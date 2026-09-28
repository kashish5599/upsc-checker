from fastapi import FastAPI

from backend.api.routes.evaluate import router as evaluate_router
from backend.api.routes.knowledge import router as knowledge_router


def create_app() -> FastAPI:
    app = FastAPI(title="UPSC Copy Checker API")
    app.include_router(evaluate_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1/knowledge")

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "UPSC Copy Checker API is running"}

    return app
