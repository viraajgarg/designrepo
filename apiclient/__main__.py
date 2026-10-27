import argparse
import logging
import sys
from pathlib import Path

from apiclient.dataset_importer import import_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Import local design folders into the Design Registry API.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(r"C:\workarea\patent\legtech\dataset"),
        help="Root directory containing data_<design-number> folders",
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--log-file", type=Path, default=Path("apiclient/logs/import.log"))
    parser.add_argument("--limit", type=int, default=10, help="Preview/import only the first N folders")
    parser.add_argument("--all", action="store_true", help="Process every design folder")
    parser.add_argument("--submit", action="store_true", help="POST records; otherwise only log payloads")
    args = parser.parse_args()

    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(args.log_file, encoding="utf-8"),
        ],
        force=True,
    )
    logger = logging.getLogger("apiclient")
    try:
        limit = None if args.all else max(args.limit, 0)
        if args.submit and not args.all and args.limit <= 0:
            parser.error("Use --all to submit the full dataset")
        processed, failed = import_dataset(
            args.dataset,
            logger,
            submit=args.submit,
            limit=limit,
            base_url=args.api_url,
        )
        mode = "submitted" if args.submit else "previewed"
        logger.info("Finished: %d %s, %d failed", processed, mode, failed)
        return 1 if failed else 0
    except Exception:
        logger.exception("Dataset import could not start")
        return 1


if __name__ == "__main__":
    sys.exit(main())