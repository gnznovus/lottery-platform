import json

from django.core.management.base import BaseCommand, CommandError

from scraping.config_loader import ScraperConfigError, load_source_config
from scraping.services import run_configured_scrape


class Command(BaseCommand):
    help = "Run a configured scraper and print normalized output."

    def add_arguments(self, parser):
        parser.add_argument("source_code")
        parser.add_argument("--html-file", dest="html_file")
        parser.add_argument("--url", dest="source_url")
        parser.add_argument("--draw-date", dest="draw_date")
        parser.add_argument("--persist", action="store_true", dest="persist")

    def handle(self, *args, **options):
        source_code = options["source_code"]
        html_file = options.get("html_file")
        source_url = options.get("source_url")
        draw_date = options.get("draw_date")

        if not html_file and not source_url:
            try:
                config = load_source_config(source_code)
            except ScraperConfigError as exc:
                raise CommandError(str(exc)) from exc

            has_config_source = bool(config.get("source_url") or config.get("source_url_template"))
            if not has_config_source:
                raise CommandError(
                    "Provide --html-file or --url, or configure source_url/source_url_template for this source"
                )

            if config.get("source_url_template") and not draw_date:
                raise CommandError("This source requires --draw-date because it uses source_url_template")

        payload = run_configured_scrape(
            source_code,
            html_file=html_file,
            source_url=source_url,
            draw_date=draw_date,
            persist=options.get("persist", False),
        )

        result = {
            "source_code": payload.source_code,
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
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
