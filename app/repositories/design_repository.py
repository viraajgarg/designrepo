from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.orm import Session, aliased, selectinload

from app.models import ApplicantDetail, DesignDetail, Image, PriorityDetail


class DesignRepository:
    def __init__(self, db: Session):
        self.db = db

    def latest_for_update(self, design_num_id: str) -> DesignDetail | None:
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": design_num_id},
        )
        return self.db.scalar(
            select(DesignDetail)
            .where(DesignDetail.design_num_id == design_num_id)
            .order_by(DesignDetail.version.desc(), DesignDetail.id.desc())
            .limit(1)
            .with_for_update()
        )

    def by_id_with_children(self, design_id: int) -> DesignDetail | None:
        return self.db.scalar(
            select(DesignDetail)
            .options(
                selectinload(DesignDetail.applicants),
                selectinload(DesignDetail.images),
                selectinload(DesignDetail.priorities),
            )
            .where(DesignDetail.id == design_id)
        )

    def latest_id(self, design_num_id: str) -> int | None:
        design, row_num = self._ranked_designs()
        return self.db.scalar(
            select(design.id).where(
                design.design_num_id == design_num_id,
                row_num == 1,
                design.active == "Y",
            )
        )

    def search_latest(self, query: str, page: int, page_size: int) -> tuple[list[int], int]:
        design, row_num = self._ranked_designs()
        pattern = f"%{query.replace('*', '%')}%"
        applicant_match = select(ApplicantDetail.id).where(
            ApplicantDetail.design_id == design.id,
            ApplicantDetail.active == "Y",
            or_(
                ApplicantDetail.applicant_name.ilike(pattern),
                ApplicantDetail.applicant_address.ilike(pattern),
            ),
        ).exists()
        image_match = select(Image.id).where(
            Image.design_id == design.id,
            Image.active == "Y",
            or_(Image.image.ilike(pattern), Image.image_view.ilike(pattern)),
        ).exists()
        priority_match = select(PriorityDetail.id).where(
            PriorityDetail.design_id == design.id,
            PriorityDetail.active == "Y",
            or_(
                PriorityDetail.application_number.ilike(pattern),
                PriorityDetail.country_name.ilike(pattern),
                cast(PriorityDetail.date_of_filing_conversion_country, String).ilike(pattern),
            ),
        ).exists()
        matches = or_(
            design.design_num_id.ilike(pattern),
            design.article_name.ilike(pattern),
            design.design_class.ilike(pattern),
            design.journal_num.ilike(pattern),
            cast(design.filing_date, String).ilike(pattern),
            cast(design.journal_date, String).ilike(pattern),
            design.image.ilike(pattern),
            applicant_match,
            image_match,
            priority_match,
        )
        current = (row_num == 1) & (design.active == "Y") & matches
        total = self.db.scalar(select(func.count()).select_from(design).where(current)) or 0
        ids = self.db.scalars(
            select(design.id)
            .where(current)
            .order_by(design.design_num_id, design.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(ids), total

    @staticmethod
    def _ranked_designs():
        ranked = (
            select(
                DesignDetail,
                func.row_number()
                .over(
                    partition_by=DesignDetail.design_num_id,
                    order_by=(DesignDetail.version.desc(), DesignDetail.id.desc()),
                )
                .label("row_num"),
            )
            .subquery()
        )
        return aliased(DesignDetail, ranked), ranked.c.row_num