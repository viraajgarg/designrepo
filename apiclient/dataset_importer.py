import json
import logging
import mimetypes
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from app.schemas import DesignCreate


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
DATE_FORMATS = (
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def parse_datetime(value: str, field_name: str) -> datetime:
    normalized = " ".join(value.split())
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(normalized, date_format)
        except ValueError:
            continue
    raise ValueError(f"Unsupported {field_name} value: {value!r}")


def _labeled_value(soup: BeautifulSoup, field_name: str, required: bool = True) -> str | None:
    for label in soup.select("#divApplicationDetail label"):
        label_text = " ".join(label.get_text(" ", strip=True).split()).rstrip(":").casefold()
        if label_text != field_name.casefold():
            continue
        row = label.find_parent("div", class_="row")
        value = row.select_one("div.col-lg-8 label") if row else None
        if value:
            text = " ".join(value.get_text(" ", strip=True).split())
            if text:
                return text
    if required:
        raise ValueError(f"Required field not found in HTML: {field_name}")
    return None


def _applicants(soup: BeautifulSoup) -> list[dict[str, str]]:
    section = soup.select_one("#divApplicantData")
    if section is None:
        return []
    applicants = []
    for row in section.select("table tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 3:
            continue
        name = " ".join(cells[-2].get_text(" ", strip=True).split()).rstrip(",")
        address = " ".join(cells[-1].get_text(" ", strip=True).split())
        if name and address:
            applicants.append({"applicant_name": name, "applicant_address": address})
    return applicants


def _priorities(soup: BeautifulSoup) -> list[dict[str, Any]]:
    section = soup.select_one("#divPCTPriority")
    if section is None:
        return []
    table = section.find("table")
    if table is None or "record not found" in table.get_text(" ", strip=True).casefold():
        return []

    headers = [" ".join(cell.get_text(" ", strip=True).split()).casefold() for cell in table.select("thead th")]
    priorities = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td", recursive=False)
        values = [" ".join(cell.get_text(" ", strip=True).split()) for cell in cells]
        if not values:
            continue
        if headers and len(headers) == len(values):
            row_values = dict(zip(headers, values, strict=False))
            application_number = _header_value(row_values, "application number")
            country_name = _header_value(row_values, "country name")
            filing_date = _header_value(row_values, "date of filing convention country")
        elif len(values) >= 4:
            _, application_number, country_name, filing_date = values[:4]
        else:
            continue
        if not (application_number and country_name and filing_date):
            continue
        priorities.append({
            "application_number": application_number,
            "country_name": country_name,
            "date_of_filing_conversion_country": parse_datetime(
                filing_date, "priority filing date"
            ).isoformat(),
        })
    return priorities


def _header_value(values: dict[str, str], key: str) -> str:
    return next((value for header, value in values.items() if key in header), "")


def parse_design_folder(folder: Path) -> tuple[dict[str, Any], list[Path]]:
    if not folder.is_dir() or not folder.name.startswith("data_"):
        raise ValueError(f"Not a design dataset folder: {folder}")
    design_num_id = folder.name.removeprefix("data_")
    metadata_path = folder / f"details_{design_num_id}.html"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Metadata HTML is missing: {metadata_path}")

    soup = BeautifulSoup(metadata_path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    html_design_num_id = _labeled_value(soup, "Design Number")
    if html_design_num_id != design_num_id:
        raise ValueError(
            f"Folder design number {design_num_id} does not match HTML value {html_design_num_id}"
        )

    filing_date = parse_datetime(_labeled_value(soup, "Filing Date"), "filing date")
    journal_date_value = _labeled_value(soup, "Journal Date", required=False)
    journal_num = _labeled_value(soup, "Journal Number", required=False)
    image_paths = sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: path.name.casefold(),
    )
    if not 1 <= len(image_paths) <= 7:
        raise ValueError(f"Expected 1 to 7 images; found {len(image_paths)} in {folder}")

    payload = {
        "design_num_id": design_num_id,
        "filing_date": filing_date.isoformat(),
        "article_name": _labeled_value(soup, "Article Name"),
        "class": _labeled_value(soup, "Class"),
        "journal_num": journal_num,
        "journal_date": parse_datetime(journal_date_value, "journal date").isoformat()
        if journal_date_value
        else None,
        "applicants": _applicants(soup),
        "priorities": _priorities(soup),
    }
    try:
        validated_payload = DesignCreate.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid metadata in {metadata_path}: {exc}") from exc
    return validated_payload.model_dump(mode="json", by_alias=True), image_paths


class DesignApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 60):
        self.endpoint = f"{base_url.rstrip('/')}/designs"
        self.timeout = timeout
        self.session = requests.Session()

    def submit(self, payload: dict[str, Any], image_paths: list[Path]) -> dict[str, Any]:
        with ExitStack() as stack:
            files = []
            for image_path in image_paths:
                media_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
                files.append((
                    "images",
                    (image_path.name, stack.enter_context(image_path.open("rb")), media_type),
                ))
            response = self.session.post(
                self.endpoint,
                data={"data": json.dumps(payload, ensure_ascii=False)},
                files=files,
                timeout=self.timeout,
            )
        if not response.ok:
            raise requests.HTTPError(
                f"HTTP {response.status_code}: {response.text[:2000]}",
                response=response,
            )
        return response.json()


def import_dataset(
    dataset_dir: Path,
    logger: logging.Logger,
    submit: bool = False,
    limit: int | None = 10,
    base_url: str = "http://127.0.0.1:8000",
) -> tuple[int, int]:
    if not dataset_dir.is_dir():
        raise NotADirectoryError(dataset_dir)
    client = DesignApiClient(base_url)
    folders = sorted(
        (path for path in dataset_dir.iterdir() if path.is_dir() and path.name.startswith("data_")),
        key=lambda path: path.name.casefold(),
    )
    if limit is not None:
        folders = folders[:limit]

    succeeded = 0
    failed = 0
    for folder in folders:
        design_num_id = folder.name.removeprefix("data_")
        try:
            payload, image_paths = parse_design_folder(folder)
            logger.info(
                "POST payload design_num_id=%s: %s",
                design_num_id,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )
            logger.info("Image uploads design_num_id=%s: %s", design_num_id, [p.name for p in image_paths])
            if submit:
                result = client.submit(payload, image_paths)
                logger.info(
                    "POST success design_num_id=%s response_id=%s",
                    design_num_id,
                    result.get("id"),
                )
            succeeded += 1
        except Exception:
            failed += 1
            logger.exception("Import failed for design_num_id=%s", design_num_id)
    return succeeded, failed