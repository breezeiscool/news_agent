import json
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from trendradar.ai.curation import _canonical_url, curate_events
from trendradar.report.html import _render_curated_events, render_html_content


ROOT = Path(__file__).resolve().parents[1]


def _stat(word, category, items):
    return {"word": word, "category": category, "titles": items}


def _item(title, url, source, source_id, summary=""):
    return {"title": title, "url": url, "source_name": source,
            "source_id": source_id, "summary": summary}


class FakeClient:
    calls = 0

    def __init__(self, _config):
        self.api_key = "fake"

    def chat(self, messages, **_kwargs):
        FakeClient.calls += 1
        items = json.loads(messages[-1]["content"])
        if FakeClient.calls <= 2:
            score = 78 if FakeClient.calls == 1 else 82
            return json.dumps({"scores": [{"id": i["id"], "score": score} for i in items]})
        if FakeClient.calls == 3:
            return json.dumps({"clusters": [[1, 2], [3]]})
        return json.dumps({"approved": [[1, 2]]})


class CurationTests(unittest.TestCase):
    def setUp(self):
        FakeClient.calls = 0
        self.stats = [
            _stat("腾讯", "公司监控", [
                _item("腾讯发布新的企业级人工智能平台", "https://a.example/story", "A", "a", "平台正式上线")]),
            _stat("大模型厂商", "行业动态", [
                _item("Tencent launches new enterprise AI platform", "https://b.example/story", "B", "b", "Platform launched"),
                _item("OpenAI announces new model evaluation benchmark", "https://c.example/story", "C", "c", "New benchmark")]),
        ]

    def test_independent_scores_and_same_event_multiple_sources(self):
        with patch("trendradar.ai.curation.AIClient", FakeClient):
            result = curate_events(self.stats, [], {"API_KEY": "fake"},
                                   {"MAX_ITEMS": 60, "MAX_EVENTS": 20, "THRESHOLDS": {"T1": 60, "T2": 76}},
                                   [{"id": "a", "tier": "T2"}, {"id": "b", "tier": "T2"}])
        self.assertTrue(result["scored"])
        self.assertEqual(FakeClient.calls, 4)
        self.assertEqual(len(result["events"]), 2)
        merged = next(e for e in result["events"] if e["company_watch"])
        self.assertEqual(len(merged["sources"]), 2)
        self.assertEqual(merged["scores"], [78, 82])
        page = _render_curated_events(result)
        self.assertIn("https://a.example/story", page)
        self.assertIn("https://b.example/story", page)
        full_page = render_html_content(
            {"stats": [], "new_titles": [], "failed_ids": [], "total_new_count": 0,
             "curated_events": result}, 0, region_order=["hotlist"],
        )
        self.assertIn("今日精选事件", full_page)
        self.assertIn("https://b.example/story", full_page)

    def test_failed_second_score_keeps_company_and_industry_visible(self):
        def respond(messages, **_kwargs):
            items = json.loads(messages[-1]["content"])
            respond.calls += 1
            if respond.calls == 2:
                return "not JSON"
            return json.dumps({"scores": [{"id": i["id"], "score": 90} for i in items]})
        respond.calls = 0
        with patch("trendradar.ai.curation.AIClient") as factory:
            factory.return_value.api_key = "fake"
            factory.return_value.chat.side_effect = respond
            result = curate_events(self.stats, [], {}, {"MAX_ITEMS": 60, "MAX_EVENTS": 20}, [])
        self.assertFalse(result["scored"])
        self.assertEqual(result["candidate_count"], 3)
        self.assertEqual(len(result["events"]), 3)

    def test_aihot_sources_and_22_company_groups_still_configured(self):
        config = yaml.safe_load((ROOT / "config/config.yaml").read_text(encoding="utf-8"))
        feeds = config["rss"]["feeds"]
        supplemental = {"anthropic-news", "nvidia-developer"}
        ai_hot_feeds = [f for f in feeds if f.get("tier") in {"T1", "T2"} and f["id"] not in supplemental]
        self.assertEqual(len(ai_hot_feeds), 18)
        self.assertEqual(len({f["id"] for f in feeds}), len(feeds))
        words = (ROOT / "config/frequency_words.txt").read_text(encoding="utf-8")
        company_section = words.split("[分类:公司监控]", 1)[1].split("[分类:行业动态]", 1)[0]
        self.assertEqual(sum(1 for line in company_section.splitlines() if line.startswith("[") and line.endswith("]")), 22)

    def test_article_id_query_is_not_dropped_as_tracking(self):
        self.assertNotEqual(_canonical_url("https://news.example/article?id=1"),
                            _canonical_url("https://news.example/article?id=2"))
        self.assertEqual(_canonical_url("https://news.example/article?id=1&utm_source=x"),
                         _canonical_url("https://news.example/article?id=1"))


if __name__ == "__main__":
    unittest.main()
