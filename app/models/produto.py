
from sqlalchemy import CheckConstraint, Integer, String, text
from sqlalchemy.dialects.mysql import BIGINT, DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Produto(Base):
    __tablename__ = "produtos"

    __table_args__ = (
        CheckConstraint(
            "quantidade_total >= 0",
            name="ck_produtos_quantidade"
        ),
        CheckConstraint(
            "CHAR_LENGTH(TRIM(nome)) > 0",
            name="ck_produtos_nome"
        ),
        {"mysql_engine": "InnoDB"},
    )

    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    nome: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )

    quantidade_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0")
    )

    criado_em: Mapped[object] = mapped_column(
        DATETIME(fsp=6),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)")
    )

    retencoes: Mapped[list["Retencao"]] = relationship(
        back_populates="produto"
    )
