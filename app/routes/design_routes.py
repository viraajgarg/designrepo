from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError

from app.routes.dependencies import get_design_service
from app.schemas import DesignCreate, DesignRead, DesignSearchResult, DesignUpdate
from app.services import DesignService


router = APIRouter(prefix="/designs", tags=["designs"])


@router.post("", response_model=DesignRead, status_code=status.HTTP_201_CREATED)
def create_design(
    data: str = Form(..., description="JSON-encoded design, applicant, and priority details"),
    images: list[UploadFile] = File(..., description="One to seven design images"),
    service: DesignService = Depends(get_design_service),
):
    try:
        payload = DesignCreate.model_validate_json(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    return service.create(payload, images)


@router.get("/search", response_model=DesignSearchResult)
def search_designs(
    q: str = Query(min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=20),
    service: DesignService = Depends(get_design_service),
):
    return service.search(q, page, page_size)


@router.get("/{design_num_id}", response_model=DesignRead)
def get_design(
    design_num_id: str,
    service: DesignService = Depends(get_design_service),
):
    return service.get(design_num_id)


@router.put("/{design_num_id}", response_model=DesignRead)
def update_design(
    design_num_id: str,
    payload: DesignUpdate,
    service: DesignService = Depends(get_design_service),
):
    return service.update(design_num_id, payload)


@router.delete("/{design_num_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_design(
    design_num_id: str,
    service: DesignService = Depends(get_design_service),
) -> Response:
    service.deactivate(design_num_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)