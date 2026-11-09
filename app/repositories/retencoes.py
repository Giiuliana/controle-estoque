from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.retencao import Retencao


def adicionar_retencao(
    db: Session,
    retencao: Retencao,
) -> None:
    db.add(retencao)


def buscar_retencao_por_id(
    db: Session,
    produto_id: int,
    retencao_id: int,
) -> Retencao | None:
    consulta = select(Retencao).where(
        Retencao.id == retencao_id,
        Retencao.produto_id == produto_id,
    )

    return db.scalar(consulta)

def listar_retencoes_por_produto(
    db: Session,
    produto_id: int,
) -> list[Retencao]:
    consulta = (
        select(Retencao)
        .where(Retencao.produto_id == produto_id)
        .order_by(Retencao.id)
    )

    return list(db.scalars(consulta).all())