from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


JOURNAL_LIST_URL = "https://search.ipindia.gov.in/IPOJournal/Journal/Patent"
JOURNAL_PDF_URL = "https://search.ipindia.gov.in/IPOJournal/Journal/ViewJournal"


@dataclass(frozen=True)
class JournalIssue:
    number: str
    publication_date: str
    availability_date: str
    file_name: str


class JournalClient:
    def __init__(self, timeout: int = 45):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "DesignRegistryJournalImporter/1.0"})

    def latest_design_issue(self) -> JournalIssue:
        response = self.session.get(JOURNAL_LIST_URL, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for row in soup.select("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td", recursive=False)]
            if len(cells) < 4:
                continue
            for form in row.find_all("form"):
                button = form.find("button")
                file_field = form.find("input", {"name": "FileName"})
                if (
                    button
                    and "part iv - designs" in button.get_text(" ", strip=True).casefold()
                    and file_field
                    and file_field.get("value")
                ):
                    return JournalIssue(
                        number=cells[1],
                        publication_date=cells[2],
                        availability_date=cells[3],
                        file_name=file_field["value"],
                    )
        raise ValueError("No Part IV - Designs journal PDF was found on the listing page")

    def download_pdf(self, issue: JournalIssue) -> bytes:
        response = self.session.post(
            JOURNAL_PDF_URL,
            data={"FileName": issue.file_name},
            timeout=self.timeout,
        )
        response.raise_for_status()
        if "application/pdf" not in response.headers.get("Content-Type", "").casefold():
            raise ValueError(
                "Journal endpoint did not return a PDF "
                f"(Content-Type: {response.headers.get('Content-Type', 'missing')})"
            )
        if not response.content.startswith(b"%PDF-"):
            raise ValueError("Journal response does not contain a valid PDF signature")
        return response.content