from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import produtos as produtos_api
from app.database.connection import get_db
from app.main import app
from app.schemas.produto import ProdutoCreate
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
    listar_retencoes,
)

@pytest.fixture
def cliente():
    app.dependency_overrides[get_db] = lambda: object()

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_cadastrar_produto(cliente, monkeypatch):
    def simular_cadastro(db, dados):
        return SimpleNamespace(
            id=1,
            nome=dados.nome,
            quantidade_total=0,
            criado_em=datetime(2026, 11, 7, 12, 0),
        )

    monkeypatch.setattr(
        produtos_api,
        "cadastrar_produto",
        simular_cadastro,
    )

    resposta = cliente.post(
        "/produtos",
        json={"nome": "Teclado Mecânico"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Teclado Mecânico"
    assert resposta.json()["quantidade_total"] == 0


def test_rejeitar_nome_vazio(cliente):
    resposta = cliente.post(
        "/produtos",
        json={"nome": "   "},
    )

    assert resposta.status_code == 422


def test_service_confirma_cadastro():
    db = Mock()
    dados = ProdutoCreate(nome="Mouse")

    with patch(
        "app.services.produtos.adicionar_produto"
    ) as adicionar:
        produto = cadastrar_produto(db, dados)

    adicionar.assert_called_once_with(db, produto)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(produto)


def test_service_desfaz_em_caso_de_erro():
    db = Mock()
    dados = ProdutoCreate(nome="Monitor")

    with patch(
        "app.services.produtos.adicionar_produto",
        side_effect=RuntimeError("Falha simulada"),
    ):
        with pytest.raises(RuntimeError):
            cadastrar_produto(db, dados)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()

def test_registrar_entrada_estoque(cliente, monkeypatch):
    def simular_entrada(db, produto_id, quantidade):
        return SimpleNamespace(
            id=produto_id,
            nome="Teclado Mecânico",
            quantidade_total=quantidade,
            criado_em=datetime(2026, 11, 7, 12, 0),
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_entrada",
        simular_entrada,
    )

    resposta = cliente.post(
        "/produtos/1/entradas",
        json={"quantidade": 15},
    )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == 1
    assert resposta.json()["quantidade_total"] == 15

def test_entrada_produto_inexistente(cliente, monkeypatch):
    def simular_entrada(db, produto_id, quantidade):
        raise ProdutoNaoEncontradoError(
            "Produto não encontrado."
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_entrada",
        simular_entrada,
    )

    resposta = cliente.post(
        "/produtos/999/entradas",
        json={"quantidade": 10},
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Produto não encontrado."

@pytest.mark.parametrize("quantidade", [0, -5])
def test_rejeitar_quantidade_invalida(cliente, quantidade):
    resposta = cliente.post(
        "/produtos/1/entradas",
        json={"quantidade": quantidade},
    )

    assert resposta.status_code == 422

def test_service_confirma_entrada():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Teclado",
        quantidade_total=10,
    )

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=produto,
    ) as buscar:
        resultado = registrar_entrada(db, 1, 5)

    buscar.assert_called_once_with(db, 1)

    assert resultado.quantidade_total == 15

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(produto)
    db.rollback.assert_not_called()

def test_service_entrada_produto_inexistente():
    db = Mock()

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=None,
    ):
        with pytest.raises(ProdutoNaoEncontradoError):
            registrar_entrada(db, 999, 5)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()

def test_service_desfaz_entrada_em_caso_de_erro():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Teclado",
        quantidade_total=10,
    )

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=produto,
    ):
        db.commit.side_effect = RuntimeError("Falha simulada")

        with pytest.raises(RuntimeError):
            registrar_entrada(db, 1, 5)

    assert produto.quantidade_total == 15
    db.commit.assert_called_once()
    db.rollback.assert_called_once()

def test_registrar_saida_estoque(cliente, monkeypatch):
    def simular_saida(db, produto_id, quantidade):
        return SimpleNamespace(
            id=produto_id,
            nome="Teclado Mecânico",
            quantidade_total=50,
            criado_em=datetime(2026, 11, 7, 12, 0),
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_saida",
        simular_saida,
    )

    resposta = cliente.post(
        "/produtos/1/saidas",
        json={"quantidade": 10},
    )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == 1
    assert resposta.json()["quantidade_total"] == 50

