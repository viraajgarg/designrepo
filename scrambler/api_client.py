import json
import mimetypes
from contextlib import ExitStack
from pathlib import Path

import requests
from pydantic import ValidationError

from app.schemas import DesignCreate


class DesignApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def create_design(self, data: dict, image_paths: list[Path]) -> dict:
        try:
            validated = DesignCreate.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Reviewed design payload is incomplete or invalid: {exc}") from exc
        if not 1 <= len(image_paths) <= 7:
            raise ValueError("One to seven local image paths are required")
        with ExitStack() as stack:
            files = []
            for image_path in image_paths:
                if not image_path.is_file():
                    raise FileNotFoundError(image_path)
                content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
                files.append(("images", (image_path.name, stack.enter_context(image_path.open("rb")), content_type)))
            response = self.session.post(
                f"{self.base_url}/designs",
                data={"data": json.dumps(validated.model_dump(by_alias=True))},
                files=files,
                timeout=self.timeout,
            )
        if not response.ok:
            raise RuntimeError(f"Local API returned HTTP {response.status_code}: {response.text[:1000]}")
        return response.json()