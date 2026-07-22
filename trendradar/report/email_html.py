# coding=utf-8
"""
邮件专用轻量 HTML 渲染模块

Gmail 会在约 102KB 处裁剪邮件正文，完整网页报告（含 CSS/JS/订阅管理面板）
远超此限制。本模块生成一个无 JS、极简 CSS 的静态版本专供邮件推送：
- 只保留 AI 简报、分类热榜、RSS（摘要截断）、零命中提示
- 与网页版使用同一套沉静配色
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from trendradar.report.helpers import html_escape, order_stats_by_category, category_icon
from trendradar.ai.formatter import _format_list_content

# 邮件版摘要截断长度（字符）
EMAIL_SUMMARY_MAX_LEN = 140

_EMAIL_CSS = """
body{margin:0;padding:16px;background:#f4f3f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;color:#333;line-height:1.6}
.wrap{max-width:640px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;border:1px solid #e7e5e0}
.hd{background:#2f3e4e;color:#fff;padding:20px 24px}
.hd h1{margin:0;font-size:18px;font-weight:700}
.hd .meta{margin-top:6px;font-size:12px;opacity:.85}
.bd{padding:20px 24px}
.sec{margin-bottom:24px}
.sec-title{font-size:15px;font-weight:700;color:#2f3e4e;border-bottom:1px solid #e7e5e0;padding-bottom:6px;margin-bottom:12px}
.ai-block{margin-bottom:14px;padding:12px 14px;background:#f6f6f3;border-radius:8px}
.ai-block-title{font-size:13px;font-weight:700;color:#4b5b6b;margin-bottom:6px}
.ai-block-content{font-size:13px;color:#444;white-space:pre-wrap}
.cat{margin:16px 0 8px 0;padding:8px 12px;border-radius:6px;font-size:14px;font-weight:700}
.cat-0{background:#eef2f5;color:#33506b;border-left:3px solid #52708f}
.cat-1{background:#f5f1e8;color:#6b5636;border-left:3px solid #a8834e}
.grp{font-size:13px;font-weight:700;color:#1f2937;margin:10px 0 4px 0}
.grp .cnt{font-weight:400;color:#9ca3af;font-size:12px}
.it{font-size:13px;margin:4px 0;padding-left:8px}
.it .src{color:#9ca3af;font-size:11px;margin-right:6px}
.it a{color:#39648c;text-decoration:none}
.smry{font-size:12px;color:#6b7280;margin:2px 0 8px 16px}
.empty{margin-top:16px;padding:10px 12px;background:#f6f6f3;border-radius:6px;font-size:11px;color:#9ca3af}
.ft{padding:14px 24px;background:#faf9f7;border-top:1px solid #e7e5e0;font-size:11px;color:#9ca3af;text-align:center}
"""


def render_email_html(
    report_data: Dict,
    total_titles: int,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    rss_items: Optional[List[Dict]] = None,
    ai_analysis: Optional[Any] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
) -> str:
    """渲染邮件专用轻量 HTML（目标体积远小于 Gmail 102KB 裁剪线）"""
    now = get_time_func() if get_time_func else datetime.now()
    mode_display = {"current": "当前榜单", "incremental": "增量监控"}.get(mode, "全天汇总")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>情报简报</title><style>{_EMAIL_CSS}</style></head><body><div class="wrap">
<div class="hd"><h1>📡 情报简报 · {mode_display}</h1>
<div class="meta">{now.strftime("%Y-%m-%d %H:%M")} · 热榜命中 {sum(len(s["titles"]) for s in report_data.get("stats", []))} 条</div></div>
<div class="bd">"""

    # ---- AI 简报 ----
    if ai_analysis is not None and getattr(ai_analysis, "success", False):
        html += '<div class="sec"><div class="sec-title">✨ AI 情报分析</div>'
        for field, title in (
            ("core_trends", "今日核心研判"),
            ("sentiment_controversy", "客户与公司动态"),
            ("outlook_strategy", "值得跟踪的线索"),
        ):
            content = getattr(ai_analysis, field, None)
            if content:
                formatted = html_escape(_format_list_content(content))
                html += (
                    f'<div class="ai-block"><div class="ai-block-title">{title}</div>'
                    f'<div class="ai-block-content">{formatted}</div></div>'
                )
        html += "</div>"

    # ---- 分类热榜 ----
    stats = [s for s in report_data.get("stats", []) if s.get("count", 0) > 0]
    if stats:
        ordered, cat_order = order_stats_by_category(stats)
        html += '<div class="sec"><div class="sec-title">📊 关键词命中</div>'
        rendered_cat = object()
        for stat in ordered:
            cat = stat.get("category")
            if cat_order and cat != rendered_cat:
                rendered_cat = cat
                cat_idx = cat_order.index(cat)
                cat_name = cat if cat is not None else "其他"
                html += (
                    f'<div class="cat cat-{cat_idx % 2}">'
                    f"{category_icon(cat, cat_idx)} {html_escape(cat_name)}</div>"
                )
            html += (
                f'<div class="grp">{html_escape(stat["word"])} '
                f'<span class="cnt">{stat["count"]} 条</span></div>'
            )
            for title_data in stat["titles"]:
                link = title_data.get("mobile_url") or title_data.get("url", "")
                title_text = html_escape(title_data.get("title", ""))
                source = html_escape(title_data.get("source_name", ""))
                title_html = (
                    f'<a href="{html_escape(link)}">{title_text}</a>' if link else title_text
                )
                html += f'<div class="it"><span class="src">{source}</span>{title_html}</div>'
        html += "</div>"

    # ---- RSS（摘要截断） ----
    if rss_items:
        rss_nonempty = [s for s in rss_items if s.get("titles")]
        if rss_nonempty:
            ordered, cat_order = order_stats_by_category(rss_nonempty)
            html += '<div class="sec"><div class="sec-title">📰 RSS 订阅</div>'
            rendered_cat = object()
            for stat in ordered:
                cat = stat.get("category")
                if cat_order and cat != rendered_cat:
                    rendered_cat = cat
                    cat_idx = cat_order.index(cat)
                    cat_name = cat if cat is not None else "其他"
                    html += (
                        f'<div class="cat cat-{cat_idx % 2}">'
                        f"{category_icon(cat, cat_idx)} {html_escape(cat_name)}</div>"
                    )
                html += (
                    f'<div class="grp">{html_escape(stat["word"])} '
                    f'<span class="cnt">{len(stat["titles"])} 条</span></div>'
                )
                for title_data in stat["titles"]:
                    link = title_data.get("url", "")
                    title_text = html_escape(title_data.get("title", ""))
                    source = html_escape(title_data.get("source_name", ""))
                    title_html = (
                        f'<a href="{html_escape(link)}">{title_text}</a>' if link else title_text
                    )
                    html += f'<div class="it"><span class="src">{source}</span>{title_html}</div>'
                    summary = (title_data.get("summary") or "").strip()
                    if summary and summary != title_data.get("title", ""):
                        if len(summary) > EMAIL_SUMMARY_MAX_LEN:
                            summary = summary[:EMAIL_SUMMARY_MAX_LEN] + "…"
                        html += f'<div class="smry">{html_escape(summary)}</div>'
            html += "</div>"

    # ---- 零命中提示 ----
    empty_groups = report_data.get("empty_groups") or []
    if empty_groups:
        words = "、".join(html_escape(g["word"]) for g in empty_groups)
        html += f'<div class="empty">📭 今日无动态（{len(empty_groups)} 组）：{words}</div>'

    html += """</div>
<div class="ft">由 Coco Wang 制作 · 邮件精简版，完整交互报告请查看网页版</div>
</div></body></html>"""
    return html
