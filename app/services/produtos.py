from sqlalchemy.orm import Session

from app.models.produto import Produto
from app.models.retencao import Retencao

from app.repositories.produtos import (
    adicionar_produto,
    buscar_produto_por_id,
    buscar_produto_para_consulta,
    obter_quantidade_retida,
    obter_quantidades_retidas,
)

from app.repositories.retencoes import (
    adicionar_retencao,
    buscar_retencao_por_id,
    listar_retencoes_por_produto,
)

from app.schemas.produto import ProdutoCreate


class ProdutoNaoEncontradoError(Exception):
    pass

class EstoqueInsuficienteError(Exception):
    pass

class RetencaoNaoEncontradaError(Exception):
    pass


class RetencaoJaLiberadaError(Exception):
    pass

def cadastrar_produto(
    db: Session,
    dados: ProdutoCreate,
) -> Produto:
    produto = Produto(
        nome=dados.nome,
        quantidade_total=0,
    )

    try:
        adicionar_produto(db, produto)
        db.commit()
        db.refresh(produto)

    except Exception:
        db.rollback()
        raise

    return produto

def registrar_entrada(
    db: Session,
    produto_id: int,
    quantidade: int,
) -> Produto:

    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    try:
        produto = buscar_produto_por_id(db, produto_id)

        if produto is None:
            raise ProdutoNaoEncontradoError(
                "Produto não encontrado."
            )

        produto.quantidade_total += quantidade

        db.commit()
        db.refresh(produto)

    except Exception:
        db.rollback()
        raise

    return produto

def registrar_saida(
    db: Session,
    produto_id: int,
    quantidade: int,
) -> Produto:
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    try:
        # Busca o produto e bloqueia sua linha durante a transação.
        produto = buscar_produto_por_id(db, produto_id)

        if produto is None:
            raise ProdutoNaoEncontradoError("Produto não encontrado.")

        # Soma as quantidades que estão reservadas ou bloqueadas.
        quantidade_retida = obter_quantidade_retida(db, produto_id)

        # Calcula o estoque que realmente pode ser retirado.
        quantidade_disponivel = (
            produto.quantidade_total - quantidade_retida
        )

        if quantidade > quantidade_disponivel:
            raise EstoqueInsuficienteError(
                "Quantidade solicitada maior que o estoque disponível."
            )

        # Atualiza o estoque total.
        produto.quantidade_total -= quantidade

        db.commit()
        db.refresh(produto)

    except Exception:
        db.rollback()
        raise

    return produto

def registrar_reserva(
    db: Session,
    produto_id: int,
    solicitacao_id: str,
    quantidade: int,
) -> Retencao:
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    try:
        # Busca o produto e bloqueia sua linha durante a transação.
        produto = buscar_produto_por_id(db, produto_id)

        if produto is None:
            raise ProdutoNaoEncontradoError(
                "Produto não encontrado."
            )

        # Consulta as reservas e os bloqueios ativos.
        quantidade_retida = obter_quantidade_retida(
            db,
            produto_id,
        )

        # Calcula a quantidade disponível.
        quantidade_disponivel = (
            produto.quantidade_total - quantidade_retida
        )

        if quantidade > quantidade_disponivel:
            raise EstoqueInsuficienteError(
                "Quantidade solicitada maior que o estoque disponível."
            )

        # Cria o registro da reserva.
        retencao = Retencao(
            produto_id=produto_id,
            solicitacao_id=solicitacao_id,
            tipo="RESERVA",
            quantidade=quantidade,
            status="ATIVA",
        )

        adicionar_retencao(db, retencao)

        db.commit()
        db.refresh(retencao)

    except Exception:
        db.rollback()
        raise

    return retencao

def registrar_bloqueio(
    db: Session,
    produto_id: int,
    quantidade: int,
) -> Retencao:
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    try:
        # Busca o produto e bloqueia sua linha durante a transação.
        produto = buscar_produto_por_id(db, produto_id)

        if produto is None:
            raise ProdutoNaoEncontradoError(
                "Produto não encontrado."
            )

        # Consulta as reservas e os bloqueios ativos.
        quantidade_retida = obter_quantidade_retida(
            db,
            produto_id,
        )

        # Calcula o estoque disponível.
        quantidade_disponivel = (
            produto.quantidade_total - quantidade_retida
        )

        if quantidade > quantidade_disponivel:
            raise EstoqueInsuficienteError(
                "Quantidade solicitada maior que o estoque disponível."
            )

        # Cria o registro do bloqueio.
        retencao = Retencao(
            produto_id=produto_id,
            solicitacao_id=None,
            tipo="BLOQUEIO",
            quantidade=quantidade,
            status="ATIVA",
        )

        adicionar_retencao(db, retencao)

        db.commit()
        db.refresh(retencao)

    except Exception:
        db.rollback()
        raise

    return retencao

def liberar_retencao(
    db: Session,
    produto_id: int,
    retencao_id: int,
) -> Retencao:

    try:
        # Busca o produto e bloqueia sua linha durante a transação.
        produto = buscar_produto_por_id(db, produto_id)

        if produto is None:
            raise ProdutoNaoEncontradoError(
                "Produto não encontrado."
            )

        # Busca a reserva ou o bloqueio vinculado ao produto.
        retencao = buscar_retencao_por_id(
            db,
            produto_id,
            retencao_id,
        )

        if retencao is None:
            raise RetencaoNaoEncontradaError(
                "Reserva ou bloqueio não encontrado."
            )

        # Impede que uma retenção seja liberada duas vezes.
        if retencao.status == "LIBERADA":
            raise RetencaoJaLiberadaError(
                "Esta reserva ou bloqueio já foi liberado."
            )

        # Altera o status sem excluir o histórico.
        retencao.status = "LIBERADA"

        db.commit()
        db.refresh(retencao)

    except Exception:
        db.rollback()
        raise

    return retencao

def consultar_estoque(
    db: Session,
    produto_id: int,
) -> dict:

    produto = buscar_produto_para_consulta(db, produto_id)

    if produto is None:
        raise ProdutoNaoEncontradoError()

    quantidades = obter_quantidades_retidas(db, produto_id)

    quantidade_reservada = quantidades["quantidade_reservada"]
    quantidade_bloqueada = quantidades["quantidade_bloqueada"]

    quantidade_disponivel = (
        produto.quantidade_total
        - quantidade_reservada
        - quantidade_bloqueada
    )

    return {
        "produto_id": produto.id,
        "nome": produto.nome,
        "quantidade_total": produto.quantidade_total,
        "quantidade_reservada": quantidade_reservada,
        "quantidade_bloqueada": quantidade_bloqueada,
        "quantidade_disponivel": quantidade_disponivel,
    }


def consultar_retencao(
    db: Session,
    produto_id: int,
    retencao_id: int,
) -> Retencao:

    produto = buscar_produto_para_consulta(db, produto_id)

    if produto is None:
        raise ProdutoNaoEncontradoError(
            "Produto não encontrado."
        )

    retencao = buscar_retencao_por_id(
        db,
        produto_id,
        retencao_id,
    )

    if retencao is None:
        raise RetencaoNaoEncontradaError(
            "Reserva ou bloqueio não encontrado."
        )

    return retencao

def listar_retencoes(
    db: Session,
    produto_id: int,
) -> list[Retencao]:
    produto = buscar_produto_para_consulta(db, produto_id)

    if produto is None:
        raise ProdutoNaoEncontradoError(
            "Produto não encontrado."
        )

    return listar_retencoes_por_produto(db, produto_id)

