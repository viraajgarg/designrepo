from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.design_detail import DesignDetail


class PriorityDetail(Base):
    __tablename__ = "PRIORITY_DETAIL"
    __table_args__ = {"schema": "designs"}

    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True)
    design_id: Mapped[int] = mapped_column(
        "DESIGN_ID", ForeignKey("designs.DESIGN_DETAIL.ID"), nullable=False
    )
    application_number: Mapped[str] = mapped_column("APPLICATION_NUMBER", String, nullable=False)
    country_name: Mapped[str] = mapped_column("COUNTRY_NAME", String, nullable=False)
    date_of_filing_conversion_country: Mapped[datetime] = mapped_column(
        "DATE_OF_FILING_CONVERSION_COUNTRY", DateTime, nullable=False
    )
    created_date: Mapped[datetime] = mapped_column(
        "CREATED_DATE", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_date: Mapped[datetime | None] = mapped_column("UPDATED_DATE", DateTime(timezone=True))
    version: Mapped[int] = mapped_column("VERSION", BigInteger, nullable=False)
    created_by: Mapped[str | None] = mapped_column("CREATED_BY", String)
    updated_by: Mapped[str | None] = mapped_column("UPDATED_BY", String)
    active: Mapped[str] = mapped_column("active", String, nullable=False, server_default="Y")

    design: Mapped["DesignDetail"] = relationship(back_populates="priorities")