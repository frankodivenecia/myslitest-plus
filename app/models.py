"""Datový model. Katalog (subjects/cards/questions) je sdílený a jen ke čtení,
user_questions drží per-user soukromý stav (odpověď + značka „těžká")."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker,
)

from .config import settings

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def to_roman(weight: int) -> str:
    return ROMAN[weight] if 0 < weight < len(ROMAN) else str(weight)


class Base(DeclarativeBase):
    pass


# SQLite potřebuje check_same_thread=False při použití ve web serveru
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    weight: Mapped[int] = mapped_column(Integer)          # 1..7 → římská číslice
    part_kind: Mapped[str] = mapped_column(String(10))    # "karta" | "okruh"

    cards: Mapped[list["Card"]] = relationship(
        back_populates="subject", order_by="Card.number", cascade="all, delete-orphan"
    )

    @property
    def roman(self) -> str:
        return to_roman(self.weight)


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    number: Mapped[int] = mapped_column(Integer)
    slug: Mapped[str] = mapped_column(String(60))         # "karta-1" | "okruh-3"

    subject: Mapped["Subject"] = relationship(back_populates="cards")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="card", order_by="Question.ordinal", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("subject_id", "number", name="uq_card_subject_number"),)


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"))
    block: Mapped[str | None] = mapped_column(String(1), nullable=True)   # 'A'.. | None u okruhu
    number: Mapped[int] = mapped_column(Integer)          # pořadí v bloku (nebo v okruhu)
    ordinal: Mapped[int] = mapped_column(Integer)         # pořadí v kartě celkově
    qid: Mapped[str] = mapped_column(String(8))           # "A1" | "12"
    code: Mapped[str] = mapped_column(String(24))         # "VII/A/1"
    text: Mapped[str] = mapped_column(Text)
    elsewhere_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    card: Mapped["Card"] = relationship(back_populates="questions")

    __table_args__ = (UniqueConstraint("card_id", "block", "number", name="uq_question_card_block_number"),)


class UserQuestion(Base):
    """Per-user soukromý stav k jedné otázce. Chybějící řádek = neoznačeno
    a nezodpovězeno."""
    __tablename__ = "user_questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    hard: Mapped[bool] = mapped_column(Boolean, default=False)
    answer_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )

    __table_args__ = (UniqueConstraint("user_id", "question_id", name="uq_userquestion_user_question"),)
