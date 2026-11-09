# Sistema de Controle de Estoque

API REST desenvolvida em Python com FastAPI para gerenciamento de estoque, permitindo controlar entradas, saídas, reservas e bloqueios de produtos, mantendo a consistência das quantidades disponíveis.

O projeto foi desenvolvido como parte de um case prático de Engenharia de Software, com foco em organização, regras de negócio, persistência de dados e testes automatizados.

## Funcionalidades

- Cadastro de produtos.
- Registro de entrada de produtos no estoque.
- Registro de saída, limitado à quantidade disponível.
- Reserva de produtos vinculada a um identificador de solicitação.
- Bloqueio de produtos sem necessidade de identificador de solicitação.
- Liberação de reservas e bloqueios.
- Consulta de uma reserva ou bloqueio pelo identificador.
- Listagem das reservas e bloqueios de um produto.
- Consulta das quantidades total, reservada, bloqueada e disponível.

## Tecnologias utilizadas

- **Python 3.12**
- **FastAPI** — desenvolvimento da API REST.
- **SQLAlchemy** — mapeamento objeto-relacional e acesso ao banco de dados.
- **MySQL** — persistência dos dados.
- **Pydantic** — validação dos dados de entrada e saída.
- **Pytest** — testes automatizados.
- **HTTPX** — suporte aos testes dos endpoints.
- **PyMySQL** — conexão com o MySQL.

## Arquitetura do projeto

O projeto utiliza uma organização em camadas para separar as responsabilidades:

| Camada | Responsabilidade |
|---|---|
| `api` | Definição das rotas e tratamento das requisições HTTP. |
| `services` | Implementação das regras de negócio. |
| `repositories` | Consultas e operações de persistência no banco de dados. |
| `models` | Representação das tabelas do banco de dados. |
| `schemas` | Validação e estruturação dos dados com Pydantic. |
| `database` | Configuração da conexão e inicialização das tabelas. |

### Estrutura de diretórios

```text
controle-estoque/
├── app/
│   ├── api/
│   │   └── produtos.py
│   ├── database/
│   │   ├── base.py
│   │   ├── connection.py
│   │   └── create_tables.py
│   ├── models/
│   │   ├── produto.py
│   │   └── retencao.py
│   ├── repositories/
│   │   ├── produtos.py
│   │   └── retencoes.py
│   ├── schemas/
│   │   └── produto.py
│   ├── services/
│   │   └── produtos.py
│   ├── config.py
│   └── main.py
├── tests/
│   └── test_produtos.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Regras de negócio

O sistema considera quatro informações principais:

- **Quantidade total:** quantidade física registrada no estoque.
- **Quantidade reservada:** quantidade vinculada a reservas ativas.
- **Quantidade bloqueada:** quantidade vinculada a bloqueios ativos.
- **Quantidade disponível:** quantidade que pode ser utilizada em novas operações.

O cálculo da quantidade disponível é:

```text
Disponível = Total - Reservado - Bloqueado
```

As operações de saída, reserva e bloqueio não podem ultrapassar a quantidade disponível.

As reservas e os bloqueios são registrados na tabela `retencoes`, diferenciados pelo campo `tipo`. O campo `status` permite identificar se uma retenção está ativa ou liberada.

Ao liberar uma retenção, seu registro é preservado no banco de dados para manter o histórico da operação.

## Decisões técnicas

- Separação entre API, serviços, repositórios, modelos e schemas para facilitar manutenção e evolução.
- Utilização de transações com `commit` e `rollback` para evitar persistência de operações inválidas.
- Bloqueio da linha do produto durante operações de alteração de estoque, utilizando `SELECT FOR UPDATE`, para serializar operações concorrentes sobre o mesmo produto e reduzir o risco de inconsistências.
- Cálculo da quantidade disponível a partir das retenções ativas, evitando armazenar um saldo disponível independente que poderia ficar desatualizado.
- Utilização de uma única estrutura de retenções para representar reservas e bloqueios.

## Como executar localmente

### 1. Pré-requisitos

- Python 3.12 ou superior.
- MySQL instalado e em execução.
- Git.

### 2. Clonar o repositório

```bash
git clone https://github.com/Giiuliana/controle-estoque
cd controle-estoque
```

### 3. Criar e ativar o ambiente virtual

No Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 4. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 5. Configurar o banco de dados

Crie o banco de dados no MySQL:

```sql
CREATE DATABASE controle_estoque;
```

Copie o arquivo `.env.example` para `.env` e configure as credenciais do seu ambiente:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_NAME=controle_estoque
```

O arquivo `.env` contém informações locais e não deve ser enviado ao GitHub.

### 6. Criar as tabelas

Execute:

```bash
python -m app.database.create_tables
```

### 7. Iniciar a API

```bash
uvicorn app.main:app --reload
```

A API estará disponível em:

```text
http://127.0.0.1:8000
```

A documentação interativa pode ser acessada em:

```text
http://127.0.0.1:8000/docs
```

## Testes automatizados

Para executar os testes:

```bash
pytest
```

O projeto possui testes automatizados para verificar as regras de negócio e o comportamento dos endpoints.

**Resultado atual:** 47 testes aprovados.

## Limitações e possíveis evoluções

- O projeto utiliza MySQL local para execução e persistência dos dados.
- A criação das tabelas é realizada com `SQLAlchemy create_all`; não há gerenciamento de migrações com Alembic.
- Os testes atuais priorizam a validação das regras de negócio e dos endpoints. Testes de integração com uma instância real do MySQL podem ser adicionados futuramente.
- Para um ambiente de produção, podem ser avaliados recursos como autenticação, autorização, migrações de banco de dados, observabilidade e configuração de implantação.

## Uso de Inteligência Artificial

A Inteligência Artificial foi utilizada como ferramenta de apoio durante o desenvolvimento, principalmente para:

- Esclarecimento de conceitos de Python, FastAPI e SQLAlchemy.
- Discussão sobre arquitetura e organização das camadas.
- Apoio na identificação de cenários de teste e regras de negócio.
- Análise de possíveis problemas de consistência nas operações de estoque.
- Revisão da implementação e da aderência aos requisitos do case.

As sugestões foram analisadas e testadas antes de serem incorporadas. O código foi revisado e ajustado durante o desenvolvimento para que as decisões técnicas e as regras de negócio fossem compreendidas.

## Cinco aspectos de qualidade de engenharia

## Cinco aspectos de qualidade de engenharia

1. **Consistência:** validação da quantidade disponível antes de operações que consomem estoque.
2. **Confiabilidade:** utilização de transações e rollback em caso de falha.
3. **Concorrência:** utilização de `SELECT FOR UPDATE` para reduzir o risco de inconsistências em operações simultâneas sobre o mesmo produto.
4. **Testabilidade:** implementação de testes automatizados com Pytest.
5. **Manutenibilidade:** código organizado em módulos, com responsabilidades bem definidas e possibilidade de evolução.
---

Desenvolvido como projeto prático de Engenharia de Software.