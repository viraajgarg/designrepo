import re
from dataclasses import asdict, dataclass
from io import BytesIO

from pypdf import PdfReader


DESIGN_NUMBER_PATTERN = re.compile(r"Design\s+Number\s*[:#]?\s*(\d{5,8}-\d{3})", re.IGNORECASE)


@dataclass(frozen=True)
class JournalDesign:
    design_num_id: str
    page_number: int
    article_name: str | None
    design_class: str | None
    registration_date: str | None
    applicant_source_text: str | None
    priority_source_text: str | None
    source_text: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class JournalPdfParser:
    def parse(self, pdf_bytes: bytes) -> list[JournalDesign]:
        reader = PdfReader(BytesIO(pdf_bytes))
        records: list[JournalDesign] = []
        seen: set[str] = set()
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            matches = list(DESIGN_NUMBER_PATTERN.finditer(page_text))
            for index, match in enumerate(matches):
                design_num_id = match.group(1)
                if design_num_id in seen:
                    continue
                seen.add(design_num_id)
                end = matches[index + 1].start() if index + 1 < len(matches) else len(page_text)
                source_text = page_text[match.start():end].strip()
                class_match = re.search(r"\bClass\s+([\d]{2}-[\d]{2})\b", source_text, re.IGNORECASE)
                title_match = re.search(r"\bTitle\s*:?\s*(.+)", source_text, re.IGNORECASE)
                registration_match = re.search(
                    r"\bDate\s+of\s+Registration\s*:?\s*(\d{2}/\d{2}/\d{4})",
                    source_text,
                    re.IGNORECASE,
                )
                applicant_text = None
                if class_match and registration_match and class_match.end() <= registration_match.start():
                    applicant_text = source_text[class_match.end():registration_match.start()].strip()
                priority_match = re.search(r"\bPriority\s*:?\s*(.*)", source_text, re.IGNORECASE)
                records.append(JournalDesign(
                    design_num_id=design_num_id,
                    page_number=page_number,
                    article_name=title_match.group(1).strip() if title_match else None,
                    design_class=class_match.group(1) if class_match else None,
                    registration_date=registration_match.group(1) if registration_match else None,
                    applicant_source_text=applicant_text,
                    priority_source_text=priority_match.group(1).strip() if priority_match else None,
                    source_text=source_text,
                ))
        return records