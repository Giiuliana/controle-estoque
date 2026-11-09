
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.mysql import BIGINT, DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Retencao(Base):
    __tablename__ = "retencoes"

    __table_args__ = (
        CheckConstraint(
            "quantidade > 0",
            name="ck_retencoes_quantidade"
        ),
        CheckConstraint(
            "tipo IN ('RESERVA', 'BLOQUEIO')",
            name="ck_retencoes_tipo"
        ),
        CheckConstraint(
            "status IN ('ATIVA', 'LIBERADA')",
            name="ck_retencoes_status"
        ),
        CheckConstraint(
            "tipo <> 'RESERVA' OR "
            "(solicitacao_id IS NOT NULL AND "
            "CHAR_LENGTH(TRIM(solicitacao_id)) > 0)",
            name="ck_retencoes_solicitacao"
        ),
        Index(
            "ix_retencoes_produto_status_tipo",
            "produto_id",
            "status",
            "tipo"
        ),
        {"mysql_engine": "InnoDB"},
    )

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    produto_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("produtos.id", ondelete="RESTRICT"),
        nullable=False
    )

    solicitacao_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    tipo: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    quantidade: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default=text("'ATIVA'")
    )

    criado_em: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)")
    )

    produto: Mapped["Produto"] = relationship(
        back_populates="retencoes"
    )
