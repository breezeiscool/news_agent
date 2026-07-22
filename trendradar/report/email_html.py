# coding=utf-8
"""
邮件专用 HTML 渲染模块（demo 风格紧凑版）

Gmail 会在约 102KB 处裁剪邮件正文，完整网页报告（含 CSS/JS/交互）远超此限制。
本模块生成与网页版同一套视觉语言（科技蓝渐变页头 / 分区配色 / 热度蓝阶）
但体积紧凑的静态版本，专供邮件推送：
- 页头：标题 + 一句话总研判 + 读者数字 + 标注图例
- 分区：行业动态（青蓝）在前、公司监控（深海蓝）在后，含无动态灰名单
- 条目：#排名徽标（蓝色深浅=热度）+ 来源 + 可点标题 + RSS 摘要
- 不用 flex/grid 等邮件客户端兼容性差的布局
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from trendradar.report.helpers import html_escape, order_stats_by_category, category_icon, titles_similar

# 邮件版摘要截断长度（字符）
EMAIL_SUMMARY_MAX_LEN = 160

_EMAIL_CSS = """
body{margin:0;padding:16px;background:#eef3f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;color:#333;line-height:1.55}
.wrap{max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #d3e2ef}
.hd{background:#14456b;background:linear-gradient(135deg,#0c2340 0%,#14456b 55%,#2a6f97 100%);color:#fff;padding:22px 26px;text-align:center}
.hd h1{margin:0;font-size:19px;font-weight:700}
.hd .sub{margin-top:5px;font-size:12px;opacity:.75}
.hd .headline{margin:12px auto 0 auto;font-size:14.5px;font-weight:600;line-height:1.6;max-width:560px;color:rgba(255,255,255,.95)}
.hd .quick{margin-top:12px}
.hd .qi{display:inline-block;font-size:12px;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.2);padding:4px 11px;border-radius:13px;margin:2px 3px}
.hd .legend{margin-top:12px;font-size:10.5px;opacity:.58;line-height:1.6;max-width:600px;margin-left:auto;margin-right:auto}
.bd{padding:18px 22px}
.ai{margin-bottom:20px;padding:16px;background:#f2f7fb;border:1px solid #d9e6f0;border-radius:10px}
.ai-hd{font-size:15px;font-weight:700;color:#174e7c;margin-bottom:10px}
.ai-block{margin-bottom:12px;padding:12px 14px;background:#fff;border-radius:8px}
.ai-block:last-child{margin-bottom:0}
.ai-block-t{font-size:13px;font-weight:700;color:#174e7c;margin-bottom:6px}
.ai-block-c{font-size:13px;color:#3c4650;white-space:pre-wrap}
.ai-side{border-left:3px solid #2a6f97;background:#eff5fa}
.zone{margin-bottom:18px;border-radius:10px;padding:14px 16px;border:1px solid}
.zone-ind{background:#f2f9fb;border-color:#cfe6ed}
.zone-com{background:#f4f8fc;border-color:#d3e2ef}
.zone-hd{font-size:15px;font-weight:700;padding-bottom:8px;margin-bottom:10px;border-bottom:2px solid rgba(0,0,0,.05)}
.zone-ind .zone-hd{color:#125a72}
.zone-com .zone-hd{color:#14456b}
.zone-meta{font-weight:400;font-size:11px;opacity:.6;margin-left:8px}
.grp{font-size:13.5px;font-weight:700;color:#1f2937;margin:12px 0 4px 0;padding-bottom:3px;border-bottom:1px solid rgba(0,0,0,.06)}
.grp:first-of-type{margin-top:0}
.grp .cnt{font-weight:400;color:#93a8ba;font-size:11px;margin-left:6px}
.it{font-size:13px;margin:5px 0;padding-left:2px}
.src{color:#93a8ba;font-size:11px;margin-right:6px}
.rk{display:inline-block;color:#fff;font-size:10px;font-weight:700;padding:1px 6px;border-radius:9px;margin-right:5px;background:#93a8ba}
.rk-top{background:#16548f}
.rk-high{background:#4d8ec4}
.rss-tag{display:inline-block;font-size:9.5px;font-weight:700;color:#1e7f9e;background:#d7ebf1;padding:1px 5px;border-radius:4px;margin-right:5px}
.it a{color:#1f6cab;text-decoration:none}
.smry{font-size:12px;color:#6b7280;margin:2px 0 8px 14px;line-height:1.55}
.cluster{padding:6px 0;border-bottom:1px solid rgba(0,0,0,.05)}
.cluster:last-child{border-bottom:none}
.cluster-hd{font-size:13px;font-weight:700;color:#174e7c}
.cluster-cnt{font-weight:400;font-size:10.5px;color:#93a8ba;margin-left:5px}
.cluster-sum{font-size:12.5px;line-height:1.6;color:#3c4650;margin-top:2px}
.cite{font-size:10.5px;font-weight:600;color:#1f6cab;text-decoration:none;margin-left:2px}
.mut{margin-top:12px;padding:9px 12px;background:rgba(255,255,255,.65);border-radius:7px;font-size:11px;color:#93a8ba;line-height:1.7}
.mut b{color:#6b7f92}
.runline{margin-top:4px;font-size:11px;color:#93a8ba;text-align:center}
.ft{padding:13px 22px;background:#f7fafc;border-top:1px solid #e3edf5;font-size:11px;color:#93a8ba;text-align:center}
"""


def _is_company_cat(name) -> bool:
    return bool(name) and any(h in name for h in ("公司", "客户", "监控"))


def _fmt_ai(text: str) -> str:
    from trendradar.ai.formatter import _format_list_content

    return html_escape(_format_list_content(text))


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
    """渲染邮件专用紧凑 HTML（与网页版同一套视觉语言，体积远小于 Gmail 102KB 裁剪线）"""
    now = get_time_func() if get_time_func else datetime.now()
    mode_display = {"current": "当前榜单", "incremental": "增量监控"}.get(mode, "全天汇总")

    # ── 将 RSS 条目并入词组（与网页版一致，避免重复分区） ──
    # 网页版渲染可能已把 RSS 并入 report_data["stats"]（原地修改），
    # 此时跳过合并，避免条目重复计数
    stats: List[Dict] = [dict(s) for s in report_data.get("stats", [])]
    already_merged = any(
        t.get("is_rss") for s in stats for t in s.get("titles", [])
    )
    stats_by_word = {s["word"]: s for s in stats}
    for rs in [] if already_merged else (rss_items or []):
        rss_titles = []
        for t in rs.get("titles", []):
            t = dict(t)
            t["is_rss"] = True
            rss_titles.append(t)
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
                if dup is not None:
                    src = t.get("source_name", "")
                    if src and src not in dup.get("source_name", ""):
                        dup["source_name"] = f"{dup['source_name']} / {src}"
                    if not dup.get("summary") and t.get("summary"):
                        dup["summary"] = t["summary"]
                    continue
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

    active = [s for s in stats if s.get("count", 0) > 0]
    nonzero_words = {s["word"] for s in active}
    empty_groups = [
        g for g in (report_data.get("empty_groups") or [])
        if g["word"] not in nonzero_words
    ]

    # 读者数字
    company_updates = sum(1 for s in active if _is_company_cat(s.get("category")))
    industry_updates = sum(
        1 for s in active if s.get("category") and not _is_company_cat(s.get("category"))
    )
    total_picked = sum(s["count"] for s in active)

    # 一句话总研判
    headline = ""
    ai_ok = ai_analysis is not None and getattr(ai_analysis, "success", False)
    if ai_ok:
        core_text = (getattr(ai_analysis, "core_trends", "") or "").strip()
        if core_text:
            headline = core_text.split("\n")[0].strip()
            if len(headline) > 90:
                headline = headline[:90] + "…"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>产业情报简报</title><style>{_EMAIL_CSS}</style></head><body><div class="wrap">
<div class="hd">
<h1>产业情报简报</h1>
<div class="sub">{mode_display} · {now.strftime("%m-%d %H:%M")} 生成</div>"""
    if headline:
        html += f"""
<div class="headline">「{html_escape(headline)}」</div>"""
    quick = []
    if industry_updates:
        quick.append(f'<span class="qi">📡 行业动态 <b>{industry_updates}</b> 组更新</span>')
    if company_updates:
        quick.append(f'<span class="qi">🏢 客户动态 <b>{company_updates}</b> 家</span>')
    quick.append(f'<span class="qi">📰 精选 <b>{total_picked}</b> 条</span>')
    html += f"""
<div class="quick">{"".join(quick)}</div>
<div class="legend">标注说明：<b>#n</b>＝该平台热榜排名（颜色越深越靠前）· <b>n次</b>＝当日累计上榜次数 · <b>RSS</b>＝订阅源文章（附摘要）</div>
</div>
<div class="bd">"""

    # ── AI 情报分析 ──
    if ai_ok:
        blocks = ""
        core = getattr(ai_analysis, "core_trends", None)
        if core:
            blocks += f'<div class="ai-block"><div class="ai-block-t">今日核心研判</div><div class="ai-block-c">{_fmt_ai(core)}</div></div>'
        cust = getattr(ai_analysis, "sentiment_controversy", None)
        if cust:
            blocks += f'<div class="ai-block"><div class="ai-block-t">客户与公司动态</div><div class="ai-block-c">{_fmt_ai(cust)}</div></div>'
        leads = getattr(ai_analysis, "outlook_strategy", None)
        if leads:
            blocks += f'<div class="ai-block ai-side"><div class="ai-block-t">📌 值得跟踪的线索</div><div class="ai-block-c">{_fmt_ai(leads)}</div></div>'
        if blocks:
            html += f'<div class="ai"><div class="ai-hd">✨ AI 情报分析</div>{blocks}</div>'

    # ── 分区（行业动态在前、公司监控在后，与网页版一致） ──
    def render_item(title_data: Dict) -> str:
        item = '<div class="it">'
        if title_data.get("is_rss"):
            item += '<span class="rss-tag">RSS</span>'
        else:
            ranks = title_data.get("ranks", [])
            if ranks:
                min_rank = min(ranks)
                max_rank = max(ranks)
                threshold = title_data.get("rank_threshold", 10)
                rk_class = "rk-top" if min_rank <= 3 else ("rk-high" if min_rank <= threshold else "")
                rk_text = str(min_rank) if min_rank == max_rank else f"{min_rank}-{max_rank}"
                item += f'<span class="rk {rk_class}">#{rk_text}</span>'
        item += f'<span class="src">{html_escape(title_data.get("source_name", ""))}</span>'
        count_info = title_data.get("count", 1)
        link = title_data.get("mobile_url") or title_data.get("url", "")
        title_text = html_escape(title_data.get("title", ""))
        if link:
            item += f'<a href="{html_escape(link)}">{title_text}</a>'
        else:
            item += title_text
        if count_info > 1:
            item += f'<span class="src"> {count_info}次</span>'
        item += "</div>"
        summary = (title_data.get("summary") or "").strip()
        if summary and summary != title_data.get("title", ""):
            if len(summary) > EMAIL_SUMMARY_MAX_LEN:
                summary = summary[:EMAIL_SUMMARY_MAX_LEN] + "…"
            item += f'<div class="smry">{html_escape(summary)}</div>'
        return item

    ordered, cat_order = order_stats_by_category(active)
    display_cats = sorted(cat_order, key=lambda c: 1 if _is_company_cat(c if c is not None else "") else 0)
    for cat in display_cats:
        cat_stats = [s for s in ordered if s.get("category") == cat]
        cat_empty = [g["word"] for g in empty_groups if g.get("category") == cat]
        if not cat_stats and not cat_empty:
            continue
        cat_name = cat if cat is not None else "其他"
        is_company = _is_company_cat(cat_name)
        zone_class = "zone-com" if is_company else "zone-ind"
        cat_idx = display_cats.index(cat)
        total_items = sum(s["count"] for s in cat_stats)
        html += f"""
<div class="zone {zone_class}"><div class="zone-hd">{category_icon(cat_name, cat_idx)} {html_escape(cat_name)}<span class="zone-meta">{len(cat_stats)} 组有更新 · {total_items} 条</span></div>"""
        industry_summaries = (
            getattr(ai_analysis, "industry_summaries", None) or {} if ai_ok else {}
        )
        for s in cat_stats:
            html += f'<div class="grp">{html_escape(s["word"])}<span class="cnt">{s["count"]} 条</span></div>'
            if not is_company and industry_summaries:
                # 行业组：按命中公司/主题聚类，有 AI 总结的簇只展示总结+引用角标
                clusters = {}
                for t in s["titles"]:
                    sub = t.get("matched_word") or s["word"]
                    clusters.setdefault(sub, []).append(t)
                for sub, items in clusters.items():
                    summary = industry_summaries.get(f"{s['word']}/{sub}")
                    if summary and len(items) >= 2:
                        cites = ""
                        for ci, t in enumerate(items, 1):
                            link = t.get("mobile_url") or t.get("url", "")
                            tip = f"{t.get('title', '')} ｜ {t.get('source_name', '')}"
                            if link:
                                cites += f'<a class="cite" href="{html_escape(link)}" title="{html_escape(tip)}">[{ci}]</a>'
                            else:
                                cites += f'<span class="cite" title="{html_escape(tip)}">[{ci}]</span>'
                        html += (
                            '<div class="cluster">'
                            f'<div class="cluster-hd">{html_escape(sub)}<span class="cluster-cnt">{len(items)} 条</span></div>'
                            f'<div class="cluster-sum">{html_escape(summary)}{cites}</div>'
                            '</div>'
                        )
                    else:
                        for t in items:
                            html += render_item(t)
            else:
                for t in s["titles"]:
                    html += render_item(t)
        if cat_empty:
            label = "今日无相关资讯" if is_company else "今日无动态"
            html += f'<div class="mut"><b>📭 {label}（{len(cat_empty)} 组）：</b>{html_escape("、".join(cat_empty))}</div>'
        html += "</div>"

    # ── 运行统计（一行小字） ──
    hotlist_total = report_data.get("hotlist_total", total_titles)
    hot_count = sum(1 for s in active for t in s["titles"] if not t.get("is_rss"))
    rss_count = sum(1 for s in active for t in s["titles"] if t.get("is_rss"))
    html += f"""
<div class="runline">运行统计：热榜命中 {hot_count} / {hotlist_total} · RSS {rss_count} 条 · 生成于 {now.strftime("%Y-%m-%d %H:%M")}</div>
</div>
<div class="ft">由 Coco Wang 制作 · 邮件紧凑版，完整交互报告请查看网页版</div>
</div></body></html>"""
    return html
