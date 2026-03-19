from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from draws.models import DrawEvent
from ops.models import ScrapeRun
from results.models import DrawResult, RewardType
from sources.models import LotterySource


class ApiReadEndpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.source = LotterySource.objects.create(
            code="huaylao",
            name="Huay Lao",
            category=LotterySource.Category.REGIONAL,
        )
        self.second_source = LotterySource.objects.create(
            code="huaymaley",
            name="Huay Maley",
            category=LotterySource.Category.REGIONAL,
        )
        self.draw_event = DrawEvent.objects.create(
            source=self.source,
            scheduled_date=date(2026, 3, 18),
            resolved_date=date(2026, 3, 18),
            status=DrawEvent.Status.COMPLETED,
            resolution_method=DrawEvent.ResolutionMethod.CALENDAR_SCRAPE,
        )
        self.second_draw_event = DrawEvent.objects.create(
            source=self.second_source,
            scheduled_date=date(2026, 3, 17),
            resolved_date=date(2026, 3, 17),
            status=DrawEvent.Status.COMPLETED,
            resolution_method=DrawEvent.ResolutionMethod.CALENDAR_SCRAPE,
        )
        self.reward_type = RewardType.objects.create(
            source=self.source,
            code="last_2_digits",
            name="Last 2 Digits",
            digit_length=2,
            expected_count=1,
            sort_order=1,
        )
        self.second_reward_type = RewardType.objects.create(
            source=self.second_source,
            code="bottom_2_digits",
            name="Bottom 2 Digits",
            digit_length=2,
            expected_count=1,
            sort_order=1,
        )
        DrawResult.objects.create(
            draw_event=self.draw_event,
            reward_type=self.reward_type,
            value="29",
            sequence=1,
            raw_label="last_2_digits",
        )
        DrawResult.objects.create(
            draw_event=self.second_draw_event,
            reward_type=self.second_reward_type,
            value="89",
            sequence=1,
            raw_label="bottom_2_digits",
        )
        ScrapeRun.objects.create(
            source=self.source,
            draw_event=self.draw_event,
            job_type=ScrapeRun.JobType.SCRAPE_RESULTS,
            status=ScrapeRun.Status.SUCCEEDED,
            message="scrape completed",
        )

    def test_api_root_lists_available_endpoints(self):
        response = self.client.get(reverse("api-root"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("source_latest_results", response.json()["endpoints"])
        self.assertIn("sources_latest_results", response.json()["endpoints"])

    def test_sources_endpoint_returns_paginated_sources(self):
        response = self.client.get(reverse("source-list"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)
        self.assertEqual(payload["results"][0]["code"], "huaylao")

    def test_source_detail_returns_source_by_code(self):
        response = self.client.get(reverse("source-detail", kwargs={"source_code": "huaylao"}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Huay Lao")

    def test_draw_events_endpoint_filters_by_source(self):
        response = self.client.get(reverse("draw-event-list"), {"source": "huaylao"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)
        self.assertEqual(payload["results"][0]["source_code"], "huaylao")
        self.assertEqual(payload["results"][0]["result_count"], 1)

    def test_draw_event_detail_returns_single_event(self):
        response = self.client.get(reverse("draw-event-detail", kwargs={"pk": self.draw_event.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.draw_event.pk)

    def test_draw_event_results_returns_paginated_results_for_event(self):
        response = self.client.get(reverse("draw-event-results", kwargs={"pk": self.draw_event.pk}))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)
        self.assertEqual(payload["results"][0]["value"], "29")
        self.assertEqual(payload["results"][0]["source_code"], "huaylao")

    def test_results_endpoint_filters_by_reward_type(self):
        response = self.client.get(
            reverse("draw-result-list"),
            {"source": "huaylao", "reward_type": "last_2_digits"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)
        self.assertEqual(payload["results"][0]["value"], "29")
        self.assertEqual(payload["results"][0]["reward_type_code"], "last_2_digits")

    def test_source_latest_results_returns_draw_event_and_results(self):
        response = self.client.get(reverse("source-latest-results", kwargs={"source_code": "huaylao"}))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"]["code"], "huaylao")
        self.assertEqual(payload["draw_event"]["id"], self.draw_event.pk)
        self.assertEqual(payload["results"][0]["value"], "29")

    def test_sources_latest_results_returns_paginated_grouped_feed(self):
        response = self.client.get(reverse("sources-latest-results"), {"sources": "huaylao,huaymaley"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["results"][0]["source_code"], "huaylao")
        self.assertEqual(payload["results"][1]["source_code"], "huaymaley")

    def test_scrape_runs_endpoint_filters_by_status(self):
        response = self.client.get(
            reverse("scrape-run-list"),
            {"source": "huaylao", "status": ScrapeRun.Status.SUCCEEDED},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)
        self.assertEqual(payload["results"][0]["status"], ScrapeRun.Status.SUCCEEDED)

    def test_scrape_run_detail_returns_single_run(self):
        run = ScrapeRun.objects.get(source=self.source)
        response = self.client.get(reverse("scrape-run-detail", kwargs={"pk": run.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], run.pk)
