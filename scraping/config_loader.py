import json
from pathlib import Path

from django.conf import settings


class ScraperConfigError(ValueError):
    pass


def config_directory() -> Path:
    return settings.BASE_DIR / "scraping" / "configs"


def load_source_config(source_code: str) -> dict:
    path = config_directory() / f"{source_code}.json"
    if not path.exists():
        raise ScraperConfigError(f"Missing scraper config for source: {source_code}")

    with path.open("r", encoding="utf-8-sig") as config_file:
        data = json.load(config_file)

    if data.get("source_code") != source_code:
        raise ScraperConfigError(
            f"Config mismatch: expected source_code '{source_code}', got '{data.get('source_code')}'"
        )
    return data
