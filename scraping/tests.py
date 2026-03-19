from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from requests import HTTPError, Response

from draws.models import DrawEvent
from ops.models import ScrapeRun
from results.models import DrawResult, RewardType
from scraping.config_loader import load_source_config
from scraping.services import run_configured_scrape
from scraping.validators import ValidationError
from sources.models import LotterySource


HUAYRAT_SAMPLE_HTML = (
    "<div>"
    "<h1>ผลสลากกินแบ่งรัฐบาล</h1>"
    "<h2>งวดวันที่ 16 มีนาคม 2569</h2>"
    "<div>รางวัลที่ 1 รางวัลละ 6,000,000 บาท</div>"
    "<div>833009</div>"
    "<div>เลขหน้า 3 ตัว 2 รางวัลๆละ 4,000 บาท</div>"
    "<div>510 983</div>"
    "<div>เลขท้าย 3 ตัว 2 รางวัลๆละ 4,000 บาท</div>"
    "<div>439 954</div>"
    "<div>เลขท้าย 2 ตัว 1 รางวัลๆละ 2,000 บาท</div>"
    "<div>64</div>"
    "<div>รางวัลข้างเคียงรางวัลที่ 1 2 รางวัลๆละ 100,000 บาท</div>"
    "<div>833008 833010</div>"
    "<div>รางวัลที่ 2 มี 5 รางวัลๆละ 200,000 บาท</div>"
    "<div>117025 179593 374236 397484 735523</div>"
    "<div>รางวัลที่ 3 มี 10 รางวัลๆละ 80,000 บาท</div>"
    "<div>059493 138565 182277 298749 404097</div>"
    "<div>487540 577743 625073 654498 837597</div>"
    "<div>รางวัลที่ 4 มี 50 รางวัลๆละ 40,000 บาท</div>"
    "<div>007567 078977 180744 249388 321823</div>"
    "<div>446056 555748 675895 797796 954048</div>"
    "<div>029255 089857 201187 272045 324346</div>"
    "<div>459757 565081 735221 812558 960949</div>"
    "<div>059485 092685 212645 280129 324916</div>"
    "<div>469188 579461 736554 820609 966241</div>"
    "<div>070451 107914 236689 311922 395110</div>"
    "<div>503941 603558 745920 850019 978750</div>"
    "<div>077905 139317 246777 311988 434858</div>"
    "<div>506568 669082 746770 869653 997677</div>"
    "<div>รางวัลที่ 5 มี 100 รางวัลๆละ 20,000 บาท</div>"
    "<div>017302 069126 175727 282835 396223</div>"
    "<div>483882 619290 717271 837068 918949</div>"
    "<div>022869 081659 192312 298403 404850</div>"
    "<div>486260 648647 724005 839524 931437</div>"
    "<div>031227 083222 202155 299654 405743</div>"
    "<div>499190 658083 745140 841507 958669</div>"
    "<div>032558 090173 217417 308776 420840</div>"
    "<div>515904 664006 769134 842453 960056</div>"
    "<div>040017 121582 238719 312487 421239</div>"
    "<div>547491 686557 782509 859319 963508</div>"
    "<div>053363 129636 247185 325318 422025</div>"
    "<div>558370 700094 797189 878413 966376</div>"
    "<div>054220 134959 248160 334816 426445</div>"
    "<div>564499 705090 809274 906900 977089</div>"
    "<div>060705 139611 261044 335661 461514</div>"
    "<div>588245 705159 812630 913334 983987</div>"
    "<div>061436 142662 261105 336209 467533</div>"
    "<div>592181 709068 813220 913523 984866</div>"
    "<div>066369 159666 263925 358156 476995</div>"
    "<div>599204 712646 828287 918203 985993</div>"
    "<div>ตรวจหวยย้อนหลัง</div>"
    "</div>"
)


def build_simple_result_html(title, draw_date_text, full_result, top_3_digits, bottom_2_digits):
    return (
        "<div>"
        f"<h1>{title}</h1>"
        f"<h2>{title} วันที่ 18 มีนาคม 2569</h2>"
        f"<div>{title}</div>"
        f"<div>งวดวันที่ {draw_date_text}</div>"
        "<div>ผลรางวัล</div>"
        f"<div>{full_result}</div>"
        "<div>3 ตัวบน</div>"
        "<div>2 ตัวล่าง</div>"
        f"<div>{top_3_digits}</div>"
        f"<div>{bottom_2_digits}</div>"
        "<div>คำนวณ</div>"
        "</div>"
    )


