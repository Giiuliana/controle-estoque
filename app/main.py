
from fastapi import FastAPI

from app.api.produtos import router as produtos_router


app = FastAPI(
    title="API de Controle de Estoque",
    description="API para gerenciamento de produtos e operações de estoque.",
    version="0.1.0",
)

app.include_router(produtos_router)


@app.get("/health", tags=["Sistema"])
def verificar_saude():
    return {"status": "ok"}
