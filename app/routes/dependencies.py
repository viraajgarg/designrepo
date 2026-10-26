from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import DesignService


def get_design_service(db: Session = Depends(get_db)) -> DesignService:
    return DesignService(db)