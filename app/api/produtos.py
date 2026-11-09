
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db

from app.services.produtos import (
    cadastrar_produto,
    registrar_entrada,
    registrar_saida,
    registrar_reserva,
    registrar_bloqueio,
    ProdutoNaoEncontradoError,
    EstoqueInsuficienteError,
    liberar_retencao,
    RetencaoNaoEncontradaError,
    RetencaoJaLiberadaError,
    consultar_estoque,
    consultar_retencao,
    listar_retencoes,
)
from app.schemas.produto import (
    ProdutoCreate,
    ProdutoResponse,
    EntradaEstoque,
    SaidaEstoque,
    ReservaEstoque,
    BloqueioEstoque,
    RetencaoResponse,
    EstoqueResponse,
    
)


router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
)


@router.post(
    "",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_produto(
    dados: ProdutoCreate,
    db: Session = Depends(get_db),
):
    return cadastrar_produto(db, dados)


@router.post(
    "/{produto_id}/entradas",
    response_model=ProdutoResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Produto não encontrado."},
    },
)
def registrar_entrada_estoque(
    produto_id: int,
    dados: EntradaEstoque,
    db: Session = Depends(get_db),
):
    try:
        return registrar_entrada(
            db,
            produto_id,
            dados.quantidade,
        )

    except ProdutoNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )


@router.post(
    "/{produto_id}/saidas",
    response_model=ProdutoResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Produto não encontrado."},
        409: {"description": "Estoque disponível insuficiente."},
    },
)
def registrar_saida_estoque(
    produto_id: int,
    dados: SaidaEstoque,
    db: Session = Depends(get_db),
):
    try:
        return registrar_saida(
            db,
            produto_id,
            dados.quantidade,
        )

    except ProdutoNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    except EstoqueInsuficienteError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro),
        )

@router.post(
    "/{produto_id}/reservas",
    response_model=RetencaoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Produto não encontrado."},
        409: {"description": "Estoque disponível insuficiente."},
    },
)
def criar_reserva(
    produto_id: int,
    dados: ReservaEstoque,
    db: Session = Depends(get_db),
):
    try:
        return registrar_reserva(
            db,
            produto_id,
            dados.solicitacao_id,
            dados.quantidade,
        )

    except ProdutoNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    except EstoqueInsuficienteError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro),
        )

@router.post(
    "/{produto_id}/bloqueios",
    response_model=RetencaoResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Produto não encontrado."},
        409: {"description": "Estoque disponível insuficiente."},
    },
)
def criar_bloqueio(
    produto_id: int,
    dados: BloqueioEstoque,
    db: Session = Depends(get_db),
):
    try:
        return registrar_bloqueio(
            db,
            produto_id,
            dados.quantidade,
        )

    except ProdutoNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    except EstoqueInsuficienteError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro),
        )

@router.post(
    "/{produto_id}/retencoes/{retencao_id}/liberar",
    response_model=RetencaoResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Produto ou retenção não encontrado."
        },
        409: {
            "description": "Retenção já liberada."
        },
    },
)
def liberar_reserva_ou_bloqueio(
    produto_id: int,
    retencao_id: int,
    db: Session = Depends(get_db),
):
    try:
        return liberar_retencao(
            db,
            produto_id,
            retencao_id,
        )

    except ProdutoNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    except RetencaoNaoEncontradaError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva ou bloqueio não encontrado.",
        )

    except RetencaoJaLiberadaError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(erro),
        )
    
@router.get(
    "/{produto_id}/estoque",
    response_model=EstoqueResponse,
    status_code=status.HTTP_200_OK,
)
def consultar_estoque_produto(
    produto_id: int,
    db: Session = Depends(get_db),
):
    try:
        return consultar_estoque(db, produto_id)

    except ProdutoNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

@router.get(
    "/{produto_id}/retencoes/{retencao_id}",
    response_model=RetencaoResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Produto ou retenção não encontrado."
        },
    },
)
def consultar_reserva_ou_bloqueio(
    produto_id: int,
    retencao_id: int,
    db: Session = Depends(get_db),
):
    try:
        return consultar_retencao(
            db,
            produto_id,
            retencao_id,
        )

    except ProdutoNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )

    except RetencaoNaoEncontradaError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva ou bloqueio não encontrado.",
        )
    
@router.get(
    "/{produto_id}/retencoes",
    response_model=list[RetencaoResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Produto não encontrado."
        },
    },
)
def listar_reservas_e_bloqueios(
    produto_id: int,
    db: Session = Depends(get_db),
):
    try:
        return listar_retencoes(db, produto_id)

    except ProdutoNaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado.",
        )