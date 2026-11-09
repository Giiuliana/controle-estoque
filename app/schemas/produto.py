
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, Field

NomeProduto = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
    ),
]


class ProdutoCreate(BaseModel):
    nome: NomeProduto

class EntradaEstoque(BaseModel):
    quantidade: int = Field(gt=0)

class ProdutoResponse(BaseModel):
    id: int
    nome: str
    quantidade_total: int
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)

class SaidaEstoque(BaseModel):
    quantidade: int = Field(gt=0)

class ReservaEstoque(BaseModel):
    solicitacao_id: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=100,
        ),
    ]

    quantidade: int = Field(gt=0)

class BloqueioEstoque(BaseModel):
    quantidade: int = Field(gt=0)

class RetencaoResponse(BaseModel):
    id: int
    produto_id: int
    solicitacao_id: str | None
    tipo: str
    quantidade: int
    status: str
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)

class EstoqueResponse(BaseModel):
    produto_id: int
    nome: str
    quantidade_total: int
    quantidade_reservada: int
    quantidade_bloqueada: int
    quantidade_disponivel: int


