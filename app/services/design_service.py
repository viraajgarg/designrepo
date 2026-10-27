import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models import ApplicantDetail, DesignDetail, Image, PriorityDetail
from app.repositories import DesignRepository
from app.schemas import DesignCreate, DesignSearchResult, DesignUpdate


IMAGE_STORAGE_DIR = Path(os.getenv("IMAGE_STORAGE_DIR", r"C:\workarea\images"))
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class DesignService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = DesignRepository(db)

    def create(self, payload: DesignCreate, uploads: list[UploadFile]) -> DesignDetail:
        if not 1 <= len(uploads) <= 7:
            raise HTTPException(status_code=422, detail="A design must have between 1 and 7 images")
        image_paths: list[Path] = []
        created_paths: list[Path] = []
        now = datetime.now(timezone.utc)
        try:
            with self.db.begin():
                if self.repository.latest_for_update(payload.design_num_id) is not None:
                    raise HTTPException(status_code=409, detail="DESIGN_NUM_ID already exists")
                image_paths, created_paths = self._save_uploads(uploads, payload.design_num_id)
                design = DesignDetail(
                    design_num_id=payload.design_num_id,
                    filing_date=payload.filing_date,
                    article_name=payload.article_name,
                    design_class=payload.design_class,
                    journal_num=payload.journal_num,
                    journal_date=payload.journal_date,
                    created_date=now,
                    version=1,
                    created_by=payload.created_by,
                    image=str(image_paths[0]),
                    active="Y",
                )
                self.db.add(design)
                self.db.flush()
                self._add_children(design.id, payload, image_paths, now, version=1)
                design_id = design.id
        except Exception:
            self._remove_files(created_paths)
            raise
        return self._get_design(design_id)

    def update(self, design_num_id: str, payload: DesignUpdate) -> DesignDetail:
        now = datetime.now(timezone.utc)
        with self.db.begin():
            current = self.repository.latest_for_update(design_num_id)
            if current is None or current.active != "Y":
                raise HTTPException(status_code=404, detail="Design not found")

            new_version = DesignDetail(
                design_num_id=current.design_num_id,
                filing_date=payload.filing_date,
                article_name=payload.article_name,
                design_class=payload.design_class,
                journal_num=payload.journal_num,
                journal_date=payload.journal_date,
                created_date=now,
                updated_date=now,
                version=current.version + 1,
                created_by=current.created_by,
                updated_by=payload.updated_by,
                image=current.image,
                active="Y",
            )
            self.db.add(new_version)
            self.db.flush()
            for applicant in current.applicants:
                if applicant.active == "Y":
                    self.db.add(ApplicantDetail(
                        design_id=new_version.id,
                        applicant_name=applicant.applicant_name,
                        applicant_address=applicant.applicant_address,
                        created_date=now,
                        version=new_version.version,
                        created_by=applicant.created_by,
                        active="Y",
                    ))
            for image in current.images:
                if image.active == "Y":
                    self.db.add(Image(
                        design_id=new_version.id,
                        image=image.image,
                        image_view=image.image_view,
                        created_date=now,
                        version=new_version.version,
                        created_by=image.created_by,
                        active="Y",
                    ))
            for priority in current.priorities:
                if priority.active == "Y":
                    self.db.add(PriorityDetail(
                        design_id=new_version.id,
                        application_number=priority.application_number,
                        country_name=priority.country_name,
                        date_of_filing_conversion_country=priority.date_of_filing_conversion_country,
                        created_date=now,
                        version=new_version.version,
                        created_by=priority.created_by,
                        active="Y",
                    ))
            design_id = new_version.id
        return self._get_design(design_id)

    def get(self, design_num_id: str) -> DesignDetail:
        design_id = self.repository.latest_id(design_num_id)
        if design_id is None:
            raise HTTPException(status_code=404, detail="Design not found")
        return self._get_design(design_id)

    def search(self, query: str, page: int, page_size: int) -> DesignSearchResult:
        ids, total = self.repository.search_latest(query, page, page_size)
        items = [self._get_design(design_id) for design_id in ids]
        return DesignSearchResult(items=items, page=page, page_size=page_size, total=total)

    def deactivate(self, design_num_id: str) -> None:
        with self.db.begin():
            current = self.repository.latest_for_update(design_num_id)
            if current is None or current.active != "Y":
                raise HTTPException(status_code=404, detail="Design not found")
            current.active = "NO"
            current.updated_date = datetime.now(timezone.utc)

    def _get_design(self, design_id: int) -> DesignDetail:
        design = self.repository.by_id_with_children(design_id)
        if design is None:
            raise HTTPException(status_code=404, detail="Design not found")
        return design

    def _add_children(
        self,
        design_id: int,
        payload: DesignCreate,
        image_paths: list[Path],
        now: datetime,
        version: int,
    ) -> None:
        self.db.add_all([
            ApplicantDetail(
                design_id=design_id,
                applicant_name=applicant.applicant_name,
                applicant_address=applicant.applicant_address,
                created_date=now,
                version=version,
                created_by=payload.created_by,
                active="Y",
            )
            for applicant in payload.applicants
        ])
        self.db.add_all([
            Image(
                design_id=design_id,
                image=str(image_path),
                image_view=str(image_path),
                created_date=now,
                version=version,
                created_by=payload.created_by,
                active="Y",
            )
            for image_path in image_paths[1:]
        ])
        self.db.add_all([
            PriorityDetail(
                design_id=design_id,
                application_number=priority.application_number,
                country_name=priority.country_name,
                date_of_filing_conversion_country=priority.date_of_filing_conversion_country,
                created_date=now,
                version=version,
                created_by=payload.created_by,
                active="Y",
            )
            for priority in payload.priorities
        ])

    @staticmethod
    def _save_uploads(
        uploads: list[UploadFile], design_num_id: str
    ) -> tuple[list[Path], list[Path]]:
        IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        image_paths: list[Path] = []
        created_paths: list[Path] = []
        safe_design_num_id = re.sub(r"[^A-Za-z0-9_. -]", "_", design_num_id).strip(" .")
        if not safe_design_num_id:
            raise HTTPException(status_code=422, detail="DESIGN_NUM_ID cannot be used as a filename")
        try:
            for index, upload in enumerate(uploads):
                suffix = Path(upload.filename or "image").suffix.lower()
                if upload.content_type not in ALLOWED_IMAGE_TYPES or suffix not in ALLOWED_EXTENSIONS:
                    raise HTTPException(status_code=415, detail="Unsupported image type")
                filename = f"{safe_design_num_id}{suffix}" if index == 0 else f"{uuid.uuid4().hex}{suffix}"
                path = IMAGE_STORAGE_DIR / filename
                if path.exists():
                    upload_bytes = upload.file.read()
                    upload.file.seek(0)
                    if path.read_bytes() != upload_bytes:
                        raise HTTPException(status_code=409, detail=f"Image already exists: {filename}")
                else:
                    with path.open("xb") as destination:
                        created_paths.append(path)
                        shutil.copyfileobj(upload.file, destination)
                image_paths.append(path)
        except Exception:
            DesignService._remove_files(created_paths)
            raise
        return image_paths, created_paths

    @staticmethod
    def _remove_files(paths: list[Path]) -> None:
        for path in paths:
            path.unlink(missing_ok=True)