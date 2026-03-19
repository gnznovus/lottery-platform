import requests

from scraping.types import FetchResult


class FetchError(RuntimeError):
    pass


DEFAULT_TIMEOUT = 30


def fetch_url(url: str, *, headers: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> FetchResult:
    response = requests.get(url, headers=headers or {}, timeout=timeout)
    response.raise_for_status()

    apparent_encoding = getattr(response, "apparent_encoding", None)
    if apparent_encoding and response.encoding != apparent_encoding:
        response.encoding = apparent_encoding

    return FetchResult(
        url=response.url,
        status_code=response.status_code,
        text=response.text,
        content_type=response.headers.get("Content-Type", ""),
    )
