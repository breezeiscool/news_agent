import json
import unittest

from trendradar.ai.analyzer import AIAnalyzer, AIAnalysisResult
from trendradar.report.email_html import render_email_html
from trendradar.report.html import render_html_content


class NewsFocusTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = AIAnalyzer.__new__(AIAnalyzer)
        self.analyzer.max_news = 8
        self.analyzer.include_rss = True

    def test_company_and_industry_both_survive_news_limit(self):
        stats = [
            {"category": "公司监控", "word": "工商银行", "titles": [
                {"title": f"工行新闻{i}"} for i in range(20)
            ]},
            {"category": "行业动态", "word": "AI 芯片及硬件", "titles": [
                {"title": f"芯片新闻{i}"} for i in range(20)
            ]},
        ]
        rss_stats = [
            {"category": "公司监控", "word": "招商银行", "titles": [
                {"title": f"招行公告{i}", "summary": "真实采购细节"} for i in range(20)
            ]},
            {"category": "行业动态", "word": "大模型厂商", "titles": [
                {"title": f"模型发布{i}", "summary": "模型性能与发布时间"} for i in range(20)
            ]},
        ]
        prepared = self.analyzer._prepare_news_content(stats, rss_stats)
        self.assertEqual(prepared.analyzed_count, 8)
        self.assertEqual(prepared.hotlist_analyzed, 4)
        self.assertEqual(prepared.rss_analyzed, 4)
        self.assertIn("公司监控 / 工商银行", prepared.news_content)
        self.assertIn("行业动态 / AI 芯片及硬件", prepared.news_content)
        self.assertIn("公司监控 / 招商银行", prepared.rss_content)
        self.assertIn("行业动态 / 大模型厂商", prepared.rss_content)
        self.assertIn("模型性能与发布时间", prepared.rss_content)

    def test_evidence_validation_drops_unmatched_company_and_cluster(self):
        response = json.dumps({
            "company_summaries": [
                {"company": "工商银行", "summary": "拟采购算力", "titles": ["工行采购公告", "不存在"]},
                {"company": "不存在公司", "summary": "虚构", "titles": ["工行采购公告"]},
            ],
            "industry_clusters": [
                {"group": "大模型厂商", "section": "cn", "company": "腾讯", "summary": "发布模型", "titles": ["腾讯新模型", "不存在"]},
                {"group": "云基础设施", "section": "cn", "company": "假公司", "summary": "虚构", "titles": ["腾讯新模型"]},
            ],
            "industry_level_summaries": {"大模型厂商": "有发布", "云基础设施": "虚构"},
        }, ensure_ascii=False)
        result = self.analyzer._parse_response(response)
        self.analyzer._validate_evidence(
            result,
            [{"category": "公司监控", "word": "工商银行", "titles": [{"title": "工行采购公告"}]}],
            [{"category": "行业动态", "word": "大模型厂商", "titles": [{"title": "腾讯新模型"}]}],
        )
        self.assertEqual(result.company_summaries[0]["titles"], ["工行采购公告"])
        self.assertEqual(len(result.company_summaries), 1)
        self.assertEqual(result.industry_clusters[0]["titles"], ["腾讯新模型"])
        self.assertEqual(len(result.industry_clusters), 1)
        self.assertEqual(result.industry_level_summaries, {"大模型厂商": "有发布"})

    def test_company_digest_precedes_folded_source_links(self):
        ai_result = AIAnalysisResult(
            success=True,
            company_summaries=[{
                "company": "工商银行",
                "summary": "启动算力采购，值得跟踪招标公告。",
                "titles": ["工商银行采购公告"],
            }],
        )
        report = {
            "stats": [{
                "category": "公司监控",
                "word": "工商银行",
                "count": 1,
                "titles": [{
                    "title": "工商银行采购公告",
                    "source_name": "公司公告",
                    "url": "https://example.com/tender",
                }],
            }],
            "new_titles": [],
            "failed_ids": [],
            "total_new_count": 0,
        }
        html = render_html_content(
            report, 1, region_order=["hotlist", "ai_analysis"],
            ai_analysis=ai_result, show_new_section=False,
        )
        self.assertIn("启动算力采购，值得跟踪招标公告。", html)
        self.assertIn('<details class="company-evidence">', html)
        self.assertIn('href="https://example.com/tender"', html)
        self.assertLess(html.index("启动算力采购"), html.index("查看原始资讯"))

    def test_company_summary_precedes_industry_in_page_and_email(self):
        analysis = AIAnalysisResult(
            success=True,
            sentiment_controversy="腾讯公布新一轮算力采购计划。",
            core_trends="AI 芯片供应链有新增扩产信号。",
        )
        report = {"stats": [], "new_titles": [], "failed_ids": [], "total_new_count": 0}
        page = render_html_content(report, 0, region_order=["ai_analysis"], ai_analysis=analysis)
        email = render_email_html(report, 0, ai_analysis=analysis)
        self.assertLess(page.index("腾讯公布新一轮算力采购计划"), page.index("AI 芯片供应链有新增扩产信号"))
        self.assertLess(email.index("一、重点公司动态"), email.index("二、AI 行业交集"))


if __name__ == "__main__":
    unittest.main()