HUAYLAO_SIMPLE_HTML = build_simple_result_html("ผลหวยลาวพัฒนา", "17 มีนาคม 2569", "504329", "329", "43")
HUAYMALEY_SIMPLE_HTML = build_simple_result_html("ผลหวยมาเลย์", "17 มีนาคม 2569", "9991", "991", "89")
HUAYHANOY_SPECIAL_HTML = build_simple_result_html("ผลหวยฮานอยพิเศษ", "17 มีนาคม 2569", "51116", "116", "83")
HUAYHANOY_NORMAL_HTML = build_simple_result_html("ผลหวยฮานอยปกติ", "17 มีนาคม 2569", "25287", "287", "70")
HUAYHANOY_VIP_HTML = build_simple_result_html("ผลหวยฮานอย VIP", "17 มีนาคม 2569", "23466", "466", "26")
HUAYLAO_BROKEN_HTML = build_simple_result_html("ผลหวยลาวพัฒนา", "17 มีนาคม 2569", "504329", "329", "")


class HuayRatScrapingPipelineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        LotterySource.objects.create(code="huayrat", name="Huay Rat")

    def test_load_huayrat_config(self):
        config = load_source_config("huayrat")
        self.assertEqual(config["source_code"], "huayrat")

    def test_run_huayrat_scrape_with_inline_html(self):
        payload = run_configured_scrape("huayrat", html=HUAYRAT_SAMPLE_HTML, source_url="https://news.sanook.com/lotto/check/16032569/")

        self.assertEqual(payload.source_code, "huayrat")
        self.assertEqual(payload.draw_date, "16032569")
        self.assertEqual(len(payload.extracted_fields), 9)
        result_map = {field.reward_type: field.values for field in payload.extracted_fields}
        self.assertEqual(result_map["first_prize"], ["833009"])
        self.assertEqual(result_map["front_3_digits"], ["510", "983"])
        self.assertEqual(result_map["back_3_digits"], ["439", "954"])
        self.assertEqual(result_map["last_2_digits"], ["64"])
        self.assertEqual(result_map["near_first_prize"], ["833008", "833010"])
        self.assertEqual(len(result_map["prize_4"]), 50)
        self.assertEqual(len(result_map["prize_5"]), 100)

    def test_persist_huayrat_scrape_creates_draw_event_and_results(self):
        run_configured_scrape("huayrat", html=HUAYRAT_SAMPLE_HTML, source_url="https://news.sanook.com/lotto/check/16032569/", persist=True)

        draw_event = DrawEvent.objects.get(source__code="huayrat", scheduled_date="2026-03-16")
        self.assertEqual(draw_event.resolved_date.isoformat(), "2026-03-16")
        self.assertEqual(draw_event.status, DrawEvent.Status.COMPLETED)
        self.assertEqual(RewardType.objects.filter(source__code="huayrat").count(), 9)
        self.assertEqual(RewardType.objects.get(source__code="huayrat", code="first_prize").name, "รางวัลที่ 1")
        self.assertEqual(DrawResult.objects.filter(draw_event=draw_event).count(), 173)

    def test_persist_huayrat_rerun_replaces_results_without_duplicates(self):
        run_configured_scrape("huayrat", html=HUAYRAT_SAMPLE_HTML, source_url="https://news.sanook.com/lotto/check/16032569/", persist=True)
        run_configured_scrape("huayrat", html=HUAYRAT_SAMPLE_HTML, source_url="https://news.sanook.com/lotto/check/16032569/", persist=True)

        draw_event = DrawEvent.objects.get(source__code="huayrat", scheduled_date="2026-03-16")
        self.assertEqual(DrawEvent.objects.filter(source__code="huayrat", scheduled_date="2026-03-16").count(), 1)
        self.assertEqual(DrawResult.objects.filter(draw_event=draw_event).count(), 173)


class ExpHuaySimpleSourceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for code, name in [
            ("huaylao", "Huay Lao"),
            ("huaymaley", "Huay Maley"),
            ("huayhanoy_special", "Huay Hanoy Special"),
            ("huayhanoy_normal", "Huay Hanoy Normal"),
            ("huayhanoy_vip", "Huay Hanoy VIP"),
        ]:
            LotterySource.objects.create(code=code, name=name)

    def test_load_simple_source_configs(self):
        for source_code in ["huaylao", "huaymaley", "huayhanoy_special", "huayhanoy_normal", "huayhanoy_vip"]:
            with self.subTest(source_code=source_code):
                config = load_source_config(source_code)
                self.assertEqual(config["source_code"], source_code)

    def test_run_simple_source_scrapes_with_inline_html(self):
        scenarios = [
            ("huaylao", HUAYLAO_SIMPLE_HTML, "https://exphuay.com/result/laosdevelops?date=2026-03-18", "2026-03-17", ["504329", "329", "43"]),
            ("huaymaley", HUAYMALEY_SIMPLE_HTML, "https://exphuay.com/result/magnum4d?date=2026-03-18", "2026-03-17", ["9991", "991", "89"]),
            ("huayhanoy_special", HUAYHANOY_SPECIAL_HTML, "https://exphuay.com/result/xsthm?date=2026-03-18", "2026-03-17", ["51116", "116", "83"]),
            ("huayhanoy_normal", HUAYHANOY_NORMAL_HTML, "https://exphuay.com/result/minhngoc?date=2026-03-18", "2026-03-17", ["25287", "287", "70"]),
            ("huayhanoy_vip", HUAYHANOY_VIP_HTML, "https://exphuay.com/result/mlnhngo?date=2026-03-18", "2026-03-17", ["23466", "466", "26"]),
        ]

        for source_code, html, source_url, expected_date, expected_values in scenarios:
            with self.subTest(source_code=source_code):
                payload = run_configured_scrape(source_code, html=html, source_url=source_url, draw_date="2026-03-18")
                self.assertEqual(payload.draw_date, expected_date)
                result_map = {field.reward_type: field.values for field in payload.extracted_fields}
                self.assertEqual(result_map["full_result"], [expected_values[0]])
                self.assertEqual(result_map["top_3_digits"], [expected_values[1]])
                self.assertEqual(result_map["bottom_2_digits"], [expected_values[2]])

    def test_persist_simple_source_scrapes_keeps_requested_and_resolved_dates(self):
        scenarios = [
            ("huaylao", HUAYLAO_SIMPLE_HTML, "https://exphuay.com/result/laosdevelops?date=2026-03-18"),
            ("huaymaley", HUAYMALEY_SIMPLE_HTML, "https://exphuay.com/result/magnum4d?date=2026-03-18"),
            ("huayhanoy_special", HUAYHANOY_SPECIAL_HTML, "https://exphuay.com/result/xsthm?date=2026-03-18"),
            ("huayhanoy_normal", HUAYHANOY_NORMAL_HTML, "https://exphuay.com/result/minhngoc?date=2026-03-18"),
            ("huayhanoy_vip", HUAYHANOY_VIP_HTML, "https://exphuay.com/result/mlnhngo?date=2026-03-18"),
        ]

        for source_code, html, source_url in scenarios:
            with self.subTest(source_code=source_code):
                run_configured_scrape(source_code, html=html, source_url=source_url, draw_date="2026-03-18", persist=True)
                draw_event = DrawEvent.objects.get(source__code=source_code, scheduled_date="2026-03-18")
                self.assertEqual(draw_event.resolved_date.isoformat(), "2026-03-17")
                self.assertEqual(draw_event.status, DrawEvent.Status.COMPLETED)
                self.assertIn("Requested 2026-03-18, resolved 2026-03-17", draw_event.notes)
                self.assertEqual(RewardType.objects.filter(source__code=source_code).count(), 3)
                self.assertEqual(DrawResult.objects.filter(draw_event=draw_event).count(), 3)

    def test_failed_scrape_records_useful_metadata(self):
        with self.assertRaises(ValidationError):
            run_configured_scrape(
                "huaylao",
                html=HUAYLAO_BROKEN_HTML,
                source_url="https://exphuay.com/result/laosdevelops?date=2026-03-18",
                draw_date="2026-03-18",
            )

        run = ScrapeRun.objects.filter(source__code="huaylao").latest("id")
        self.assertEqual(run.status, ScrapeRun.Status.FAILED)
        self.assertEqual(run.metadata["requested_draw_date"], "2026-03-18")
        self.assertEqual(run.metadata["resolved_draw_date"], "2026-03-17")
        self.assertTrue(run.metadata["draw_date_shifted"])
        self.assertEqual(run.metadata["error_type"], "ValidationError")
        self.assertIn("bottom_2_digits", run.metadata["missing_reward_types"])
        self.assertIn("Missing values", run.error_details)


class ScrapeCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        LotterySource.objects.create(code="huaylao", name="Huay Lao")

    def test_scrape_command_defaults_to_success_for_exp_sources(self):
        stdout = StringIO()
        call_command("scrape", "huaylao", "--date", "2026-03-18", stdout=stdout)
        self.assertIn('"status": "success"', stdout.getvalue())
        self.assertIn('"draw_date": "2026-03-17"', stdout.getvalue())

    def test_scrape_command_reports_not_found_for_missing_page(self):
        response = Response()
        response.status_code = 404
        response.url = "https://exphuay.com/result/laosdevelops?date=2026-03-10"
        error = HTTPError("404 Client Error", response=response)

        with patch("scraping.management.commands.scrape.run_configured_scrape", side_effect=error):
            stdout = StringIO()
            call_command("scrape", "huaylao", "--date", "2026-03-10", stdout=stdout)

        self.assertIn('"status": "not_found"', stdout.getvalue())
        self.assertIn('"requested_draw_date": "2026-03-10"', stdout.getvalue())
