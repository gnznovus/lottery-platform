from dataclasses import dataclass, field


@dataclass
class FetchResult:
    url: str
    status_code: int
    text: str
    content_type: str = ""


@dataclass
class ExtractedField:
    reward_type: str
    raw_label: str
    values: list[str]
    metadata: dict = field(default_factory=dict)


@dataclass
class ScrapePayload:
    source_code: str
    source_name: str
    draw_date: str | None
    fetched_url: str
    extracted_fields: list[ExtractedField]
    raw_html: str
