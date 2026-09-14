from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for models; Alembic compares its metadata with the database."""
