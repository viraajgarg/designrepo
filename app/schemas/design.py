from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplicantInput(BaseModel):
    applicant_name: str = Field(min_length=1)
    applicant_address: str = Field(min_length=1)


class PriorityInput(BaseModel):
    application_number: str = Field(min_length=1)
    country_name: str = Field(min_length=1)
    date_of_filing_conversion_country: datetime


class DesignFields(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    design_num_id: str = Field(min_length=1)
    filing_date: datetime
    article_name: str = Field(min_length=1)
    design_class: str = Field(alias="class", min_length=1)
    journal_num: str | None = None
    journal_date: datetime | None = None
    created_by: str | None = None


class DesignCreate(DesignFields):
    applicants: list[ApplicantInput] = Field(default_factory=list)
    priorities: list[PriorityInput] = Field(default_factory=list)


class DesignUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    filing_date: datetime
    article_name: str = Field(min_length=1)
    design_class: str = Field(alias="class", min_length=1)
    journal_num: str | None = None
    journal_date: datetime | None = None
    updated_by: str | None = None


class ApplicantRead(ApplicantInput):
    model_config = ConfigDict(from_attributes=True)


class ImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image: str
    image_view: str


class PriorityRead(PriorityInput):
    model_config = ConfigDict(from_attributes=True)


class DesignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    design_num_id: str
    filing_date: datetime
    article_name: str
    design_class: str = Field(serialization_alias="class")
    journal_num: str | None
    journal_date: datetime | None
    created_date: datetime
    updated_date: datetime | None
    version: int
    created_by: str | None
    updated_by: str | None
    image: str | None
    active: str
    applicants: list[ApplicantRead]
    images: list[ImageRead]
    priorities: list[PriorityRead]


class DesignSearchResult(BaseModel):
    items: list[DesignRead]
    page: int
    page_size: int
    total: int