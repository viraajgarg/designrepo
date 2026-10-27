import os
import re
import time
from io import BytesIO
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image


DESIGN_IMAGE_URL = "https://search.ipindia.gov.in/DesignSearch/DesignSearch/GetCaptchaImage"
DESIGN_NUMBER_PATTERN = re.compile(r"\d{5,8}-\d{3}\Z")


class DesignImageClient:
    def __init__(self, image_dir: Path | None = None, timeout: int = 30, request_delay: float = 0.5):
        load_dotenv()
        self.image_dir = image_dir or Path(os.getenv("IMAGE_STORAGE_DIR", r"C:\workarea\images"))
        self.timeout = timeout
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "DesignRegistryJournalImporter/1.0"})

    def download(self, design_num_id: str) -> Path:
        if not DESIGN_NUMBER_PATTERN.fullmatch(design_num_id):
            raise ValueError(f"Unexpected design number format: {design_num_id}")
        self.image_dir.mkdir(parents=True, exist_ok=True)
        image_path = self.image_dir / f"{design_num_id}.png"
        if image_path.is_file():
            return image_path

        response = self.session.get(
            DESIGN_IMAGE_URL,
            params={"application_number": design_num_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        if not response.headers.get("Content-Type", "").casefold().startswith("image/"):
            raise ValueError(f"Image endpoint returned {response.headers.get('Content-Type', 'no content type')}")

        temporary_path = image_path.with_suffix(".png.tmp")
        try:
            with Image.open(BytesIO(response.content)) as downloaded:
                downloaded.load()
                downloaded.convert("RGBA" if "A" in downloaded.getbands() else "RGB").save(
                    temporary_path,
                    format="PNG",
                )
            temporary_path.replace(image_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        return image_path

    def wait_between_requests(self) -> None:
        time.sleep(self.request_delay)