def test_saida_produto_inexistente(cliente, monkeypatch):
    def simular_saida(db, produto_id, quantidade):
        raise ProdutoNaoEncontradoError(
            "Produto não encontrado."
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_saida",
        simular_saida,
    )

    resposta = cliente.post(
        "/produtos/999/saidas",
        json={"quantidade": 10},
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Produto não encontrado."

def test_saida_estoque_insuficiente(cliente, monkeypatch):
    def simular_saida(db, produto_id, quantidade):
        raise EstoqueInsuficienteError(
            "Quantidade solicitada maior que o estoque disponível."
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_saida",
        simular_saida,
    )

    resposta = cliente.post(
        "/produtos/1/saidas",
        json={"quantidade": 100},
    )

    assert resposta.status_code == 409
    assert "estoque disponível" in resposta.json()["detail"]

@pytest.mark.parametrize("quantidade", [0, -5])
def test_rejeitar_quantidade_saida_invalida(cliente, quantidade):
    resposta = cliente.post(
        "/produtos/1/saidas",
        json={"quantidade": quantidade},
    )

    assert resposta.status_code == 422

@pytest.mark.parametrize(
    ("quantidade_saida", "estoque_final"),
    [
        (50, 50),
        (70, 30),
    ],
)
def test_service_confirma_saida(
    quantidade_saida,
    estoque_final,
):
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Teclado",
        quantidade_total=100,
    )

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=produto,
    ) as buscar:

        with patch(
            "app.services.produtos.obter_quantidade_retida",
            return_value=30,
        ) as obter_retida:

            resultado = registrar_saida(
                db,
                1,
                quantidade_saida,
            )

    buscar.assert_called_once_with(db, 1)
    obter_retida.assert_called_once_with(db, 1)

    assert resultado.quantidade_total == estoque_final

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(produto)
    db.rollback.assert_not_called()

def test_service_saida_estoque_insuficiente():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Teclado",
        quantidade_total=100,
    )

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=produto,
    ):

        with patch(
            "app.services.produtos.obter_quantidade_retida",
            return_value=30,
        ):

            with pytest.raises(EstoqueInsuficienteError):
                registrar_saida(db, 1, 71)

    assert produto.quantidade_total == 100

    db.rollback.assert_called_once()
    db.commit.assert_not_called()

def test_service_saida_produto_inexistente():
    db = Mock()

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=None,
    ):
        with pytest.raises(ProdutoNaoEncontradoError):
            registrar_saida(db, 999, 5)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()

def test_service_desfaz_saida_em_caso_de_erro():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Teclado",
        quantidade_total=100,
    )

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=produto,
    ):
        with patch(
            "app.services.produtos.obter_quantidade_retida",
            return_value=20,
        ):
            db.commit.side_effect = RuntimeError("Falha simulada")

            with pytest.raises(RuntimeError):
                registrar_saida(db, 1, 10)

    assert produto.quantidade_total == 90

    db.commit.assert_called_once()
    db.rollback.assert_called_once()

