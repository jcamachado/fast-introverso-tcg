from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_superuser: Mapped[bool] = mapped_column(default=False)

    cards: Mapped[list["Card"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    variant: Mapped[str] = mapped_column(String(255), default="")
    collection_name: Mapped[str] = mapped_column(String(255), default="")
    number: Mapped[str] = mapped_column(String(100), default="")
    collection_number: Mapped[str] = mapped_column(String(100), default="")
    picture_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)

    owner: Mapped[User] = relationship(back_populates="cards")
