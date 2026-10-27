import argparse
import json
import logging
import re
import sys
from pathlib import Path

from scrambler.api_client import DesignApiClient
from scrambler.image_client import DesignImageClient
from scrambler.journal_client import JournalClient
from scrambler.pdf_parser import JournalPdfParser


def _configure_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_path, encoding="utf-8")],
        force=True,
    )
    return logging.getLogger("scrambler")


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value.replace("/", "_"))


def _scrape(output_dir: Path, logger: logging.Logger) -> Path:
    client = JournalClient()
    issue = client.latest_design_issue()
    logger.info(
        "Found journal %s, publication=%s availability=%s",
        issue.number,
        issue.publication_date,
        issue.availability_date,
    )
    pdf_bytes = client.download_pdf(issue)
    pdf_dir = output_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / f"journal_{_safe_filename(issue.number)}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    records = JournalPdfParser().parse(pdf_bytes)
    image_client = DesignImageClient()
    image_paths: dict[str, str] = {}
    for index, record in enumerate(records):
        if index:
            image_client.wait_between_requests()
        try:
            image_path = image_client.download(record.design_num_id)
            logger.info("Downloaded design image %s to %s", record.design_num_id, image_path)
            image_paths[record.design_num_id] = str(image_path)
        except Exception:
            logger.exception("Failed to download image for design %s", record.design_num_id)
    manifest = {
        "journal_number": issue.number,
        "publication_date": issue.publication_date,
        "availability_date": issue.availability_date,
        "source_file": issue.file_name,
        "pdf_path": str(pdf_path),
        "design_count": len(records),
        "designs": [
            {
                **record.as_dict(),
                "journal_number": issue.number,
                "journal_date": issue.publication_date,
                "image_path": image_paths.get(record.design_num_id),
            }
            for record in records
        ],
    }
    manifest_path = output_dir / f"journal_{_safe_filename(issue.number)}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Parsed %d unique design numbers into %s", len(records), manifest_path)
    for record in records:
        if not record.article_name or not record.design_class:
            logger.warning("Design %s has incomplete structured PDF fields", record.design_num_id)
    return manifest_path


def _submit_reviewed(reviewed_path: Path, base_url: str, logger: logging.Logger) -> int:
    reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
    designs = reviewed.get("designs")
    if not isinstance(designs, list):
        raise ValueError("Reviewed JSON must contain a 'designs' array")
    client = DesignApiClient(base_url)
    failures = 0
    for item in designs:
        design_num_id = str(item.get("data", {}).get("design_num_id", "unknown"))
        try:
            images = [Path(path) for path in item["images"]]
            result = client.create_design(item["data"], images)
            logger.info("Created design %s as record ID %s", design_num_id, result.get("id"))
        except Exception:
            failures += 1
            logger.exception("Failed to submit design %s", design_num_id)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public design journal issues and prepare reviewed API submissions.")
    parser.add_argument("--output-dir", type=Path, default=Path("scrambler/output"))
    parser.add_argument("--log-file", type=Path, default=Path("scrambler/logs/scrambler.log"))
    parser.add_argument("--submit-reviewed", type=Path, help="Submit a human-reviewed JSON packet to the local Design API")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    logger = _configure_logging(args.log_file)
    try:
        if args.submit_reviewed:
            failures = _submit_reviewed(args.submit_reviewed, args.api_url, logger)
            return 1 if failures else 0
        manifest_path = _scrape(args.output_dir, logger)
        logger.info("Review extracted details and supply images before API ingestion: %s", manifest_path)
        return 0
    except Exception:
        logger.exception("Journal processing failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())