from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.applicant_detail import ApplicantDetail
    from app.models.image import Image
    from app.models.priority_detail import PriorityDetail


class DesignDetail(Base):
    __tablename__ = "DESIGN_DETAIL"
    __table_args__ = {"schema": "designs"}

    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True)
    design_num_id: Mapped[str] = mapped_column("DESIGN_NUM_ID", String, nullable=False, index=True)
    filing_date: Mapped[datetime] = mapped_column("FILING_DATE", DateTime, nullable=False)
    article_name: Mapped[str] = mapped_column("ARTICLE_NAME", String, nullable=False)
    design_class: Mapped[str] = mapped_column("CLASS", String, nullable=False)
    journal_num: Mapped[str | None] = mapped_column("JOURNAL_NUM", String)
    journal_date: Mapped[datetime | None] = mapped_column("JOURNAL_DATE", DateTime)
    created_date: Mapped[datetime] = mapped_column(
        "CREATED_DATE", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_date: Mapped[datetime | None] = mapped_column("UPDATED_DATE", DateTime(timezone=True))
    version: Mapped[int] = mapped_column("VERSION", BigInteger, nullable=False)
    created_by: Mapped[str | None] = mapped_column("CREATED_BY", String)
    updated_by: Mapped[str | None] = mapped_column("UPDATED_BY", String)
    image: Mapped[str | None] = mapped_column("image", String)
    active: Mapped[str] = mapped_column("active", String, nullable=False, server_default="Y")

    applicants: Mapped[list["ApplicantDetail"]] = relationship(back_populates="design")
    images: Mapped[list["Image"]] = relationship(back_populates="design")
    priorities: Mapped[list["PriorityDetail"]] = relationship(back_populates="design")