from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from django.utils import timezone

from ops.models import ScrapeRun
from scraping.config_loader import load_source_config
from scraping.date_utils import parse_draw_date_value
from scraping.extractors import extract_fields
from scraping.fetchers import fetch_url
from scraping.normalizers import normalize_extracted_fields
from scraping.persistence import persist_scrape_payload
from scraping.types import ScrapePayload
from scraping.validators import validate_extracted_fields
from sources.models import LotterySource


class ScraperServiceError(RuntimeError):
    pass


def _load_html(*, html: str | None = None, html_file: str | None = None, source_url: str | None = None, headers: dict | None = None) -> tuple[str, str]:
    if html is not None:
        return html, source_url or "inline://html"

    if html_file is not None:
        path = Path(html_file)
        return path.read_text(encoding="utf-8"), str(path)

    if not source_url:
        raise ScraperServiceError("A source URL is required when html/html_file are not provided")

    fetch_result = fetch_url(source_url, headers=headers)
    return fetch_result.text, fetch_result.url


def _extract_page_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    lines = [" ".join(line.split()) for line in soup.get_text("\n").splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _build_draw_date_context(draw_date: str) -> dict[str, str]:
    context = {"draw_date": draw_date}
    parsed_date = parse_draw_date_value(draw_date)
    if parsed_date is None:
        return context

    context.update(
        {
            "draw_date_iso": parsed_date.isoformat(),
            "draw_date_compact": parsed_date.strftime("%Y%m%d"),
            "draw_date_dmy": parsed_date.strftime("%d%m%Y"),
            "draw_date_thai_compact": parsed_date.strftime("%d%m") + f"{parsed_date.year + 543:04d}",
        }
    )
    return context


def _resolve_source_url(config: dict, draw_date: str | None, source_url: str | None) -> str | None:
    if source_url:
        return source_url

    source_url_template = config.get("source_url_template")
    if source_url_template and draw_date:
        return source_url_template.format(**_build_draw_date_context(draw_date))

    return config.get("source_url")


def _resolve_draw_date(draw_date: str | None, fetched_url: str, raw_html: str, config: dict) -> str | None:
    if draw_date and not config.get("draw_date", {}).get("override_input", False):
        return draw_date

    resolver = config.get("draw_date", {})
    source = resolver.get("source")

    if source == "url_regex":
        pattern = resolver.get("pattern")
        if not pattern:
            return draw_date
        match = re.search(pattern, fetched_url)
        if match:
            return match.group(resolver.get("group", 1))
        return draw_date

    if source == "page_regex":
        pattern = resolver.get("pattern")
        if not pattern:
            return draw_date

        page_text = _extract_page_text(raw_html)
        match = re.search(pattern, page_text)
        if not match:
            return draw_date

        resolved_value = " ".join(match.group(resolver.get("group", 1)).split())
        if resolver.get("format") == "thai_text":
            return parse_draw_date_value(resolved_value).isoformat()
        return resolved_value

    return draw_date


def _build_run_metadata(
    *,
    config: dict,
    fetched_url: str,
    requested_draw_date: str | None,
    resolved_draw_date: str | None,
    persist: bool,
    raw_html: str,
    extracted_fields=None,
    normalized_fields=None,
    error: Exception | None = None,
) -> dict:
    metadata = {
        "fetched_url": fetched_url,
        "requested_draw_date": requested_draw_date,
        "resolved_draw_date": resolved_draw_date,
        "draw_date_shifted": bool(requested_draw_date and resolved_draw_date and requested_draw_date != resolved_draw_date),
        "persist": persist,
        "extraction_mode": config.get("extraction", {}).get("mode", "label_groups"),
        "reward_definition_count": len(config.get("reward_definitions", [])),
        "html_size": len(raw_html),
    }

    if extracted_fields is not None:
        metadata["extracted_reward_types"] = [field.reward_type for field in extracted_fields]
        metadata["missing_reward_types"] = [field.reward_type for field in extracted_fields if not field.values]

    if normalized_fields is not None:
        metadata["reward_types"] = [field.reward_type for field in normalized_fields]
        metadata["value_count"] = sum(len(field.values) for field in normalized_fields)
        metadata["value_counts"] = {field.reward_type: len(field.values) for field in normalized_fields}

    if error is not None:
        metadata["error_type"] = error.__class__.__name__

    return metadata


def run_configured_scrape(
    source_code: str,
    *,
    html: str | None = None,
    html_file: str | None = None,
    source_url: str | None = None,
    draw_date: str | None = None,
    persist: bool = False,
) -> ScrapePayload:
    source = LotterySource.objects.get(code=source_code)
    config = load_source_config(source_code)
    requested_draw_date = draw_date
    source_url = _resolve_source_url(config, draw_date, source_url)
    raw_html, fetched_url = _load_html(
        html=html,
        html_file=html_file,
        source_url=source_url,
        headers=config.get("headers"),
    )
    draw_date = _resolve_draw_date(draw_date, fetched_url, raw_html, config)

    run = ScrapeRun.objects.create(
        source=source,
        job_type=ScrapeRun.JobType.SCRAPE_RESULTS,
        status=ScrapeRun.Status.STARTED,
        message=f"Scrape started for {source_code}.",
        metadata=_build_run_metadata(
            config=config,
            fetched_url=fetched_url,
            requested_draw_date=requested_draw_date,
            resolved_draw_date=draw_date,
            persist=persist,
            raw_html=raw_html,
        ),
    )

    extracted_fields = None
    normalized_fields = None

    try:
        extracted_fields = extract_fields(
            raw_html,
            config.get("extraction", {}),
            config.get("reward_definitions", []),
        )
        normalized_fields = normalize_extracted_fields(extracted_fields, config.get("reward_definitions", []))
        validate_extracted_fields(normalized_fields, config.get("reward_definitions", []))

        payload = ScrapePayload(
            source_code=source_code,
            source_name=source.name,
            draw_date=draw_date,
            fetched_url=fetched_url,
            extracted_fields=normalized_fields,
            raw_html=raw_html,
        )

        if persist:
            draw_event = persist_scrape_payload(source, payload, config, requested_draw_date=requested_draw_date)
            run.draw_event = draw_event

        run.status = ScrapeRun.Status.SUCCEEDED
        run.finished_at = timezone.now()
        run.message = f"Scrape completed successfully for {source_code}."
        run.metadata = _build_run_metadata(
            config=config,
            fetched_url=fetched_url,
            requested_draw_date=requested_draw_date,
            resolved_draw_date=draw_date,
            persist=persist,
            raw_html=raw_html,
            extracted_fields=extracted_fields,
            normalized_fields=normalized_fields,
        )
        run.save(update_fields=["draw_event", "status", "finished_at", "message", "metadata"])
        return payload
    except Exception as exc:
        run.status = ScrapeRun.Status.FAILED
        run.finished_at = timezone.now()
        run.message = f"Scrape failed for {source_code}."
        run.error_details = str(exc)
        run.metadata = _build_run_metadata(
            config=config,
            fetched_url=fetched_url,
            requested_draw_date=requested_draw_date,
            resolved_draw_date=draw_date,
            persist=persist,
            raw_html=raw_html,
            extracted_fields=extracted_fields,
            normalized_fields=normalized_fields,
            error=exc,
        )
        run.save(update_fields=["status", "finished_at", "message", "error_details", "metadata"])
        raise
