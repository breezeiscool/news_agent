import json
import unittest
from types import SimpleNamespace

from trendradar.ai.analyzer import AIAnalyzer
from trendradar.report.html import _render_cfo_signal_radar


class CFOAnalysisParsingTests(unittest.TestCase):
    def setUp(self):
        # _parse_response 不依赖初始化后的客户端，避免测试触发模型或网络。
        self.analyzer = AIAnalyzer.__new__(AIAnalyzer)

    def test_cfo_signals_are_validated_sorted_and_limited(self):
        signals = []
        for index, score in enumerate([61, 93, 76, 110, 55, 82], 1):
            signals.append(
                {
                    "subject": f"公司{index}",
                    "event_type": "未知标签" if index == 1 else "招标采购",
                    "direction": "未知方向" if index == 1 else "机会",
                    "score": score,
                    "summary": f"事件{index}",
                    "cfo_relevance": "可能影响收入机会",
                    "titles": [f"标题{index}"],
                }
            )
        response = json.dumps({"core_trends": "研判", "cfo_top_signals": signals}, ensure_ascii=False)

        result = self.analyzer._parse_response(response)

        self.assertTrue(result.success)
        self.assertEqual(len(result.cfo_top_signals), 5)
        self.assertEqual([item["score"] for item in result.cfo_top_signals], [100, 93, 82, 76, 61])
        fallback = next(item for item in result.cfo_top_signals if item["subject"] == "公司1")
        self.assertEqual(fallback["event_type"], "其他")
        self.assertEqual(fallback["direction"], "观察")

    def test_old_ai_response_remains_compatible(self):
        result = self.analyzer._parse_response('{"core_trends":"旧版研判"}')
        self.assertTrue(result.success)
        self.assertEqual(result.cfo_top_signals, [])


class CFORadarRenderingTests(unittest.TestCase):
    def test_radar_links_evidence_and_escapes_model_text(self):
        ai_result = SimpleNamespace(
            success=True,
            cfo_top_signals=[
                {
                    "subject": "示例客户 <A>",
                    "event_type": "招标采购",
                    "direction": "机会",
                    "score": 88,
                    "summary": "启动 AI 基础设施采购",
                    "cfo_relevance": "形成近期收入机会",
                    "titles": ["示例客户启动采购"],
                }
            ],
        )
        stats = [
            {
                "titles": [
                    {
                        "title": "示例客户启动采购",
                        "source_name": "公司公告",
                        "url": "https://example.com/tender",
                    }
                ]
            }
        ]

        rendered = _render_cfo_signal_radar(ai_result, stats)

        self.assertIn("今日商业信号", rendered)
        self.assertIn("示例客户 &lt;A&gt;", rendered)
        self.assertIn('href="https://example.com/tender"', rendered)
        self.assertIn("88", rendered)
        self.assertNotIn("示例客户 <A>", rendered)


if __name__ == "__main__":
    unittest.main()