def test_registrar_reserva(cliente, monkeypatch):
    def simular_reserva(db, produto_id, solicitacao_id, quantidade):
        return SimpleNamespace(
            id=1,
            produto_id=produto_id,
            solicitacao_id=solicitacao_id,
            tipo="RESERVA",
            quantidade=quantidade,
            status="ATIVA",
            criado_em=datetime(2026, 11, 9, 12, 0),
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_reserva",
        simular_reserva,
    )

    resposta = cliente.post(
        "/produtos/2/reservas",
        json={
            "solicitacao_id": "PED-2026-001",
            "quantidade": 10,
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["produto_id"] == 2
    assert resposta.json()["solicitacao_id"] == "PED-2026-001"
    assert resposta.json()["tipo"] == "RESERVA"
    assert resposta.json()["quantidade"] == 10
    assert resposta.json()["status"] == "ATIVA"

def test_reserva_produto_inexistente(cliente, monkeypatch):
    def simular_reserva(db, produto_id, solicitacao_id, quantidade):
        raise ProdutoNaoEncontradoError(
            "Produto não encontrado."
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_reserva",
        simular_reserva,
    )

    resposta = cliente.post(
        "/produtos/999/reservas",
        json={
            "solicitacao_id": "PED-2026-002",
            "quantidade": 5,
        },
    )

    assert resposta.status_code == 404

def test_reserva_estoque_insuficiente(cliente, monkeypatch):
    def simular_reserva(db, produto_id, solicitacao_id, quantidade):
        raise EstoqueInsuficienteError(
            "Quantidade solicitada maior que o estoque disponível."
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_reserva",
        simular_reserva,
    )

    resposta = cliente.post(
        "/produtos/2/reservas",
        json={
            "solicitacao_id": "PED-2026-003",
            "quantidade": 100,
        },
    )

    assert resposta.status_code == 409

@pytest.mark.parametrize("quantidade", [0, -5])
def test_rejeitar_quantidade_reserva_invalida(cliente, quantidade):
    resposta = cliente.post(
        "/produtos/2/reservas",
        json={
            "solicitacao_id": "PED-2026-004",
            "quantidade": quantidade,
        },
    )

    assert resposta.status_code == 422


@pytest.mark.parametrize("solicitacao_id", ["", "   "])
def test_rejeitar_solicitacao_id_vazio(cliente, solicitacao_id):
    resposta = cliente.post(
        "/produtos/2/reservas",
        json={
            "solicitacao_id": solicitacao_id,
            "quantidade": 5,
        },
    )

    assert resposta.status_code == 422

def test_service_confirma_reserva():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Teclado",
        quantidade_total=100,
    )

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=produto,
    ) as buscar:

        with patch(
            "app.services.produtos.obter_quantidade_retida",
            return_value=30,
        ) as obter_retida:

            with patch(
                "app.services.produtos.adicionar_retencao"
            ) as adicionar:

                resultado = registrar_reserva(
                    db,
                    1,
                    "PED-2026-005",
                    40,
                )

    buscar.assert_called_once_with(db, 1)
    obter_retida.assert_called_once_with(db, 1)
    adicionar.assert_called_once_with(db, resultado)

    assert resultado.produto_id == 1
    assert resultado.solicitacao_id == "PED-2026-005"
    assert resultado.tipo == "RESERVA"
    assert resultado.quantidade == 40
    assert resultado.status == "ATIVA"

    # Reservar não diminui o estoque total.
    assert produto.quantidade_total == 100

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(resultado)
    db.rollback.assert_not_called()

def test_service_reserva_estoque_insuficiente():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Teclado",
        quantidade_total=100,
    )

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=produto,
    ):
        with patch(
            "app.services.produtos.obter_quantidade_retida",
            return_value=30,
        ):
            with patch(
                "app.services.produtos.adicionar_retencao"
            ) as adicionar:

                with pytest.raises(EstoqueInsuficienteError):
                    registrar_reserva(
                        db,
                        1,
                        "PED-2026-006",
                        71,
                    )

    adicionar.assert_not_called()
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
    assert produto.quantidade_total == 100

def test_service_reserva_produto_inexistente():
    db = Mock()

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=None,
    ):
        with pytest.raises(ProdutoNaoEncontradoError):
            registrar_reserva(
                db,
                999,
                "PED-2026-007",
                5,
            )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()

def test_service_desfaz_reserva_em_caso_de_erro():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Teclado",
        quantidade_total=100,
    )

    with patch(
        "app.services.produtos.buscar_produto_por_id",
        return_value=produto,
    ):
        with patch(
            "app.services.produtos.obter_quantidade_retida",
            return_value=20,
        ):
            with patch(
                "app.services.produtos.adicionar_retencao"
            ):
                db.commit.side_effect = RuntimeError("Falha simulada")

                with pytest.raises(RuntimeError):
                    registrar_reserva(
                        db,
                        1,
                        "PED-2026-008",
                        10,
                    )

    db.commit.assert_called_once()
    db.rollback.assert_called_once()

def test_registrar_bloqueio(cliente, monkeypatch):
    def simular_bloqueio(db, produto_id, quantidade):
        return SimpleNamespace(
            id=1,
            produto_id=produto_id,
            solicitacao_id=None,
            tipo="BLOQUEIO",
            quantidade=quantidade,
            status="ATIVA",
            criado_em=datetime(2026, 11, 9, 12, 0),
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_bloqueio",
        simular_bloqueio,
    )

    resposta = cliente.post(
        "/produtos/1/bloqueios",
        json={"quantidade": 10},
    )

    assert resposta.status_code == 201
    assert resposta.json()["produto_id"] == 1
    assert resposta.json()["solicitacao_id"] is None
    assert resposta.json()["tipo"] == "BLOQUEIO"
    assert resposta.json()["quantidade"] == 10
    assert resposta.json()["status"] == "ATIVA"

