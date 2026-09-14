from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base_class import Base


class PrefixMap(Base):
    """Flat registry: a cadastral prefix with every territory level in one row.

    The key is a unit ('022301_2' -> gmina) or a unit with obreb ('026401_1.0032' -> district).
    """

    __tablename__ = "prefix_map"

    prefix_code: Mapped[str] = mapped_column(String(32), primary_key=True)

    voivodeship_teryt: Mapped[str] = mapped_column(String(2), nullable=False)
    voivodeship_name: Mapped[str] = mapped_column(Text, nullable=False)
    powiat_teryt: Mapped[str | None] = mapped_column(String(4), nullable=True)
    powiat_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmina_teryt: Mapped[str | None] = mapped_column(String(7), nullable=True)
    gmina_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    district_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_prefix_map_gmina", "gmina_teryt"),
        Index("ix_prefix_map_powiat", "powiat_teryt"),
    )
