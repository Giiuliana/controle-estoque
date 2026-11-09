from sqlalchemy.orm import Session
from app.models.produto import Produto
from app.models.retencao import Retencao
from sqlalchemy import select, func, case


def adicionar_produto(
    db: Session,
    produto: Produto,
) -> None:
    db.add(produto)


def buscar_produto_por_id(
    db: Session,
    produto_id: int,
) -> Produto | None:
    consulta = (
        select(Produto)
        .where(Produto.id == produto_id)
        .with_for_update()
    )

    return db.scalar(consulta)

def obter_quantidade_retida(
    db: Session,
    produto_id: int,
) -> int:

    consulta = (
        select(func.coalesce(func.sum(Retencao.quantidade), 0))
        .where(
            Retencao.produto_id == produto_id,
            Retencao.status == "ATIVA",
            Retencao.tipo.in_(["RESERVA", "BLOQUEIO"]),
        )
    )

    return db.scalar(consulta)

def obter_quantidades_retidas(
    db: Session,
    produto_id: int,
) -> dict[str, int]:

    consulta = select(
        func.coalesce(
            func.sum(
                case(
                    (Retencao.tipo == "RESERVA", Retencao.quantidade),
                    else_=0,
                )
            ),
            0,
        ),
        func.coalesce(
            func.sum(
                case(
                    (Retencao.tipo == "BLOQUEIO", Retencao.quantidade),
                    else_=0,
                )
            ),
            0,
        ),
    ).where(
        Retencao.produto_id == produto_id,
        Retencao.status == "ATIVA",
    )

    quantidade_reservada, quantidade_bloqueada = db.execute(
        consulta
    ).one()

    return {
        "quantidade_reservada": quantidade_reservada,
        "quantidade_bloqueada": quantidade_bloqueada,
    }

def buscar_produto_para_consulta(
    db: Session,
    produto_id: int,
) -> Produto | None:
    consulta = select(Produto).where(
        Produto.id == produto_id
    )

    return db.scalar(consulta)