def test_bloqueio_produto_inexistente(cliente, monkeypatch):
    def simular_bloqueio(db, produto_id, quantidade):
        raise ProdutoNaoEncontradoError("Produto não encontrado.")

    monkeypatch.setattr(
        produtos_api,
        "registrar_bloqueio",
        simular_bloqueio,
    )

    resposta = cliente.post(
        "/produtos/999/bloqueios",
        json={"quantidade": 10},
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Produto não encontrado."

def test_bloqueio_estoque_insuficiente(cliente, monkeypatch):
    def simular_bloqueio(db, produto_id, quantidade):
        raise EstoqueInsuficienteError(
            "Quantidade solicitada maior que o estoque disponível."
        )

    monkeypatch.setattr(
        produtos_api,
        "registrar_bloqueio",
        simular_bloqueio,
    )

    resposta = cliente.post(
        "/produtos/1/bloqueios",
        json={"quantidade": 100},
    )

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == (
        "Quantidade solicitada maior que o estoque disponível."
    )

@pytest.mark.parametrize("quantidade", [0, -5])
def test_rejeitar_quantidade_bloqueio_invalida(cliente, quantidade):
    resposta = cliente.post(
        "/produtos/1/bloqueios",
        json={"quantidade": quantidade},
    )

    assert resposta.status_code == 422

def test_service_confirma_bloqueio():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        quantidade_total=100,
    )

    retencao = SimpleNamespace(
        id=1,
        produto_id=1,
        solicitacao_id=None,
        tipo="BLOQUEIO",
        quantidade=20,
        status="ATIVA",
    )

    with (
        patch("app.services.produtos.buscar_produto_por_id", return_value=produto),
        patch("app.services.produtos.obter_quantidade_retida", return_value=0),
        patch("app.services.produtos.adicionar_retencao") as adicionar,
    ):
        resultado = registrar_bloqueio(db, 1, 20)

    assert resultado.tipo == "BLOQUEIO"
    assert resultado.solicitacao_id is None
    assert resultado.quantidade == 20
    assert resultado.status == "ATIVA"

    adicionar.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(resultado)

    assert produto.quantidade_total == 100

def test_service_desfaz_bloqueio_em_caso_de_erro():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        quantidade_total=100,
    )

    with (
        patch(
            "app.services.produtos.buscar_produto_por_id",
            return_value=produto,
        ),
        patch(
            "app.services.produtos.obter_quantidade_retida",
            return_value=0,
        ),
        patch(
            "app.services.produtos.adicionar_retencao",
            side_effect=Exception("Erro ao adicionar bloqueio."),
        ),
    ):
        with pytest.raises(Exception, match="Erro ao adicionar bloqueio."):
            registrar_bloqueio(db, 1, 20)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()

def test_liberar_retencao(cliente, monkeypatch):
    def simular_liberacao(db, produto_id, retencao_id):
        return SimpleNamespace(
            id=retencao_id,
            produto_id=produto_id,
            solicitacao_id=None,
            tipo="BLOQUEIO",
            quantidade=20,
            status="LIBERADA",
            criado_em=datetime(2026, 11, 9, 12, 0),
        )

    monkeypatch.setattr(
        produtos_api,
        "liberar_retencao",
        simular_liberacao,
    )

    resposta = cliente.post(
        "/produtos/1/retencoes/5/liberar",
    )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == 5
    assert resposta.json()["produto_id"] == 1
    assert resposta.json()["tipo"] == "BLOQUEIO"
    assert resposta.json()["quantidade"] == 20
    assert resposta.json()["status"] == "LIBERADA"

