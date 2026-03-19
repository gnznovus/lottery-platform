import json
from calendar import monthrange
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from requests import HTTPError

from scraping.config_loader import ScraperConfigError, load_source_config
from scraping.services import run_configured_scrape
from scraping.validators import ValidationError


class Command(BaseCommand):
    help = "Run a source scraper with source-aware defaults and soft statuses."

    def add_arguments(self, parser):
        parser.add_argument("source_code")
        parser.add_argument("--date", dest="draw_date")
        parser.add_argument("--persist", action="store_true", dest="persist")

    def _previous_month(self, value: date) -> date:
        first_of_month = value.replace(day=1)
        return first_of_month - timedelta(days=1)

    def _resolve_default_draw_date(self, config: dict) -> str | None:
        strategy = config.get("default_date") or {}
        strategy_name = strategy.get("strategy")
        today = timezone.localdate()

        if strategy_name == "monthly_fixed_dates":
            days = sorted({int(day) for day in strategy.get("days", [])})
            if not days:
                raise CommandError("default_date monthly_fixed_dates requires a non-empty days list")

            for probe in [today, self._previous_month(today)]:
                valid_days = [day for day in days if day <= monthrange(probe.year, probe.month)[1]]
                candidates = [date(probe.year, probe.month, day) for day in valid_days if date(probe.year, probe.month, day) <= today]
                if candidates:
                    return max(candidates).isoformat()
            return None

        if strategy_name == "weekly_days":
            days = {str(day).strip().lower() for day in strategy.get("days", [])}
            weekday_map = {
                "mon": 0,
                "monday": 0,
                "tue": 1,
                "tues": 1,
                "tuesday": 1,
                "wed": 2,
                "wednesday": 2,
                "thu": 3,
                "thursday": 3,
                "fri": 4,
                "friday": 4,
                "sat": 5,
                "saturday": 5,
                "sun": 6,
                "sunday": 6,
            }
            weekdays = {weekday_map[day] for day in days if day in weekday_map}
            if not weekdays:
                raise CommandError("default_date weekly_days requires a non-empty days list")

            for offset in range(0, 14):
                candidate = today - timedelta(days=offset)
                if candidate.weekday() in weekdays:
                    return candidate.isoformat()
            return None

        return None

    def _emit(self, payload: dict):
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))

    def handle(self, *args, **options):
        source_code = options["source_code"]
        requested_draw_date = options.get("draw_date")
        persist = options.get("persist", False)

        try:
            config = load_source_config(source_code)
        except ScraperConfigError as exc:
            raise CommandError(str(exc)) from exc

        draw_date = requested_draw_date or self._resolve_default_draw_date(config)
        has_source = bool(config.get("source_url") or config.get("source_url_template"))
        if not has_source:
            raise CommandError("This source has no source_url or source_url_template configured")
        if config.get("source_url_template") and not draw_date and not config.get("source_url"):
            raise CommandError("This source requires --date or a default_date strategy because it uses source_url_template")

        try:
            payload = run_configured_scrape(
                source_code,
                draw_date=draw_date,
                persist=persist,
            )
        except HTTPError as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            if status_code == 404:
                self._emit(
                    {
                        "status": "not_found",
                        "source_code": source_code,
                        "requested_draw_date": draw_date,
                        "fetched_url": getattr(response, "url", None),
                        "message": f"No published result page found for {source_code} on {draw_date}.",
                    }
                )
                return
            raise
        except ValidationError as exc:
            self._emit(
                {
                    "status": "no_result",
                    "source_code": source_code,
                    "requested_draw_date": draw_date,
                    "message": str(exc),
                }
            )
            return

        status = "success"
        report_shifted_status = bool(config.get("report_resolved_other_date", False))
        if report_shifted_status and requested_draw_date and payload.draw_date and requested_draw_date != payload.draw_date:
            status = "resolved_other_date"

        self._emit(
            {
                "status": status,
                "source_code": payload.source_code,
                "requested_draw_date": requested_draw_date,
                "draw_date": payload.draw_date,
                "fetched_url": payload.fetched_url,
                "extracted_fields": [
                    {
                        "reward_type": field.reward_type,
                        "raw_label": field.raw_label,
                        "values": field.values,
                    }
                    for field in payload.extracted_fields
                ],
            }
        )
