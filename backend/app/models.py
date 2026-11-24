from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Model(Base):
    __tablename__ = "models"
    id: Mapped[int] = mapped_column(primary_key=True)
    part_number: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(250), index=True)
    design_project: Mapped[str] = mapped_column(String(250), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(160), index=True)
    tags: Mapped[str] = mapped_column(Text, default="")
    compatible_robots: Mapped[str] = mapped_column(Text, default="")
    dimension_length: Mapped[str] = mapped_column(String(60), default="")
    dimension_width: Mapped[str] = mapped_column(String(60), default="")
    dimension_height: Mapped[str] = mapped_column(String(60), default="")
    dimension_unit: Mapped[str] = mapped_column(String(10), default="in")
    rom_price: Mapped[str] = mapped_column(String(100), default="")
    last_quoted_on: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    # Which page a model belongs to: "vault" (Model Vault) or "table_config" (Table
    # Configurations, created by the Table Configurator's export).
    collection: Mapped[str] = mapped_column(String(30), default="vault", index=True)
    # Table Configurations only: the Configurator inputs used, as JSON.
    table_config: Mapped[str] = mapped_column(Text, default="")
    files: Mapped[list["File"]] = relationship(cascade="all, delete-orphan")
    prices: Mapped[list["Price"]] = relationship(cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    role: Mapped[str] = mapped_column(String(30))
    original_name: Mapped[str] = mapped_column(String(300))
    relative_path: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(150))
    size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Price(Base):
    __tablename__ = "pricing_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    rom_price: Mapped[str] = mapped_column(String(100))
    quoted_on: Mapped[str] = mapped_column(String(20))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
