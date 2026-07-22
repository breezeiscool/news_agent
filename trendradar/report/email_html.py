# coding=utf-8
"""
邮件专用 HTML 渲染模块（Outlook 安全极简版）

设计目标（按用户要求）：
1. 邮件正文只有三样东西：一句话研判 + 两段 AI 分区总结（行业动态 / 公司监控）
   + 一个跳转完整网页报告的链接按钮；明细阅读全部发生在网页端。
2. Outlook 桌面版使用 Word 渲染引擎，不支持 <style> 块 / flex / 渐变 /
   border-radius，且对特殊字符敏感——因此这里使用表格布局、全内联样式、
   纯色背景、不用 emoji 与全角装饰符，避免乱码与格式错乱。
3. AI 未运行的时段（如午间速览）降级为：数字概览 + 前几条标题链接。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from trendradar.report.helpers import html_escape, order_stats_by_category, titles_similar


def _is_company_cat(name) -> bool:
    return bool(name) and any(h in name for h in ("公司", "客户", "监控"))


def _fmt_ai(text: str) -> str:
    """AI 文本 -> 邮件安全 HTML（转义 + 换行转 <br>）"""
    from trendradar.ai.formatter import _format_list_content

    return html_escape(_format_list_content(text)).replace("\n", "<br>")


def _merge_rss(report_data: Dict, rss_items: Optional[List[Dict]]) -> List[Dict]:
    """将 RSS 并入词组统计（若上游已合并则跳过），返回有更新的词组列表"""
    stats: List[Dict] = [dict(s) for s in report_data.get("stats", [])]
    already_merged = any(
        t.get("is_rss") for s in stats for t in s.get("titles", [])
    )
    stats_by_word = {s["word"]: s for s in stats}
    for rs in [] if already_merged else (rss_items or []):
        rss_titles = [dict(t, is_rss=True) for t in rs.get("titles", [])]
        if not rss_titles:
            continue
        target = stats_by_word.get(rs["word"])
        if target:
            existing = list(target["titles"])
            appended = []
            for t in rss_titles:
                dup = next(
                    (e for e in existing if titles_similar(e.get("title", ""), t.get("title", ""))),
                    None,
                )
                if dup is None:
                    appended.append(t)
            target["titles"] = existing + appended
            target["count"] = target.get("count", 0) + len(appended)
        else:
            new_stat = {
                "word": rs["word"], "count": len(rss_titles), "titles": rss_titles,
                "category": rs.get("category"), "position": rs.get("position", 999),
            }
            stats.append(new_stat)
            stats_by_word[rs["word"]] = new_stat
    return [s for s in stats if s.get("count", 0) > 0]


# 内联样式常量（Outlook 兼容：无渐变/圆角/flex）
_TD_BASE = "font-family:Arial,'Microsoft YaHei',sans-serif;"
_BLOCK_TITLE = (
    _TD_BASE + "font-size:14px;font-weight:bold;color:#14456b;"
    "padding:14px 24px 4px 24px;"
)
_BLOCK_TEXT = (
    _TD_BASE + "font-size:13px;color:#333333;line-height:1.7;"
    "padding:4px 24px 10px 24px;"
)


def render_email_html(
    report_data: Dict,
    total_titles: int,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    rss_items: Optional[List[Dict]] = None,
    ai_analysis: Optional[Any] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    report_url: str = "",
) -> str:
    """渲染 Outlook 安全的极简邮件：链接 + 两段 AI 分区总结"""
    now = get_time_func() if get_time_func else datetime.now()
    mode_display = {"current": "当前榜单", "incremental": "增量监控"}.get(mode, "全天汇总")

    active = _merge_rss(report_data, rss_items)
    company_updates = sum(1 for s in active if _is_company_cat(s.get("category")))
    industry_updates = sum(
        1 for s in active if s.get("category") and not _is_company_cat(s.get("category"))
    )
    total_picked = sum(s["count"] for s in active)

    ai_ok = ai_analysis is not None and getattr(ai_analysis, "success", False)
    core = (getattr(ai_analysis, "core_trends", "") or "").strip() if ai_ok else ""
    company_sum = (
        (getattr(ai_analysis, "sentiment_controversy", "") or "").strip() if ai_ok else ""
    )
    rows = ""

    # 页头（纯色，Outlook 不支持渐变）
    rows += (
        '<tr><td bgcolor="#14456b" style="' + _TD_BASE
        + 'padding:22px 24px 18px 24px;">'
        '<div style="font-size:19px;font-weight:bold;color:#ffffff;">产业情报简报</div>'
        f'<div style="font-size:12px;color:#b7cbdc;padding-top:5px;">{mode_display} · {now.strftime("%Y-%m-%d %H:%M")} 生成'
        f' · 行业动态 {industry_updates} 组 · 公司监控 {company_updates} 家 · 共 {total_picked} 条</div>'
        "</td></tr>"
    )

    if ai_ok and (core or company_sum):
        # 两段分区总结（各段第一行即本信息域的一句话研判，两域不混杂）
        if core:
            rows += (
                f'<tr><td style="{_BLOCK_TITLE}">一、行业动态速览</td></tr>'
                f'<tr><td style="{_BLOCK_TEXT}">{_fmt_ai(core)}</td></tr>'
            )
        if company_sum:
            rows += (
                f'<tr><td style="{_BLOCK_TITLE}">二、公司监控速览</td></tr>'
                f'<tr><td style="{_BLOCK_TEXT}">{_fmt_ai(company_sum)}</td></tr>'
            )
    else:
        # AI 未运行的降级：数字概览 + 前几条标题链接
        rows += (
            f'<tr><td style="{_BLOCK_TITLE}">本时段更新概览</td></tr>'
            f'<tr><td style="{_BLOCK_TEXT}">本时段未运行 AI 分析（增量/速览时段），'
            f"共有 {total_picked} 条更新，重点条目如下，完整内容请打开网页报告：</td></tr>"
        )
        ordered, _ = order_stats_by_category(active)
        shown = 0
        list_html = ""
        for s in ordered:
            for t in s.get("titles", []):
                if shown >= 6:
                    break
                link = t.get("mobile_url") or t.get("url", "")
                title_text = html_escape(t.get("title", ""))
                source = html_escape(t.get("source_name", ""))
                if link:
                    item = f'<a href="{html_escape(link)}" style="color:#1f6cab;text-decoration:none;">{title_text}</a>'
                else:
                    item = title_text
                list_html += (
                    f'<div style="padding:3px 0;">· {item}'
                    f'<span style="color:#999999;font-size:11px;">（{source}）</span></div>'
                )
                shown += 1
            if shown >= 6:
                break
        if list_html:
            rows += f'<tr><td style="{_BLOCK_TEXT}">{list_html}</td></tr>'

    # 查看完整报告按钮（表格按钮，Outlook 兼容）
    if report_url:
        rows += (
            '<tr><td align="center" style="padding:16px 24px 20px 24px;">'
            '<table cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td bgcolor="#2a6f97" style="{_TD_BASE}padding:10px 34px;">'
            f'<a href="{html_escape(report_url)}" '
            'style="font-size:14px;font-weight:bold;color:#ffffff;text-decoration:none;">'
            "打开完整网页报告</a></td></tr></table>"
            f'<div style="{_TD_BASE}font-size:11px;color:#999999;padding-top:8px;">'
            "完整报告含分区明细、公司聚类总结、历史日期与订阅管理</div>"
            "</td></tr>"
        )
    else:
        rows += (
            f'<tr><td style="{_BLOCK_TEXT}color:#999999;font-size:11px;">'
            "提示：配置 EMAIL_REPORT_URL（或开启 GitHub Pages）后，此处会显示完整报告链接"
            "</td></tr>"
        )

    # 页脚
    rows += (
        '<tr><td bgcolor="#f4f6f8" style="' + _TD_BASE
        + 'font-size:11px;color:#999999;padding:12px 24px;" align="center">'
        "由 Coco Wang 制作</td></tr>"
    )

    return (
        '<!DOCTYPE html><html><head>'
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
        "<title>产业情报简报</title></head>"
        '<body style="margin:0;padding:0;background-color:#eef2f6;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#eef2f6">'
        '<tr><td align="center" style="padding:20px 10px;">'
        '<table width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" '
        'style="border:1px solid #d3dde7;">'
        + rows
        + "</table></td></tr></table></body></html>"
    )