def test_liberar_retencao_inexistente(cliente, monkeypatch):
    def simular_liberacao(db, produto_id, retencao_id):
        raise RetencaoNaoEncontradaError(
            "Reserva ou bloqueio não encontrado."
        )

    monkeypatch.setattr(
        produtos_api,
        "liberar_retencao",
        simular_liberacao,
    )

    resposta = cliente.post(
        "/produtos/1/retencoes/999/liberar",
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == (
        "Reserva ou bloqueio não encontrado."
    )

def test_consultar_estoque(cliente, monkeypatch):

    def simular_consulta(db, produto_id):
        return {
            "produto_id": produto_id,
            "nome": "Mouse",
            "quantidade_total": 9,
            "quantidade_reservada": 1,
            "quantidade_bloqueada": 1,
            "quantidade_disponivel": 7,
        }

    monkeypatch.setattr(
        produtos_api,
        "consultar_estoque",
        simular_consulta,
    )

    resposta = cliente.get("/produtos/2/estoque")

    assert resposta.status_code == 200
    assert resposta.json()["produto_id"] == 2
    assert resposta.json()["nome"] == "Mouse"
    assert resposta.json()["quantidade_total"] == 9
    assert resposta.json()["quantidade_reservada"] == 1
    assert resposta.json()["quantidade_bloqueada"] == 1
    assert resposta.json()["quantidade_disponivel"] == 7

def test_consultar_estoque_produto_inexistente(
    cliente,
    monkeypatch,
):

    def simular_consulta(db, produto_id):
        raise ProdutoNaoEncontradoError(
            "Produto não encontrado."
        )

    monkeypatch.setattr(
        produtos_api,
        "consultar_estoque",
        simular_consulta,
    )

    resposta = cliente.get("/produtos/999/estoque")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Produto não encontrado."

def test_service_consultar_estoque():

    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Mouse",
        quantidade_total=100,
    )

    with (
        patch(
            "app.services.produtos.buscar_produto_para_consulta",
            return_value=produto,
        ) as buscar,

        patch(
            "app.services.produtos.obter_quantidades_retidas",
            return_value={
                "quantidade_reservada": 20,
                "quantidade_bloqueada": 10,
            },
        ) as obter_retidas,
    ):

        resultado = consultar_estoque(db, 1)

    buscar.assert_called_once_with(db, 1)
    obter_retidas.assert_called_once_with(db, 1)

    assert resultado["quantidade_total"] == 100
    assert resultado["quantidade_reservada"] == 20
    assert resultado["quantidade_bloqueada"] == 10
    assert resultado["quantidade_disponivel"] == 70
def test_listar_retencoes(cliente, monkeypatch):
    def simular_listagem(db, produto_id):
        return [
            SimpleNamespace(
                id=1,
                produto_id=produto_id,
                solicitacao_id="PED-2026-001",
                tipo="RESERVA",
                quantidade=1,
                status="ATIVA",
                criado_em=datetime(2026, 11, 9, 12, 0),
            ),
            SimpleNamespace(
                id=2,
                produto_id=produto_id,
                solicitacao_id=None,
                tipo="BLOQUEIO",
                quantidade=1,
                status="LIBERADA",
                criado_em=datetime(2026, 11, 9, 13, 0),
            ),
        ]

    monkeypatch.setattr(
        produtos_api,
        "listar_retencoes",
        simular_listagem,
    )

    resposta = cliente.get("/produtos/2/retencoes")

    assert resposta.status_code == 200
    assert len(resposta.json()) == 2
    assert resposta.json()[0]["id"] == 1
    assert resposta.json()[0]["tipo"] == "RESERVA"
    assert resposta.json()[1]["id"] == 2
    assert resposta.json()[1]["status"] == "LIBERADA"

def test_service_listar_retencoes_vazias():
    db = Mock()

    produto = SimpleNamespace(
        id=1,
        nome="Mouse",
    )

    with (
        patch(
            "app.services.produtos.buscar_produto_para_consulta",
            return_value=produto,
        ),
        patch(
            "app.services.produtos.listar_retencoes_por_produto",
            return_value=[],
        ) as listar,
    ):
        resultado = listar_retencoes(db, 1)

    listar.assert_called_once_with(db, 1)
    assert resultado == []

def test_listar_retencoes_produto_inexistente(
    cliente,
    monkeypatch,
):
    def simular_listagem(db, produto_id):
        raise ProdutoNaoEncontradoError(
            "Produto não encontrado."
        )

    monkeypatch.setattr(
        produtos_api,
        "listar_retencoes",
        simular_listagem,
    )

    resposta = cliente.get("/produtos/999/retencoes")

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Produto não encontrado."