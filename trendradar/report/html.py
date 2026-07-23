# coding=utf-8
"""
HTML 报告渲染模块

提供 HTML 格式的热点新闻报告生成功能
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from trendradar.report.helpers import (
    html_escape,
    calculate_rank_trend,
    category_icon as _category_icon,
    order_stats_by_category as _order_stats_by_category,
    titles_similar as _titles_similar,
)
from trendradar.utils.time import convert_time_for_display
from trendradar.ai.formatter import render_ai_analysis_html_rich


# 订阅管理面板样式（仅用于独立管理页面 output/html/manager.html）
_CM_CSS = """
            /* ===== 订阅管理面板 ===== */
            .config-manager {
                margin-top: 32px;
            }
            .cm-header { margin-bottom: 16px; }
            .cm-title {
                font-size: 18px;
                font-weight: 700;
                color: #1a1a1a;
                margin-bottom: 4px;
            }
            .cm-sub { font-size: 13px; color: #6b7280; line-height: 1.5; }
            .cm-grid { display: flex; flex-direction: column; gap: 20px; }
            body.wide-mode .cm-grid { flex-direction: row; align-items: flex-start; }
            body.wide-mode .cm-panel { flex: 1; min-width: 0; }
            .cm-panel {
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 16px;
                background: #eef3f8;
            }
            .cm-panel-title { font-size: 15px; font-weight: 600; color: #374151; margin-bottom: 12px; }
            .cm-list-label { font-size: 13px; font-weight: 600; color: #4b5563; margin: 12px 0 6px 0; }
            .cm-hint { font-weight: 400; color: #9ca3af; font-size: 12px; font-family: 'SF Mono', Consolas, monospace; }
            .cm-list { max-height: 300px; overflow-y: auto; }
            .cm-group-list { max-height: 380px; }
            .cm-cat-label {
                font-size: 12px;
                font-weight: 700;
                color: #2a6f97;
                margin: 10px 0 4px 0;
                text-transform: none;
            }
            .cm-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 8px;
                border-radius: 6px;
                font-size: 13px;
            }
            .cm-item:hover { background: #f3f4f6; }
            .cm-item-name { font-weight: 600; color: #1f2937; flex-shrink: 0; }
            .cm-item-detail {
                color: #9ca3af;
                font-size: 12px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                flex: 1;
                min-width: 0;
            }
            .cm-del {
                background: none;
                border: none;
                color: #d1d5db;
                cursor: pointer;
                font-size: 12px;
                padding: 2px 6px;
                border-radius: 4px;
                flex-shrink: 0;
            }
            .cm-del:hover { color: #a3564a; background: #fee2e2; }
            .cm-empty { color: #9ca3af; font-size: 13px; padding: 8px; }
            .cm-add-row { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
            .cm-add-row input, .cm-add-row select {
                flex: 1;
                min-width: 90px;
                padding: 7px 10px;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                font-size: 13px;
                outline: none;
            }
            .cm-add-row input:focus, .cm-add-row select:focus { border-color: #2a6f97; }
            .cm-btn {
                padding: 7px 12px;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                background: white;
                color: #374151;
                font-size: 13px;
                cursor: pointer;
                white-space: nowrap;
                transition: all 0.15s;
            }
            .cm-btn:hover { border-color: #2a6f97; color: #2a6f97; }
            .cm-btn-primary { background: #2a6f97; border-color: #2a6f97; color: white; }
            .cm-btn-primary:hover { background: #1b5886; color: white; }
            .cm-actions { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
            .cm-raw {
                width: 100%;
                min-height: 260px;
                margin-top: 10px;
                padding: 10px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                font-family: 'SF Mono', Consolas, monospace;
                font-size: 12px;
                line-height: 1.6;
                box-sizing: border-box;
                resize: vertical;
                outline: none;
            }
            .cm-raw:focus { border-color: #2a6f97; }
            .cm-note { margin-top: 14px; font-size: 12px; color: #9ca3af; line-height: 1.5; }

            body.dark-mode .cm-title { color: #f1f5f9; }
            body.dark-mode .cm-sub, body.dark-mode .cm-note { color: #94a3b8; }
            body.dark-mode .cm-panel { background: #0f172a; border-color: #334155; }
            body.dark-mode .cm-panel-title { color: #e2e8f0; }
            body.dark-mode .cm-list-label { color: #cbd5e1; }
            body.dark-mode .cm-cat-label { color: #a4c6de; }
            body.dark-mode .cm-item:hover { background: #1e293b; }
            body.dark-mode .cm-item-name { color: #e2e8f0; }
            body.dark-mode .cm-add-row input, body.dark-mode .cm-add-row select,
            body.dark-mode .cm-raw {
                background: #1e293b;
                border-color: #334155;
                color: #e2e8f0;
            }
            body.dark-mode .cm-btn { background: #1e293b; border-color: #334155; color: #cbd5e1; }
            body.dark-mode .cm-btn:hover { border-color: #7fb2d9; color: #a4c6de; }
            body.dark-mode .cm-btn-primary { background: #2f6690; border-color: #2f6690; color: white; }
            body.dark-mode .cm-del:hover { color: #fca5a5; background: #450a0a; }

"""


def _render_config_manager_section(data: Dict) -> str:
    """渲染订阅管理面板（纯前端编辑，生成配置文件供下载/复制）

    默认 display:none，由页面 JS 显示——邮件客户端不执行 JS，
    因此该面板只在浏览器中可见，不会污染邮件推送。

    Args:
        data: {"frequency_raw": str, "platforms": [{id,name}], "rss_feeds": [{id,name,url}]}
    """
    # 防 </script> 注入：JSON 中的 "</" 转义
    payload = json.dumps(
        {
            "frequencyRaw": data.get("frequency_raw", ""),
            "platforms": data.get("platforms", []),
            "rssFeeds": data.get("rss_feeds", []),
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    return """
                <div class="config-manager section-divider" id="configManager" style="display:none">
                    <div class="cm-header">
                        <div class="cm-title">⚙️ 订阅管理</div>
                        <div class="cm-sub">增删信息源、监控公司与产业词组。修改后下载/复制新配置，覆盖仓库 config/ 下对应文件，下次运行生效。</div>
                    </div>
                    <div class="cm-grid">
                        <div class="cm-panel">
                            <div class="cm-panel-title">📡 信息源</div>
                            <div class="cm-list-label">热榜平台 <span class="cm-hint">config.yaml → platforms.sources</span></div>
                            <div id="cmPlatformList" class="cm-list"></div>
                            <div class="cm-add-row">
                                <input id="cmPlatId" placeholder="平台 id（如 zhihu）">
                                <input id="cmPlatName" placeholder="显示名称（如 知乎）">
                                <button class="cm-btn" onclick="cmAddPlatform()">＋ 添加</button>
                            </div>
                            <div class="cm-list-label">RSS 订阅源 <span class="cm-hint">config.yaml → rss.feeds</span></div>
                            <div id="cmRssList" class="cm-list"></div>
                            <div class="cm-add-row">
                                <input id="cmRssId" placeholder="id（如 36kr）">
                                <input id="cmRssName" placeholder="名称">
                                <input id="cmRssUrl" placeholder="订阅地址 https://...">
                                <button class="cm-btn" onclick="cmAddRss()">＋ 添加</button>
                            </div>
                            <div class="cm-actions">
                                <button class="cm-btn cm-btn-primary" onclick="cmCopySources(this)">复制 config.yaml 片段</button>
                                <button class="cm-btn" onclick="cmDownloadSources()">下载片段</button>
                            </div>
                        </div>
                        <div class="cm-panel">
                            <div class="cm-panel-title">🔍 监控词组（公司 / 产业）</div>
                            <div id="cmGroupList" class="cm-list cm-group-list"></div>
                            <div class="cm-add-row">
                                <select id="cmGroupCat"></select>
                                <input id="cmGroupName" placeholder="组名（如 阿里巴巴）">
                                <input id="cmGroupWords" placeholder="关键词，逗号分隔（如 阿里巴巴,Alibaba,阿里云）">
                                <button class="cm-btn" onclick="cmAddGroup()">＋ 添加</button>
                            </div>
                            <div class="cm-actions">
                                <button class="cm-btn cm-btn-primary" onclick="cmCopyFrequency(this)">复制 frequency_words.txt</button>
                                <button class="cm-btn" onclick="cmDownloadFrequency()">下载 frequency_words.txt</button>
                                <button class="cm-btn" onclick="cmToggleRaw()">高级编辑</button>
                            </div>
                            <textarea id="cmRawText" class="cm-raw" style="display:none" spellcheck="false" oninput="cmRenderGroups()"></textarea>
                        </div>
                    </div>
                    <div class="cm-note">提示：本页面的修改只是预览，不会自动写回服务器。GitHub 部署可直接在仓库网页编辑 config/frequency_words.txt 与 config.yaml 后提交。</div>
                </div>
                <script id="cmData" type="application/json">""" + payload + """</script>
                <script>
                (function() {
                    var cmData;
                    try { cmData = JSON.parse(document.getElementById('cmData').textContent); } catch(e) { return; }
                    window.cmPlatforms = cmData.platforms || [];
                    window.cmRss = cmData.rssFeeds || [];
                    var rawEl = document.getElementById('cmRawText');
                    rawEl.value = cmData.frequencyRaw || '';

                    var CAT_RE = /^\\[(?:分类|CATEGORY)\\s*[:：]\\s*(.+?)\\]$/i;

                    window.cmParseFreq = function(raw) {
                        var paras = raw.replace(/[ \\t]+$/gm, '').split(/\\n{2,}/);
                        var cat = null, blocks = [];
                        paras.forEach(function(p) {
                            if (!p.trim()) return;
                            var lines = p.trim().split('\\n');
                            var contentLines = lines.filter(function(l) { return l.trim() && l.trim().charAt(0) !== '#'; });
                            var first = contentLines.length ? contentLines[0].trim() : '';
                            var catMatch = first.match(CAT_RE);
                            if (catMatch && contentLines.length === 1) {
                                cat = catMatch[1].trim();
                                blocks.push({type: 'category', text: p, category: cat});
                                return;
                            }
                            var isMarker = /^\\[(GLOBAL_FILTER|WORD_GROUPS)\\]$/i.test(first);
                            var isFilterBlock = '!+@'.indexOf(first.charAt(0)) !== -1;
                            if (!first || isMarker || isFilterBlock) {
                                blocks.push({type: 'raw', text: p, category: cat});
                                return;
                            }
                            var name = first;
                            var aliasMatch = first.match(/^\\[(.+)\\]$/);
                            if (aliasMatch) name = aliasMatch[1];
                            var words = contentLines.slice(aliasMatch ? 1 : 0).map(function(l) { return l.trim(); });
                            blocks.push({type: 'group', text: p, category: cat, name: name, words: words});
                        });
                        return blocks;
                    };

                    window.cmRenderGroups = function() {
                        var blocks = cmParseFreq(rawEl.value);
                        var listEl = document.getElementById('cmGroupList');
                        var catSel = document.getElementById('cmGroupCat');
                        var html = '', cats = [], lastCat = null;
                        blocks.forEach(function(b, idx) {
                            if (b.type === 'category' && cats.indexOf(b.category) === -1) cats.push(b.category);
                            if (b.type !== 'group') return;
                            if (b.category !== lastCat) {
                                lastCat = b.category;
                                html += '<div class="cm-cat-label">' + cmEsc(b.category || '未分类') + '</div>';
                            }
                            var preview = b.words.slice(0, 4).join('、');
                            if (b.words.length > 4) preview += ' 等' + b.words.length + '词';
                            html += '<div class="cm-item"><span class="cm-item-name">' + cmEsc(b.name) + '</span>'
                                + '<span class="cm-item-detail" title="' + cmEsc(b.words.join(', ')) + '">' + cmEsc(preview) + '</span>'
                                + '<button class="cm-del" title="删除该词组" onclick="cmDelGroup(' + idx + ')">✕</button></div>';
                        });
                        listEl.innerHTML = html || '<div class="cm-empty">暂无词组</div>';
                        if (catSel) {
                            var cur = catSel.value;
                            catSel.innerHTML = cats.map(function(c) { return '<option value="' + cmEsc(c) + '">' + cmEsc(c) + '</option>'; }).join('');
                            if (cur) catSel.value = cur;
                        }
                    };

                    window.cmDelGroup = function(idx) {
                        var blocks = cmParseFreq(rawEl.value);
                        if (!blocks[idx] || blocks[idx].type !== 'group') return;
                        if (!confirm('删除词组「' + blocks[idx].name + '」？')) return;
                        blocks.splice(idx, 1);
                        rawEl.value = blocks.map(function(b) { return b.text; }).join('\\n\\n') + '\\n';
                        cmRenderGroups();
                    };

                    window.cmAddGroup = function() {
                        var cat = document.getElementById('cmGroupCat').value;
                        var name = document.getElementById('cmGroupName').value.trim();
                        var words = document.getElementById('cmGroupWords').value.split(/[,，、]/).map(function(w) { return w.trim(); }).filter(Boolean);
                        if (!name || !words.length) { alert('请填写组名和至少一个关键词'); return; }
                        var blocks = cmParseFreq(rawEl.value);
                        var newText = '[' + name + ']\\n' + words.join('\\n');
                        var insertAt = blocks.length;
                        for (var i = blocks.length - 1; i >= 0; i--) {
                            if (blocks[i].category === cat && (blocks[i].type === 'group' || blocks[i].type === 'category')) { insertAt = i + 1; break; }
                        }
                        blocks.splice(insertAt, 0, {type: 'group', text: newText, category: cat, name: name, words: words});
                        rawEl.value = blocks.map(function(b) { return b.text; }).join('\\n\\n') + '\\n';
                        document.getElementById('cmGroupName').value = '';
                        document.getElementById('cmGroupWords').value = '';
                        cmRenderGroups();
                    };

                    window.cmRenderSources = function() {
                        var pEl = document.getElementById('cmPlatformList');
                        pEl.innerHTML = cmPlatforms.map(function(p, i) {
                            return '<div class="cm-item"><span class="cm-item-name">' + cmEsc(p.name) + '</span>'
                                + '<span class="cm-item-detail">' + cmEsc(p.id) + '</span>'
                                + '<button class="cm-del" onclick="cmDelPlatform(' + i + ')">✕</button></div>';
                        }).join('') || '<div class="cm-empty">暂无平台</div>';
                        var rEl = document.getElementById('cmRssList');
                        rEl.innerHTML = cmRss.map(function(f, i) {
                            return '<div class="cm-item"><span class="cm-item-name">' + cmEsc(f.name) + '</span>'
                                + '<span class="cm-item-detail" title="' + cmEsc(f.url) + '">' + cmEsc(f.url) + '</span>'
                                + '<button class="cm-del" onclick="cmDelRss(' + i + ')">✕</button></div>';
                        }).join('') || '<div class="cm-empty">暂无 RSS 源</div>';
                    };

                    window.cmDelPlatform = function(i) { cmPlatforms.splice(i, 1); cmRenderSources(); };
                    window.cmDelRss = function(i) { cmRss.splice(i, 1); cmRenderSources(); };
                    window.cmAddPlatform = function() {
                        var id = document.getElementById('cmPlatId').value.trim();
                        var name = document.getElementById('cmPlatName').value.trim();
                        if (!id) { alert('请填写平台 id'); return; }
                        cmPlatforms.push({id: id, name: name || id});
                        document.getElementById('cmPlatId').value = '';
                        document.getElementById('cmPlatName').value = '';
                        cmRenderSources();
                    };
                    window.cmAddRss = function() {
                        var id = document.getElementById('cmRssId').value.trim();
                        var name = document.getElementById('cmRssName').value.trim();
                        var url = document.getElementById('cmRssUrl').value.trim();
                        if (!id || !url) { alert('请填写 id 和订阅地址'); return; }
                        cmRss.push({id: id, name: name || id, url: url});
                        document.getElementById('cmRssId').value = '';
                        document.getElementById('cmRssName').value = '';
                        document.getElementById('cmRssUrl').value = '';
                        cmRenderSources();
                    };

                    window.cmSourcesYaml = function() {
                        var y = '# ===== 热榜平台：替换 config.yaml 中 platforms.sources 列表 =====\\n';
                        y += 'platforms:\\n  enabled: true\\n  sources:\\n';
                        cmPlatforms.forEach(function(p) { y += '    - id: "' + p.id + '"\\n      name: "' + p.name + '"\\n'; });
                        y += '\\n# ===== RSS 源：替换 config.yaml 中 rss.feeds 列表 =====\\nrss:\\n  feeds:\\n';
                        cmRss.forEach(function(f) { y += '    - id: "' + f.id + '"\\n      name: "' + f.name + '"\\n      url: "' + f.url + '"\\n'; });
                        return y;
                    };

                    function cmCopy(text, btn) {
                        function done() {
                            if (!btn) return;
                            var t = btn.textContent;
                            btn.textContent = '✓ 已复制';
                            setTimeout(function() { btn.textContent = t; }, 1500);
                        }
                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            navigator.clipboard.writeText(text).then(done);
                        } else {
                            var ta = document.createElement('textarea');
                            ta.value = text; document.body.appendChild(ta); ta.select();
                            try { document.execCommand('copy'); done(); } catch(e) {}
                            document.body.removeChild(ta);
                        }
                    }
                    function cmDownload(text, filename) {
                        var blob = new Blob([text], {type: 'text/plain;charset=utf-8'});
                        var a = document.createElement('a');
                        a.href = URL.createObjectURL(blob);
                        a.download = filename;
                        document.body.appendChild(a); a.click(); document.body.removeChild(a);
                        URL.revokeObjectURL(a.href);
                    }
                    window.cmCopySources = function(btn) { cmCopy(cmSourcesYaml(), btn); };
                    window.cmDownloadSources = function() { cmDownload(cmSourcesYaml(), 'sources-snippet.yaml'); };
                    window.cmCopyFrequency = function(btn) { cmCopy(rawEl.value, btn); };
                    window.cmDownloadFrequency = function() { cmDownload(rawEl.value, 'frequency_words.txt'); };
                    window.cmToggleRaw = function() {
                        rawEl.style.display = rawEl.style.display === 'none' ? 'block' : 'none';
                    };
                    window.cmEsc = function(s) {
                        return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                    };

                    document.getElementById('configManager').style.display = '';
                    cmRenderSources();
                    cmRenderGroups();
                })();
                </script>"""




def render_config_manager_page(data: Dict) -> str:
    """渲染独立的订阅管理页面（写入 output/html/manager.html）

    与推送报告解耦：报告页面不再内嵌管理面板，
    信息源与关键词在此单独管理。
    """
    section = _render_config_manager_section(data)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>订阅管理 · 情报雷达</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 24px 16px; background: #eef3f8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; color: #333; line-height: 1.5; }}
.mgr-wrap {{ max-width: 1100px; margin: 0 auto; }}
.mgr-header {{ background: linear-gradient(135deg, #0c2340 0%, #14456b 55%, #2a6f97 100%); color: #fff; border-radius: 12px; padding: 22px 28px; margin-bottom: 20px; }}
.mgr-header h1 {{ margin: 0 0 6px 0; font-size: 20px; }}
.mgr-header p {{ margin: 0; font-size: 13px; opacity: 0.85; }}
.mgr-body {{ background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #d3e2ef; }}
{_CM_CSS}
.mgr-body .cm-header {{ display: none; }} /* 页头已有标题，隐藏面板内的重复标题 */
.mgr-body .config-manager {{ margin-top: 0; }}
@media (min-width: 900px) {{
    .mgr-wrap .cm-grid {{ flex-direction: row; align-items: flex-start; }}
    .mgr-wrap .cm-panel {{ flex: 1; min-width: 0; }}
}}
</style>
</head>
<body>
<div class="mgr-wrap">
    <div class="mgr-header">
        <h1>⚙️ 订阅管理</h1>
        <p>在这里增删信息源与监控词组，生成新配置后覆盖仓库 config/ 下对应文件，下次运行生效。此页面独立于推送报告，不会出现在邮件或推送内容中。</p>
    </div>
    <div class="mgr-body">{section}</div>
</div>
</body>
</html>"""

def render_html_content(
    report_data: Dict,
    total_titles: int,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    region_order: Optional[List[str]] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    display_mode: str = "keyword",
    standalone_data: Optional[Dict] = None,
    ai_analysis: Optional[Any] = None,
    show_new_section: bool = True,
    config_manager_data: Optional[Dict] = None,
) -> str:
    """渲染HTML内容

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        total_titles: 新闻总数
        mode: 报告模式 ("daily", "current", "incremental")
        update_info: 更新信息（可选）
        region_order: 区域显示顺序列表
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now）
        rss_items: RSS 统计条目列表（可选）
        rss_new_items: RSS 新增条目列表（可选）
        display_mode: 显示模式 ("keyword"=按关键词分组, "platform"=按平台分组)
        standalone_data: 独立展示区数据（可选），包含 platforms 和 rss_feeds
        ai_analysis: AI 分析结果对象（可选），AIAnalysisResult 实例
        show_new_section: 是否显示新增热点区域
        config_manager_data: 订阅管理面板数据（可选），含 frequency_raw/platforms/rss_feeds，
            提供后在页面底部渲染可交互的信息源与词组管理面板（仅浏览器可见）

    Returns:
        渲染后的 HTML 字符串
    """
    # 默认区域顺序
    default_region_order = ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]
    if region_order is None:
        region_order = default_region_order

    # ── RSS 并入两大分区 ──
    # RSS 与热榜按同一套关键词分组，分开展示会造成两块重复内容；
    # 当 hotlist 与 rss 区域同时启用时，把 RSS 条目合并进对应词组统一展示，
    # rss 独立区域随之不再渲染（rss_new_items 新增区不受影响）。
    merged_rss = False
    if rss_items and "hotlist" in region_order and "rss" in region_order:
        stats_by_word = {s["word"]: s for s in report_data["stats"]}
        for rs in rss_items:
            rss_titles = []
            for t in rs.get("titles", []):
                t = dict(t)
                t["is_rss"] = True
                rss_titles.append(t)
            if not rss_titles:
                continue
            target = stats_by_word.get(rs["word"])
            if target:
                # 与已有条目相似的 RSS 视为同一事件：合并信源、补充摘要，不重复展示
                existing = list(target["titles"])
                appended = []
                for t in rss_titles:
                    dup = next(
                        (e for e in existing if _titles_similar(e.get("title", ""), t.get("title", ""))),
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
                    "word": rs["word"],
                    "count": len(rss_titles),
                    "titles": rss_titles,
                    "category": rs.get("category"),
                    "position": rs.get("position", 999),
                    "percentage": 0,
                }
                report_data["stats"].append(new_stat)
                stats_by_word[rs["word"]] = new_stat
        # 合并后修正零命中列表（仅有 RSS 动态的词组不再算"无动态"）
        nonzero_words = {s["word"] for s in report_data["stats"] if s.get("count", 0) > 0}
        if report_data.get("empty_groups"):
            report_data["empty_groups"] = [
                g for g in report_data["empty_groups"] if g["word"] not in nonzero_words
            ]
        merged_rss = True


    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>产业情报简报</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" integrity="sha512-BNaRQnYJYiPSqHHDb58B0yaPfCu+Wgds8Gp/gU33kqBtgNS4tSPHuGibyoeqMV/TJlSKda6FXzoEyYGjTe+vXA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                margin: 0;
                padding: 16px;
                background: #eef3f8;
                color: #333;
                line-height: 1.5;
            }

            .container {
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 16px rgba(0,0,0,0.06);
            }

            .header {
                background: linear-gradient(135deg, #0c2340 0%, #14456b 55%, #2a6f97 100%);
                color: white;
                padding: 32px 24px;
                text-align: center;
                position: relative;
                overflow: visible;
            }

            .header-watermark {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: clamp(40px, 8vw, 80px);
                font-weight: 900;
                letter-spacing: 0.05em;
                color: rgba(255, 255, 255, 0.15);
                pointer-events: none;
                z-index: 1;
                white-space: nowrap;
                -webkit-mask-image: radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%);
                mask-image: radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%);
                transition: -webkit-mask-image 0.3s ease, mask-image 0.3s ease;
                user-select: none;
            }

            .save-buttons {
                position: absolute;
                top: 16px;
                right: 16px;
                display: none; /* 默认隐藏：邮件客户端不执行 JS，避免显示不可用按钮；浏览器由 JS 显示 */
                gap: 8px;
                z-index: 10;
            }

            .save-btn-group {
                position: relative;
                display: flex;
            }

            .save-btn {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 10px 18px;
                border-radius: 6px 0 0 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                transition: all 0.2s ease;
                backdrop-filter: blur(10px);
                white-space: nowrap;
                min-height: 38px;
                border-right: none;
            }

            .save-btn:hover {
                background: rgba(255, 255, 255, 0.3);
            }

            .save-btn:active {
                transform: translateY(0);
            }

            .save-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            .save-dropdown-trigger {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 10px 10px;
                border-radius: 0 6px 6px 0;
                cursor: pointer;
                font-size: 11px;
                transition: all 0.2s ease;
                backdrop-filter: blur(10px);
                min-height: 38px;
                display: flex;
                align-items: center;
            }

            .save-dropdown-trigger:hover {
                background: rgba(255, 255, 255, 0.35);
            }

            .save-dropdown-menu {
                position: absolute;
                top: 100%;
                right: 0;
                margin-top: 4px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 10px;
                padding: 4px;
                min-width: 140px;
                opacity: 0;
                visibility: hidden;
                transform: translateY(-4px);
                transition: all 0.2s ease;
                box-shadow: 0 8px 24px rgba(0,0,0,0.12);
            }

            .save-btn-group:hover .save-dropdown-menu,
            .save-dropdown-menu:hover {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }

            .save-dropdown-item {
                display: block;
                width: 100%;
                padding: 9px 14px;
                background: none;
                border: none;
                color: #374151;
                font-size: 13px;
                cursor: pointer;
                border-radius: 6px;
                text-align: left;
                transition: background 0.15s;
                white-space: nowrap;
            }

            .save-dropdown-item:hover {
                background: #f3f4f6;
                color: #2a6f97;
            }

            .dropdown-icon {
                width: 14px;
                height: 14px;
                margin-right: 8px;
                vertical-align: -2px;
                flex-shrink: 0;
            }

            .header-title {
                font-size: 22px;
                font-weight: 700;
                margin: 0 0 20px 0;
                position: relative;
                z-index: 2;
            }

            .header-info {
                position: relative;
                z-index: 2;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                font-size: 14px;
                opacity: 0.95;
            }

            .info-item {
                text-align: center;
            }

            .info-label {
                display: block;
                font-size: 12px;
                opacity: 0.8;
                margin-bottom: 4px;
            }

            .info-value {
                font-weight: 600;
                font-size: 16px;
            }

            .content {
                padding: 24px;
            }

            /* 读者视角页头 */
            .header-sub {
                position: relative;
                z-index: 2;
                font-size: 13px;
                opacity: 0.75;
                margin-top: -12px;
                margin-bottom: 14px;
            }
            .header-headline {
                position: relative;
                z-index: 2;
                font-size: 15.5px;
                line-height: 1.6;
                font-weight: 600;
                color: rgba(255,255,255,0.95);
                max-width: 640px;
                margin: 0 auto 14px auto;
            }
            .header-quickstats {
                position: relative;
                z-index: 2;
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 14px;
            }
            .hq-item {
                font-size: 12.5px;
                background: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.18);
                padding: 5px 12px;
                border-radius: 14px;
            }
            .hq-item b { font-weight: 700; }
            .header-legend {
                position: relative;
                z-index: 2;
                font-size: 11px;
                opacity: 0.6;
                line-height: 1.6;
                max-width: 620px;
                margin: 0 auto;
            }
            .header-legend b { font-weight: 700; }

            /* 运行统计（页面底部） */
            .run-stats { margin-top: 8px; }
            .run-stats-title {
                font-size: 12px;
                font-weight: 700;
                color: #93a8ba;
                letter-spacing: 0.08em;
                margin-bottom: 10px;
            }
            .run-stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
                gap: 8px 16px;
            }
            .run-stat {
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: #6b7280;
                padding: 4px 0;
                border-bottom: 1px dashed #e5eaf0;
            }
            .run-stat-label { color: #93a8ba; }
            .run-stat-value { font-weight: 600; }
            body.dark-mode .run-stat { color: #94a3b8; border-bottom-color: #24405a; }
            body.dark-mode .run-stat-label { color: #64798c; }

            .word-group {
                margin-bottom: 22px;
            }

            .word-group:first-child {
                margin-top: 0;
            }

            .word-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 8px;
                padding-bottom: 6px;
                border-bottom: 1px solid #f0f0f0;
            }

            .word-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .word-name {
                font-size: 15px;
                font-weight: 600;
                color: #1a1a1a;
            }

            .word-count {
                color: #666;
                font-size: 13px;
                font-weight: 500;
            }

            .word-count.hot { color: #16548f; font-weight: 700; }
            .word-count.warm { color: #4d8ec4; font-weight: 600; }

            .word-index {
                color: #999;
                font-size: 12px;
            }

            .news-item {
                margin-bottom: 0;
                padding: 8px 0;
                border-bottom: 1px solid #f5f5f5;
                position: relative;
                display: flex;
                gap: 10px;
                align-items: center;
            }

            .news-item:last-child {
                border-bottom: none;
            }

            .news-item.new::after {
                content: "NEW";
                position: absolute;
                top: 12px;
                right: 0;
                background: #cfe4f4;
                color: #16548f;
                font-size: 9px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 4px;
                letter-spacing: 0.5px;
            }

            .news-number {
                color: #999;
                font-size: 11px;
                font-weight: 600;
                min-width: 20px;
                text-align: center;
                flex-shrink: 0;
                background: #f8f9fa;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                align-self: flex-start;
                margin-top: 4px;
                position: relative;
                cursor: pointer;
                transition: background 0.15s, color 0.15s;
            }
            .news-number .num-text { transition: opacity 0.15s; }
            .news-number .copy-icon {
                position: absolute;
                opacity: 0;
                transition: opacity 0.15s;
            }
            .news-item:hover .news-number .num-text { opacity: 0; }
            .news-item:hover .news-number .copy-icon { opacity: 1; }
            .news-item:hover .news-number {
                background: #e9f2f9;
                color: #2a6f97;
            }
            .news-number.copied {
                background: #dfedf5 !important;
            }
            .news-number.copied .num-text { opacity: 0 !important; }
            .news-number.copied .copy-icon { opacity: 1 !important; }
            body.dark-mode .news-item:hover .news-number {
                background: #1b5886;
                color: #e0edf6;
            }
            body.dark-mode .news-number.copied {
                background: #22405a !important;
            }

            .news-content {
                flex: 1;
                min-width: 0;
                padding-right: 40px;
            }

            .news-item.new .news-content {
                padding-right: 50px;
            }

            .news-header {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 3px;
                flex-wrap: wrap;
            }

            .source-name {
                color: #666;
                font-size: 12px;
                font-weight: 500;
            }

            .keyword-tag {
                color: #1f6cab;
                font-size: 12px;
                font-weight: 500;
                background: #e8f1f8;
                padding: 2px 6px;
                border-radius: 4px;
            }

            .rank-num {
                color: #fff;
                background: #93a8ba;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 10px;
                min-width: 18px;
                text-align: center;
            }

            .rank-num.top { background: #16548f; }
            .rank-num.high { background: #4d8ec4; }

            .trend-up, .trend-down {
                font-size: 12px;
                margin-left: 2px;
                vertical-align: middle;
            }

            .time-info {
                color: #999;
                font-size: 11px;
            }

            .count-info {
                color: #2f7295;
                font-size: 11px;
                font-weight: 500;
            }

            .news-title {
                font-size: 14px;
                line-height: 1.45;
                color: #1a1a1a;
                margin: 0;
            }

            .news-link {
                color: #1f6cab;
                text-decoration: none;
            }

            .news-link:hover {
                text-decoration: underline;
            }

            .news-link:visited {
                color: #5a89ab;
            }

            /* 通用区域分割线样式 */
            .section-divider {
                margin-top: 32px;
                padding-top: 24px;
                border-top: 2px solid #e5e7eb;
            }

            /* ===== 分类分区（如 行业动态 / 公司监控） ===== */
            .category-banner {
                display: flex;
                align-items: center;
                gap: 12px;
                margin: 36px 0 24px 0;
                padding: 14px 18px;
                border-radius: 10px;
            }
            .category-banner:first-child { margin-top: 0; }
            .category-banner .category-icon {
                font-size: 22px;
                line-height: 1;
            }
            .category-banner-title {
                font-size: 17px;
                font-weight: 700;
                line-height: 1.3;
            }
            .category-banner-meta {
                font-size: 12px;
                opacity: 0.75;
                margin-top: 2px;
            }
            .category-style-0 {
                background: #e8f1f8;
                border-left: 4px solid #2a6f97;
            }
            .category-style-0 .category-banner-title { color: #174e7c; }
            .category-style-0 .category-banner-meta { color: #2a6f97; }
            .category-style-1 {
                background: #e6f3f6;
                border-left: 4px solid #1e7f9e;
            }
            .category-style-1 .category-banner-title { color: #6f5432; }
            .category-style-1 .category-banner-meta { color: #186a85; }
            .category-style-2 {
                background: #eef3ee;
                border-left: 4px solid #2f7295;
            }
            .category-style-2 .category-banner-title { color: #274d63; }
            .category-style-2 .category-banner-meta { color: #31708f; }

            body.dark-mode .category-style-0 {
                background: #101f2e;
                border-left-color: #7fb2d9;
            }
            body.dark-mode .category-style-0 .category-banner-title { color: #c4d9e9; }
            body.dark-mode .category-style-0 .category-banner-meta { color: #a4c6de; }
            body.dark-mode .category-style-1 {
                background: #0f2530;
                border-left-color: #4fa8c2;
            }
            body.dark-mode .category-style-1 .category-banner-title { color: #9cd0e0; }
            body.dark-mode .category-style-1 .category-banner-meta { color: #d9c49a; }
            body.dark-mode .category-style-2 {
                background: #122530;
                border-left-color: #66a4c4;
            }
            body.dark-mode .category-style-2 .category-banner-title { color: #b8d6e4; }
            body.dark-mode .category-style-2 .category-banner-meta { color: #8cc0d8; }

            /* 零命中词组提示 */
            .empty-groups {
                grid-column: 1 / -1;
                margin-top: 20px;
                padding: 12px 16px;
                background: #f8f9fa;
                border-radius: 8px;
                font-size: 12px;
                color: #9ca3af;
                line-height: 1.8;
            }
            .empty-groups-label { font-weight: 600; color: #6b7280; }
            .empty-groups-cat {
                font-weight: 600;
                color: #6b7280;
                margin-right: 4px;
            }
            .empty-groups-sep { margin: 0 8px; color: #d1d5db; }
            body.dark-mode .empty-groups { background: #0f172a; color: #64748b; }
            body.dark-mode .empty-groups-label,
            body.dark-mode .empty-groups-cat { color: #94a3b8; }

            /* RSS 区内的分类标签（宽屏 grid 下占满整行） */
            .rss-category-label {
                grid-column: 1 / -1;
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 8px 0 4px 0;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }
            .rss-category-label .category-icon { font-size: 16px; }
            .rss-category-label .rss-category-count {
                font-size: 12px;
                font-weight: 500;
                opacity: 0.75;
            }

            /* 热榜统计区样式 */
            .hotlist-section {
                /* 默认无边框，由 section-divider 动态添加 */
            }

            .new-section {
                margin-top: 40px;
                padding-top: 24px;
            }

            .new-section-title {
                color: #1a1a1a;
                font-size: 16px;
                font-weight: 600;
                margin: 0 0 20px 0;
            }

            .new-source-group {
                margin-bottom: 24px;
            }

            .new-source-title {
                color: #666;
                font-size: 13px;
                font-weight: 500;
                margin: 0 0 12px 0;
                padding-bottom: 6px;
                border-bottom: 1px solid #f5f5f5;
            }

            .new-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 8px 0;
                border-bottom: 1px solid #f9f9f9;
            }

            .new-item:last-child {
                border-bottom: none;
            }

            .new-item-number {
                color: #999;
                font-size: 12px;
                font-weight: 600;
                min-width: 18px;
                text-align: center;
                flex-shrink: 0;
                background: #f8f9fa;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .new-item-rank {
                color: #fff;
                background: #93a8ba;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 8px;
                min-width: 20px;
                text-align: center;
                flex-shrink: 0;
            }

            .new-item-rank.top { background: #16548f; }
            .new-item-rank.high { background: #4d8ec4; }

            .new-item-content {
                flex: 1;
                min-width: 0;
            }

            .new-item-title {
                font-size: 14px;
                line-height: 1.4;
                color: #1a1a1a;
                margin: 0;
            }

            .error-section {
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 24px;
            }

            .error-title {
                color: #a3564a;
                font-size: 14px;
                font-weight: 600;
                margin: 0 0 8px 0;
            }

            .error-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }

            .error-item {
                color: #991b1b;
                font-size: 13px;
                padding: 2px 0;
                font-family: 'SF Mono', Consolas, monospace;
            }

            .footer {
                margin-top: 32px;
                padding: 20px 24px;
                background: #f8f9fa;
                border-top: 1px solid #e5e7eb;
                text-align: center;
            }

            .footer-content {
                font-size: 13px;
                color: #6b7280;
                line-height: 1.6;
            }

            .footer-link {
                color: #2a6f97;
                text-decoration: none;
                font-weight: 500;
                transition: color 0.2s ease;
            }

            .footer-link:hover {
                color: #5a89ab;
                text-decoration: underline;
            }

            .project-name {
                font-weight: 600;
                color: #374151;
            }

            @media (max-width: 480px) {
                body { padding: 12px; }
                .header { padding: 24px 20px; }
                .content { padding: 20px; }
                .footer { padding: 16px 20px; }
                .header-info { grid-template-columns: 1fr; gap: 12px; }
                .news-header { gap: 6px; }
                .news-content { padding-right: 45px; }
                .news-item { gap: 8px; }
                .new-item { gap: 8px; }
                .news-number { width: 20px; height: 20px; font-size: 12px; }
                .save-buttons {
                    position: static;
                    margin-bottom: 16px;
                    gap: 8px;
                    justify-content: center;
                    width: 100%;
                }
                .save-btn-group {
                    flex: 1;
                }
                .save-btn {
                    width: 100%;
                    border-radius: 6px 0 0 6px;
                }
            }

            /* RSS 订阅内容样式 */
            .rss-section {
                margin-top: 32px;
                padding-top: 24px;
            }

            .rss-section-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
            }

            .rss-section-title {
                font-size: 18px;
                font-weight: 600;
                color: #2f7295;
            }

            .rss-section-count {
                color: #6b7280;
                font-size: 14px;
            }

            .feed-group {
                margin-bottom: 24px;
            }

            .feed-group:last-child {
                margin-bottom: 0;
            }

            .feed-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 2px solid #6fa3c0;
            }

            .feed-name {
                font-size: 15px;
                font-weight: 600;
                color: #2f7295;
            }

            .feed-count {
                color: #666;
                font-size: 13px;
                font-weight: 500;
            }

            .rss-item {
                margin-bottom: 12px;
                padding: 14px;
                background: #f0f6fa;
                border-radius: 8px;
                border-left: 3px solid #6fa3c0;
            }

            .rss-item:last-child {
                margin-bottom: 0;
            }

            .rss-meta {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 6px;
                flex-wrap: wrap;
            }

            .rss-time {
                color: #6b7280;
                font-size: 12px;
            }

            .rss-author {
                color: #2f7295;
                font-size: 12px;
                font-weight: 500;
            }

            .rss-title {
                font-size: 14px;
                line-height: 1.5;
                margin-bottom: 6px;
            }

            .rss-link {
                color: #1f2937;
                text-decoration: none;
                font-weight: 500;
            }

            .rss-link:hover {
                color: #2f7295;
                text-decoration: underline;
            }

            .rss-summary {
                font-size: 12.5px;
                color: #6b7280;
                line-height: 1.55;
                margin: 3px 0 0 0;
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
                cursor: pointer;
            }
            .rss-summary.expanded {
                display: block;
                -webkit-line-clamp: unset;
            }
            .rss-summary:hover { color: #374151; }
            body.dark-mode .rss-summary:hover { color: #cbd5e1; }

            /* 独立展示区样式 - 复用热点词汇统计区样式 */
            .standalone-section {
                margin-top: 32px;
                padding-top: 24px;
            }

            .standalone-section-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
            }

            .standalone-section-title {
                font-size: 18px;
                font-weight: 600;
                color: #2f7295;
            }

            .standalone-section-count {
                color: #6b7280;
                font-size: 14px;
            }

            .standalone-group {
                margin-bottom: 40px;
            }

            .standalone-group:last-child {
                margin-bottom: 0;
            }

            .standalone-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
                padding-bottom: 8px;
                border-bottom: 1px solid #f0f0f0;
            }

            .standalone-name {
                font-size: 17px;
                font-weight: 600;
                color: #1a1a1a;
            }

            .standalone-count {
                color: #666;
                font-size: 13px;
                font-weight: 500;
            }

            /* AI 分析区块样式 */
            .ai-section {
                margin-top: 32px;
                padding: 24px;
                background: #f2f7fb;
                border-radius: 12px;
                border: 1px solid #cfe0eb;
            }

            .ai-section-header {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }

            .ai-section-title {
                font-size: 18px;
                font-weight: 600;
                color: #174e7c;
            }

            .ai-section-badge {
                background: #3f7ba6;
                color: white;
                font-size: 11px;
                font-weight: 600;
                padding: 3px 8px;
                border-radius: 4px;
            }

            .ai-block {
                margin-bottom: 16px;
                padding: 16px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }

            .ai-block:last-child {
                margin-bottom: 0;
            }

            .ai-block-title {
                font-size: 14px;
                font-weight: 600;
                color: #174e7c;
                margin-bottom: 8px;
            }

            .ai-block-content {
                font-size: 14px;
                line-height: 1.6;
                color: #334155;
                white-space: pre-wrap;
            }

            .ai-error {
                padding: 16px;
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                color: #991b1b;
                font-size: 14px;
            }

            .ai-warning {
                padding: 16px;
                background: #edf6f8;
                border: 1px solid #9cd0e0;
                border-radius: 8px;
                color: #6f5432;
                font-size: 14px;
            }

            .ai-info {
                padding: 16px;
                background: #eff5fa;
                border: 1px solid #cfe0eb;
                border-radius: 8px;
                color: #174e7c;
                font-size: 14px;
            }

            /* ===== 浏览器增强样式（渐进增强，邮件客户端无影响） ===== */

            /* 宽屏模式 - 基础 */
            body.wide-mode .container { max-width: 1200px; }
            body.wide-mode .header-info { grid-template-columns: repeat(4, 1fr); }
            body.wide-mode .content { padding: 32px 40px; }

            /* ===== 信息分区（zone）：不同颜色区分不同信息区域 ===== */
            .zone {
                margin-bottom: 26px;
                border-radius: 12px;
                padding: 18px;
                border: 1px solid transparent;
            }
            .zone:last-child { margin-bottom: 0; }
            .zone-header {
                display: flex;
                align-items: baseline;
                gap: 10px;
                margin-bottom: 12px;
                padding-bottom: 10px;
                border-bottom: 2px solid rgba(0,0,0,0.05);
            }
            .zone-icon { font-size: 18px; }
            .zone-title { font-size: 18px; font-weight: 700; }
            .zone-meta { font-size: 12px; opacity: 0.65; margin-left: auto; }

            /* 公司监控区：深海蓝调 */
            .zone-company {
                background: linear-gradient(180deg, #eaf2f9 0%, #f4f8fc 120px, #f9fbfd 100%);
                border-color: #d3e2ef;
            }
            .zone-company .zone-title { color: #14456b; }
            .zone-company .zone-meta { color: #2a6f97; }
            /* 行业动态区：青蓝调 */
            .zone-industry {
                background: linear-gradient(180deg, #e8f4f7 0%, #f2f9fb 120px, #f9fcfd 100%);
                border-color: #cfe6ed;
            }
            .zone-industry .zone-title { color: #125a72; }
            .zone-industry .zone-meta { color: #1e7f9e; }

            body.dark-mode .zone-company {
                background: linear-gradient(180deg, #13273a 0%, #101f2e 140px);
                border-color: #24405a;
            }
            body.dark-mode .zone-company .zone-title { color: #a4c6de; }
            body.dark-mode .zone-industry {
                background: linear-gradient(180deg, #0f2b33 0%, #0e1f29 140px);
                border-color: #1e4552;
            }
            body.dark-mode .zone-industry .zone-title { color: #9cd0e0; }
            body.dark-mode .zone-header { border-bottom-color: rgba(255,255,255,0.07); }

            /* ── 公司监控：名单目录 + 资讯流 ── */
            .company-layout { display: flex; flex-direction: column; gap: 16px; }
            body.wide-mode .company-layout {
                display: grid;
                grid-template-columns: 200px minmax(0, 1fr);
                gap: 24px;
                align-items: start;
            }
            .company-directory {
                background: rgba(255,255,255,0.75);
                border: 1px solid #d3e2ef;
                border-radius: 10px;
                padding: 12px;
            }
            body.wide-mode .company-directory {
                position: sticky;
                top: 16px;
                max-height: calc(100vh - 32px);
                overflow-y: auto;
            }
            .dir-title {
                font-size: 12px;
                font-weight: 700;
                color: #2a6f97;
                letter-spacing: 0.08em;
                margin-bottom: 8px;
            }
            .dir-list { display: flex; flex-direction: column; gap: 2px; }
            /* 窄屏：目录横向流式排列 */
            body:not(.wide-mode) .dir-list { flex-direction: row; flex-wrap: wrap; gap: 6px; }
            .dir-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
                font-size: 13px;
                color: #14456b;
                font-weight: 600;
                text-decoration: none;
                padding: 5px 8px;
                border-radius: 6px;
                transition: background 0.15s;
            }
            .dir-item:hover { background: #e0edf6; }
            .dir-count {
                background: #2a6f97;
                color: #fff;
                font-size: 11px;
                font-weight: 700;
                min-width: 18px;
                text-align: center;
                padding: 1px 6px;
                border-radius: 9px;
            }
            .dir-item.dir-muted {
                color: #a9b8c4;
                font-weight: 400;
                cursor: default;
            }
            .dir-item.dir-muted:hover { background: none; }
            .dir-note {
                margin-top: 10px;
                padding-top: 10px;
                border-top: 1px dashed #d3e2ef;
                font-size: 11px;
                color: #93a8ba;
                line-height: 1.6;
            }
            .company-feed { min-width: 0; }
            .company-feed .word-group { scroll-margin-top: 16px; }
            .zone-empty-feed {
                padding: 32px;
                text-align: center;
                color: #93a8ba;
                font-size: 13px;
            }
            body.dark-mode .company-directory { background: rgba(15,31,46,0.6); border-color: #24405a; }
            body.dark-mode .dir-item { color: #a4c6de; }
            body.dark-mode .dir-item:hover { background: #1b3550; }
            body.dark-mode .dir-item.dir-muted { color: #4d6275; }
            body.dark-mode .dir-note { color: #64798c; border-top-color: #24405a; }

            /* ── 行业动态：子行业页签 ── */
            .ind-tabbar {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-bottom: 16px;
            }
            .ind-tab {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 14px;
                border: 1px solid #cfe6ed;
                background: rgba(255,255,255,0.8);
                color: #31708f;
                border-radius: 16px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                transition: all 0.18s;
            }
            .ind-tab:hover { border-color: #1e7f9e; color: #125a72; }
            .ind-tab.active { background: #1e7f9e; border-color: #1e7f9e; color: #fff; }
            .ind-tab .tab-count {
                font-size: 11px;
                background: rgba(0,0,0,0.08);
                padding: 1px 6px;
                border-radius: 10px;
            }
            .ind-tab.active .tab-count { background: rgba(255,255,255,0.25); }
            .zone-empty {
                margin-top: 12px;
                font-size: 12px;
                color: #93a8ba;
            }
            body.dark-mode .ind-tab { background: rgba(15,31,46,0.6); border-color: #1e4552; color: #8cc0d8; }
            body.dark-mode .ind-tab.active { background: #1e7f9e; color: #fff; }

            /* 行业区公司聚类（AI 总结 + 引用角标） */
            .cluster {
                padding: 8px 0;
                border-bottom: 1px solid #f0f0f0;
            }
            .cluster:last-child { border-bottom: none; }
            .cluster-hd {
                font-size: 13.5px;
                font-weight: 700;
                color: #174e7c;
                margin-bottom: 3px;
            }
            .cluster-cnt {
                font-weight: 400;
                font-size: 11px;
                color: #93a8ba;
                margin-left: 6px;
            }
            .cluster-sum {
                font-size: 13px;
                line-height: 1.6;
                color: #3c4650;
            }
            .cluster-region {
                font-size: 10px;
                font-weight: 600;
                color: #4d8ec4;
                background: #e8f1f8;
                padding: 1px 6px;
                border-radius: 4px;
                margin-left: 6px;
                vertical-align: 1px;
            }
            body.dark-mode .cluster-region { background: #1b3550; color: #8fbcdb; }

            .market-block {
                margin-top: 16px;
                padding: 12px 14px;
                background: rgba(255,255,255,0.55);
                border: 1px dashed #b9cede;
                border-radius: 10px;
            }
            .market-hd {
                font-size: 13px;
                font-weight: 700;
                color: #5b7a94;
                margin-bottom: 4px;
            }
            .market-cnt {
                font-weight: 400;
                font-size: 11px;
                color: #93a8ba;
                margin-left: 6px;
            }
            body.dark-mode .market-block { background: rgba(15,31,46,0.5); border-color: #2b4a63; }
            body.dark-mode .market-hd { color: #8aa8c0; }

            details.more-items { margin-top: 8px; }
            details.more-items summary {
                cursor: pointer;
                font-size: 12px;
                color: #6b8aa5;
                padding: 4px 0;
                user-select: none;
            }
            details.more-items summary:hover { color: #174e7c; }
            body.dark-mode details.more-items summary { color: #64798c; }

            .cluster-rest-label {
                margin-top: 10px;
                font-size: 11px;
                font-weight: 700;
                color: #93a8ba;
                letter-spacing: 0.05em;
            }
            .cites { margin-left: 4px; white-space: nowrap; }
            .cite {
                font-size: 11px;
                font-weight: 600;
                color: #1f6cab;
                text-decoration: none;
                margin-right: 2px;
                cursor: pointer;
            }
            .cite:hover { color: #16548f; text-decoration: underline; }
            body.dark-mode .cluster { border-bottom-color: #24405a; }
            body.dark-mode .cluster-hd { color: #a4c6de; }
            body.dark-mode .cluster-sum { color: #cbd5e1; }
            body.dark-mode .cite { color: #8fbcdb; }

            /* RSS 来源徽标（RSS 条目并入分区后的标识） */
            .rss-chip {
                font-size: 10px;
                font-weight: 700;
                color: #1e7f9e;
                background: #d7ebf1;
                padding: 1px 6px;
                border-radius: 4px;
                letter-spacing: 0.05em;
            }
            body.dark-mode .rss-chip { background: #0f2b33; color: #8cc0d8; }

            /* AI 分析：主栏（核心研判）+ 侧栏（值得跟踪的线索） */
            .ai-layout { display: flex; flex-direction: column; gap: 16px; }
            body.wide-mode .ai-layout {
                display: grid;
                grid-template-columns: minmax(0, 5fr) minmax(0, 3fr);
                gap: 16px;
                align-items: start;
            }
            .ai-main { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
            .ai-side { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
            body.wide-mode .ai-side { position: sticky; top: 16px; }
            .ai-main .ai-block, .ai-side .ai-block { margin-bottom: 0; }
            .ai-block-core .ai-block-content { font-size: 14.5px; line-height: 1.7; }
            .ai-side .ai-block {
                border-left: 3px solid #2a6f97;
                background: #eff5fa;
            }
            body.dark-mode .ai-side .ai-block { background: #13273a; border-left-color: #7fb2d9; }

            /* 宽屏模式 - RSS feed-group 两列 */
            body.wide-mode .rss-feeds-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 24px;
            }
            body.wide-mode .feed-group { margin-bottom: 0; }

            /* 宽屏模式 - AI 分析区两列网格 */
            body.wide-mode .ai-section .ai-blocks-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }
            body.wide-mode .ai-block { margin-bottom: 0; }

            /* 宽屏模式 - 新增热点多列 */
            body.wide-mode .new-section .new-sources-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 24px;
            }
            body.wide-mode .new-source-group { margin-bottom: 0; }

            /* 宽屏模式 - 独立展示区多列 */
            body.wide-mode .standalone-section .standalone-groups-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 24px;
            }
            body.wide-mode .standalone-group { margin-bottom: 0; }

            /* Tab 栏 */
            .tab-bar-wrapper {
                position: sticky;
                top: 0;
                z-index: 10;
                background: white;
                display: none;
                margin-bottom: 20px;
                align-items: stretch;
                border-bottom: 2px solid #e5e7eb;
            }
            body.wide-mode .tab-bar-wrapper { display: flex; }
            body.wide-mode .tab-bar-wrapper.tab-hidden { display: none; }

            .tab-bar {
                flex: 1;
                min-width: 0;
                display: flex;
                overflow-x: auto;
                white-space: nowrap;
                padding: 8px 0 12px 0;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
                -ms-overflow-style: none;
                gap: 4px;
                mask-image: linear-gradient(to right, transparent, black 24px, black calc(100% - 24px), transparent);
                -webkit-mask-image: linear-gradient(to right, transparent, black 24px, black calc(100% - 24px), transparent);
            }
            .tab-bar::-webkit-scrollbar { display: none; }
            .tab-bar.scroll-start {
                mask-image: linear-gradient(to right, black, black calc(100% - 24px), transparent);
                -webkit-mask-image: linear-gradient(to right, black, black calc(100% - 24px), transparent);
            }
            .tab-bar.scroll-end {
                mask-image: linear-gradient(to right, transparent, black 24px, black);
                -webkit-mask-image: linear-gradient(to right, transparent, black 24px, black);
            }
            .tab-bar.scroll-start.scroll-end,
            .tab-bar.no-overflow {
                mask-image: none;
                -webkit-mask-image: none;
            }

            .tab-arrow {
                flex-shrink: 0;
                width: 28px;
                display: none;
                align-items: center;
                justify-content: center;
                background: none;
                border: none;
                color: #9ca3af;
                font-size: 20px;
                font-weight: 300;
                cursor: pointer;
                padding: 0;
                transition: color 0.15s ease;
            }
            .tab-arrow:hover { color: #2a6f97; }
            .tab-arrow.visible { display: flex; }

            .tab-scroll-indicator {
                position: absolute;
                bottom: 0;
                left: 0;
                width: 0;
                height: 2px;
                background: #2a6f97;
                border-radius: 0 1px 1px 0;
                transition: width 0.1s linear;
            }

            .tab-btn {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 8px 16px;
                border: none;
                background: #f3f4f6;
                color: #6b7280;
                border-radius: 8px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                white-space: nowrap;
                transition: all 0.2s ease;
                flex-shrink: 0;
            }
            .tab-btn:hover { background: #e5e7eb; color: #374151; }
            .tab-btn.active { background: #2a6f97; color: white; }
            .tab-count {
                font-size: 11px;
                background: rgba(0,0,0,0.1);
                padding: 1px 6px;
                border-radius: 10px;
            }
            .tab-btn.active .tab-count { background: rgba(255,255,255,0.3); }

            /* 搜索栏 */
            /* 历史报告导航 */
            .history-nav {
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
                padding: 0 0 14px 0;
            }
            .history-nav-label {
                font-size: 12px;
                color: #9ca3af;
                margin-right: 4px;
            }
            .history-chip {
                font-size: 12px;
                color: #6b7280;
                background: #e7eef5;
                padding: 4px 10px;
                border-radius: 12px;
                text-decoration: none;
                transition: all 0.15s;
            }
            .history-chip:hover { background: #e5e9ed; color: #174e7c; }
            .history-chip.active {
                background: #2a6f97;
                color: #fff;
                pointer-events: none;
            }
            body.dark-mode .history-chip { background: #334155; color: #94a3b8; }
            body.dark-mode .history-chip:hover { background: #1b5886; color: #e2e8f0; }
            body.dark-mode .history-chip.active { background: #2a6f97; color: #fff; }

            .search-bar { display: none; padding: 0 0 16px 0; }
            .search-input {
                width: 100%;
                padding: 10px 16px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                font-size: 14px;
                outline: none;
                transition: border-color 0.2s;
                box-sizing: border-box;
            }
            .search-input:focus { border-color: #2a6f97; box-shadow: 0 0 0 3px rgba(42,111,151,0.15); }
            .search-input::placeholder { color: #9ca3af; }

            /* 右下角悬浮工具栏 */
            .fab-bar {
                position: fixed;
                bottom: 24px;
                right: 24px;
                display: flex;
                flex-direction: column;
                gap: 8px;
                z-index: 100;
                opacity: 0;
                transform: translateY(10px);
                transition: opacity 0.3s, transform 0.3s;
                pointer-events: none;
            }
            .fab-bar.visible {
                opacity: 1;
                transform: translateY(0);
                pointer-events: auto;
            }
            .fab-btn {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: #2a6f97;
                color: white;
                border: none;
                cursor: pointer;
                font-size: 16px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                transition: transform 0.2s, background 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }
            .fab-btn:hover { transform: scale(1.1); background: #1b5886; }
            body.dark-mode .fab-btn { background: #1d4e79; }
            body.dark-mode .fab-btn:hover { background: #2f6690; }

            /* 快捷键 tooltip */
            .fab-tooltip {
                position: absolute;
                bottom: 0;
                right: 52px;
                background: rgba(30, 30, 50, 0.92);
                backdrop-filter: blur(12px);
                color: white;
                border-radius: 10px;
                padding: 12px 16px;
                white-space: nowrap;
                font-size: 12px;
                line-height: 1.8;
                box-shadow: 0 8px 24px rgba(0,0,0,0.25);
                border: 1px solid rgba(255,255,255,0.1);
                opacity: 0;
                visibility: hidden;
                transform: translateY(6px);
                transition: all 0.2s ease;
                pointer-events: none;
            }
            .fab-btn:hover .fab-tooltip,
            .fab-btn.show-tip .fab-tooltip {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
                pointer-events: auto;
            }
            .fab-tooltip .tip-row {
                display: flex;
                justify-content: space-between;
                gap: 16px;
                align-items: center;
            }
            .fab-tooltip .tip-key {
                background: rgba(255,255,255,0.15);
                border-radius: 3px;
                padding: 1px 6px;
                font-family: monospace;
                font-size: 11px;
                margin-left: 8px;
            }

            /* 折叠/展开 */
            .collapse-icon {
                display: none;
                margin-right: 6px;
                font-size: 12px;
                color: #9ca3af;
                transition: transform 0.2s;
                user-select: none;
            }
            .word-header.collapsible { cursor: pointer; }
            .word-header.collapsible .collapse-icon { display: inline; }
            .word-header.collapsible:hover {
                background: #f9fafb;
                border-radius: 6px;
                margin: 0 -8px 20px -8px;
                padding: 8px;
            }
            .word-group.collapsed .news-item { display: none; }
            .word-group.collapsed .collapse-icon { transform: rotate(-90deg); }

            /* Tab 切换动画 */
            body.wide-mode .word-group[data-tab-index] { animation: tabFadeIn 0.2s ease; }
            @keyframes tabFadeIn {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* 宽屏切换按钮 */
            .toggle-wide-btn {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 10px 14px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 15px;
                transition: all 0.2s ease;
                backdrop-filter: blur(10px);
                line-height: 1;
                min-height: 38px;
            }
            .toggle-wide-btn:hover {
                background: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
                transform: translateY(-1px);
            }

            /* ===== 暗色模式 ===== */
            body.dark-mode {
                background: #0f172a;
                color: #e2e8f0;
            }
            body.dark-mode .container {
                background: #1e293b;
                box-shadow: 0 4px 24px rgba(0,0,0,0.4);
            }
            body.dark-mode .header {
                background: linear-gradient(135deg, #0a1c33 0%, #123a5c 100%);
            }
            body.dark-mode .content {
                background: #1e293b;
            }

            /* 文字颜色 */
            body.dark-mode .word-name,
            body.dark-mode .new-section-title,
            body.dark-mode .standalone-name,
            body.dark-mode .new-item-title,
            body.dark-mode .project-name { color: #f1f5f9; }
            body.dark-mode .word-count,
            body.dark-mode .word-index,
            body.dark-mode .source-name,
            body.dark-mode .time-info,
            body.dark-mode .feed-count,
            body.dark-mode .new-source-title,
            body.dark-mode .standalone-count,
            body.dark-mode .rss-section-count,
            body.dark-mode .standalone-section-count,
            body.dark-mode .news-meta,
            body.dark-mode .rss-time,
            body.dark-mode .rss-author,
            body.dark-mode .rss-summary { color: #94a3b8; }
            body.dark-mode .info-value { color: white; }

            /* 链接 */
            body.dark-mode .news-title a,
            body.dark-mode .rss-title a,
            body.dark-mode .new-item a,
            body.dark-mode .standalone-item a,
            body.dark-mode .rss-link { color: #8fbcdb; }
            body.dark-mode .news-title a:visited { color: #b3cde0; }
            body.dark-mode .rss-link:hover { color: #8cc0d8; }

            /* 强调色 */
            body.dark-mode .keyword-tag {
                background: rgba(99,102,241,0.15);
                color: #a4c6de;
            }
            body.dark-mode .count-info { color: #8cc0d8; }
            body.dark-mode .rss-source,
            body.dark-mode .feed-name,
            body.dark-mode .rss-section-title,
            body.dark-mode .standalone-section-title { color: #8cc0d8; }

            /* 边框与分割线 */
            body.dark-mode .word-header,
            body.dark-mode .news-item,
            body.dark-mode .new-item,
            body.dark-mode .standalone-item,
            body.dark-mode .new-source-title,
            body.dark-mode .standalone-header { border-bottom-color: #334155; }
            body.dark-mode .section-divider { border-top-color: #334155; }
            body.dark-mode .feed-header { border-bottom-color: #22405a; }
            body.dark-mode .tab-bar { border-bottom-color: #334155; }

            /* 序号圆圈 */
            body.dark-mode .news-number,
            body.dark-mode .new-item-number {
                background: #334155;
                color: #94a3b8;
            }

            /* 折叠 hover */
            body.dark-mode .word-header.collapsible:hover { background: #253347; }

            /* Tab 栏 */
            body.dark-mode .tab-bar-wrapper {
                background: #1e293b;
                border-bottom-color: #334155;
            }
            body.dark-mode .tab-arrow { color: #64748b; }
            body.dark-mode .tab-arrow:hover { color: #b3cde0; }
            body.dark-mode .tab-scroll-indicator { background: #7fb2d9; }
            body.dark-mode .tab-btn {
                background: #334155;
                color: #94a3b8;
            }
            body.dark-mode .tab-btn:hover {
                background: #475569;
                color: #e2e8f0;
            }
            body.dark-mode .tab-btn.active {
                background: #2f6690;
                color: white;
            }
            body.dark-mode .tab-bar::-webkit-scrollbar-track { background: #1e293b; }
            body.dark-mode .tab-bar::-webkit-scrollbar-thumb { background: #475569; }

            /* 搜索框 */
            body.dark-mode .search-input {
                background: #1e293b;
                border-color: #334155;
                color: #e2e8f0;
            }
            body.dark-mode .search-input:focus {
                border-color: #7fb2d9;
                box-shadow: 0 0 0 3px rgba(127,178,217,0.18);
            }
            body.dark-mode .search-input::placeholder { color: #64748b; }

            /* RSS 卡片 */
            body.dark-mode .rss-item {
                background: #1a2e25;
                border-left-color: #2f7295;
            }

            /* AI 分析区 */
            body.dark-mode .ai-section {
                background: #101f2e;
                border-color: #334155;
            }
            body.dark-mode .ai-section-title { color: #a4c6de; }
            body.dark-mode .ai-section-badge { background: #2a6f97; }
            body.dark-mode .ai-block {
                background: #1e293b;
                border-color: #334155;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            }
            body.dark-mode .ai-block-title { color: #a4c6de; }
            body.dark-mode .ai-block-content { color: #cbd5e1; }
            body.dark-mode .ai-warning {
                background: #422006;
                border-color: #854d0e;
                color: #d9c49a;
            }
            body.dark-mode .ai-error {
                background: #450a0a;
                border-color: #991b1b;
                color: #fca5a5;
            }
            body.dark-mode .ai-info {
                background: #172554;
                border-color: #1e40af;
                color: #8fbcdb;
            }

            /* 错误区 */
            body.dark-mode .error-section {
                background: #1c1917;
                border-color: #78350f;
            }
            body.dark-mode .error-title { color: #fca5a5; }
            body.dark-mode .error-item { color: #f87171; }

            /* Footer */
            body.dark-mode .footer {
                background: #0f172a;
                border-top-color: #334155;
                color: #94a3b8;
            }
            body.dark-mode .footer-link { color: #8fbcdb; }
            body.dark-mode .footer-link:hover { color: #b3cde0; }

            /* 悬浮按钮 */
            body.dark-mode .fab-btn { background: #2f6690; }
            body.dark-mode .fab-btn:hover { background: #5a89ab; }

            /* 下拉菜单 */
            body.dark-mode .save-dropdown-menu {
                background: rgba(30,41,59,0.95);
                border-color: #475569;
                box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            }
            body.dark-mode .save-dropdown-item {
                color: #e2e8f0;
            }
            body.dark-mode .save-dropdown-item:hover {
                background: #334155;
                color: #b3cde0;
            }

            /* 暗色模式切换按钮 */
            .toggle-dark-btn {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 10px 14px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 15px;
                transition: all 0.2s ease;
                backdrop-filter: blur(10px);
                line-height: 1;
                min-height: 38px;
            }
            .toggle-dark-btn:hover {
                background: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
                transform: translateY(-1px);
            }

            /* 快捷键面板已集成到 fab-tooltip */

            /* 阅读进度条 */
            .reading-progress {
                position: fixed;
                top: 0; left: 0;
                width: 0;
                height: 3px;
                background: #2a6f97;
                z-index: 9999;
                transition: width 0.1s linear;
            }
            body.dark-mode .reading-progress {
                background: #7fb2d9;
            }

            /* 复制按钮样式已集成到 .news-number */



            /* 新上榜标记 */
            .badge-new {
                display: inline-block;
                background: #3f7fae;
                color: white;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 6px;
                border-radius: 3px;
                margin-left: 6px;
                vertical-align: middle;
                letter-spacing: 0.5px;
            }
            body.dark-mode .badge-new {
                background: #2c5876;
            }

            /* ═══════════ v2 卡片化设计（参照复盘笔记风格，保留科技蓝配色）═══════════ */
            body {
                background: #f2f4f7;
                padding: 20px 16px;
            }
            .container {
                background: transparent;
                box-shadow: none;
                border-radius: 0;
                overflow: visible;
            }
            body.wide-mode .container { max-width: 1240px; }

            /* 页头：白色标题卡 */
            .header {
                background: #ffffff;
                border: 1px solid #e3e9f0;
                border-radius: 14px;
                padding: 20px 24px;
                text-align: left;
                color: #1a2b3c;
                margin-bottom: 14px;
            }
            .header-watermark { display: none; }
            .header-title {
                font-size: 20px;
                font-weight: 700;
                color: #1a2b3c;
                margin: 0 0 4px 0;
            }
            .header-sub {
                font-size: 12.5px;
                color: #8494a6;
                opacity: 1;
                margin: 0;
            }
            .save-buttons { top: 18px; right: 18px; }
            .save-btn, .toggle-wide-btn, .toggle-dark-btn, .save-dropdown-trigger {
                background: #ffffff;
                border: 1px solid #d7e0e9;
                color: #33506b;
                backdrop-filter: none;
            }
            .save-btn:hover, .toggle-wide-btn:hover, .toggle-dark-btn:hover,
            .save-dropdown-trigger:hover {
                background: #f2f7fb;
                border-color: #2a6f97;
                color: #14456b;
                transform: none;
            }

            /* 内容区：透明画布，卡片自管间距 */
            .content { padding: 0; }
            body.wide-mode .content { padding: 0; }
            .section-divider {
                border-top: none;
                padding-top: 0;
                margin-top: 0;
            }
            .ai-section, .run-stats { margin-bottom: 14px; }

            /* 研判横幅卡 */
            .headline-card {
                background: #e9f2f9;
                border: 1px solid #cfe2ef;
                border-radius: 14px;
                padding: 14px 20px;
                font-size: 15px;
                font-weight: 600;
                line-height: 1.65;
                color: #14456b;
                margin-bottom: 14px;
            }

            /* 大数字指标卡 */
            .metric-row {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                margin-bottom: 10px;
            }
            .metric-card {
                flex: 1;
                min-width: 130px;
                background: #ffffff;
                border: 1px solid #e3e9f0;
                border-radius: 14px;
                padding: 14px 18px;
            }
            .metric-label {
                font-size: 11.5px;
                color: #8494a6;
                margin-bottom: 6px;
                letter-spacing: 0.03em;
            }
            .metric-value {
                font-size: 26px;
                font-weight: 700;
                color: #1a2b3c;
                line-height: 1;
            }
            .metric-unit {
                font-size: 12px;
                font-weight: 400;
                color: #8494a6;
                margin-left: 5px;
            }
            .legend-line {
                font-size: 11px;
                color: #93a3b4;
                line-height: 1.7;
                margin: 2px 4px 16px 4px;
            }
            .legend-line b { color: #5b7a94; }

            /* 历史导航与搜索 */
            .history-nav { padding: 0 2px 12px 2px; }
            .search-input {
                border: 1px solid #e3e9f0;
                border-radius: 12px;
                background: #ffffff;
            }

            /* 分区：白色卡片 + "｜标题" 竖条强调 */
            .zone,
            .zone-company,
            .zone-industry {
                background: #ffffff;
                border: 1px solid #e3e9f0;
                border-radius: 14px;
                padding: 20px 22px;
                margin-bottom: 14px;
            }
            .zone-header { border-bottom: 1px solid #edf1f5; }
            .zone-icon { display: none; }
            .zone-title::before {
                content: "";
                display: inline-block;
                width: 4px;
                height: 16px;
                border-radius: 2px;
                margin-right: 9px;
                vertical-align: -2px;
                background: #2a6f97;
            }
            .zone-industry .zone-title::before { background: #1e7f9e; }
            .zone-company .zone-title::before { background: #2a6f97; }
            .zone-industry .zone-title, .zone-company .zone-title { color: #1a2b3c; }

            /* AI 区：白卡 + 竖条标题；侧栏改深海军蓝摘要卡 */
            .ai-section {
                background: #ffffff;
                border: 1px solid #e3e9f0;
                border-radius: 14px;
                padding: 20px 22px;
            }
            .ai-section-title { color: #1a2b3c; }
            .ai-section-title::before {
                content: "";
                display: inline-block;
                width: 4px;
                height: 16px;
                border-radius: 2px;
                margin-right: 9px;
                vertical-align: -2px;
                background: #2a6f97;
            }
            .ai-block {
                background: #f7fafc;
                border: 1px solid #eef2f6;
                box-shadow: none;
            }
            .ai-side .ai-block {
                background: #16324a;
                border: none;
                border-left: none;
            }
            .ai-side .ai-block-title { color: #ffffff; }
            .ai-side .ai-block-content { color: #d5e3ef; }
            .ai-side .ai-block .cite { color: #8fbcdb; }

            /* 行业子页签：描边药丸组 */
            .ind-tab {
                background: #ffffff;
                border-color: #dde5ec;
            }
            .ind-tab:hover { background: #f2f7fb; }
            .ind-tab.active { background: #1e7f9e; border-color: #1e7f9e; }

            /* 公司目录：浅灰内嵌卡 */
            .company-directory {
                background: #f7fafc;
                border-color: #e3e9f0;
            }

            /* 市场动向：浅灰内嵌卡 */
            .market-block {
                background: #f8fafc;
                border-color: #d7e0e9;
            }

            /* 运行统计与页脚 */
            .run-stats {
                background: #ffffff;
                border: 1px solid #e3e9f0;
                border-radius: 14px;
                padding: 16px 20px;
            }
            .footer {
                background: transparent;
                border-top: none;
                padding: 8px 0 0 0;
            }

            /* ── v2 暗色模式适配 ── */
            body.dark-mode { background: #0e161f; }
            body.dark-mode .container { background: transparent; box-shadow: none; }
            body.dark-mode .header,
            body.dark-mode .metric-card,
            body.dark-mode .zone,
            body.dark-mode .zone-company,
            body.dark-mode .zone-industry,
            body.dark-mode .ai-section,
            body.dark-mode .run-stats {
                background: #16202c;
                border-color: #26364a;
            }
            body.dark-mode .header-title,
            body.dark-mode .metric-value,
            body.dark-mode .zone-industry .zone-title,
            body.dark-mode .zone-company .zone-title,
            body.dark-mode .ai-section-title { color: #e2e8f0; }
            body.dark-mode .header-sub, body.dark-mode .metric-label,
            body.dark-mode .metric-unit, body.dark-mode .legend-line { color: #64798c; }
            body.dark-mode .headline-card {
                background: #14273a;
                border-color: #26364a;
                color: #a4c6de;
            }
            body.dark-mode .save-btn, body.dark-mode .toggle-wide-btn,
            body.dark-mode .toggle-dark-btn, body.dark-mode .save-dropdown-trigger {
                background: #16202c;
                border-color: #26364a;
                color: #a4c3dc;
            }
            body.dark-mode .zone-header { border-bottom-color: #26364a; }
            body.dark-mode .ai-block { background: #1b2836; border-color: #26364a; }
            body.dark-mode .ai-side .ai-block { background: #12395c; }
            body.dark-mode .ind-tab { background: #16202c; border-color: #26364a; }
            body.dark-mode .company-directory { background: #121a24; border-color: #26364a; }
            body.dark-mode .market-block { background: #121a24; border-color: #2b4a63; }
            body.dark-mode .search-input { background: #16202c; border-color: #26364a; }
            body.dark-mode .footer { background: transparent; border-top: none; }
        </style>
    </head>
    <body>
        <div class="reading-progress"></div>
        <div class="container">
            <div class="header">
                <div class="header-watermark">TrendRadar</div>
                <div class="save-buttons">
                    <button class="toggle-wide-btn" onclick="toggleWideMode()" title="在电脑宽屏和手机窄屏排版之间切换">📱 手机版</button>
                    <button class="toggle-dark-btn" onclick="toggleDarkMode()" title="切换暗色/亮色">☽</button>
                    <div class="save-btn-group">
                        <button class="save-btn" onclick="saveAsImage(event)">导出</button>
                        <button class="save-dropdown-trigger">▾</button>
                        <div class="save-dropdown-menu">
                            <button class="save-dropdown-item" onclick="saveAsImage(event)"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><circle cx="8" cy="7.5" r="2.5"/><path d="M12 4h.01"/></svg>整页截图</button>
                            <button class="save-dropdown-item" onclick="saveAsMultipleImages(event)"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="4" width="10" height="10" rx="1.5"/><path d="M5 4V2.5A1.5 1.5 0 016.5 1h7A1.5 1.5 0 0115 2.5v7a1.5 1.5 0 01-1.5 1.5H12"/></svg>分段截图</button>
                            <button class="save-dropdown-item" onclick="saveAsMarkdown()"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2.5 2h11A1.5 1.5 0 0115 3.5v9a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12.5v-9A1.5 1.5 0 012.5 2z"/><path d="M4 11V5l2.5 3L9 5v6"/><path d="M11.5 8v3m0 0l-1.5-2m1.5 2l1.5-2"/></svg>Markdown</button>
                        </div>
                    </div>
                </div>
                <div class="header-title">产业情报简报</div>"""

    # 使用提供的时间函数或默认 datetime.now
    if get_time_func:
        now = get_time_func()
    else:
        now = datetime.now()

    # 处理报告类型显示
    if mode == "current":
        mode_display = "当前榜单"
    elif mode == "incremental":
        mode_display = "增量监控"
    else:
        mode_display = "全天汇总"

    # ── 读者视角页头（卡片化设计）──
    html += f"""
                <div class="header-sub">{mode_display} · {now.strftime("%m-%d %H:%M")} 生成</div>"""

    html += """
            </div>

            <div class="content">"""

    # 一句话总研判（取 AI 行业研判的第一行，独立强调卡）
    headline = ""
    if ai_analysis is not None and getattr(ai_analysis, "success", False):
        core_text = (getattr(ai_analysis, "core_trends", "") or "").strip()
        if core_text:
            headline = core_text.split("\n")[0].strip()
            if len(headline) > 90:
                headline = headline[:90] + "…"
    if headline:
        html += f"""
                <div class="headline-card">「{html_escape(headline)}」</div>"""

    # 大数字指标卡行（读者关心的数字）
    def _hdr_is_company(cat):
        return bool(cat) and any(h in cat for h in ("公司", "客户", "监控"))

    active_stats_hdr = [s_ for s_ in report_data["stats"] if s_.get("count", 0) > 0]
    company_updates = sum(1 for s_ in active_stats_hdr if _hdr_is_company(s_.get("category")))
    industry_updates = sum(
        1 for s_ in active_stats_hdr
        if s_.get("category") and not _hdr_is_company(s_.get("category"))
    )
    total_picked = sum(s_["count"] for s_ in active_stats_hdr)
    new_count = report_data.get("total_new_count", 0)

    metric_cards = [
        ("行业动态", industry_updates, "组更新"),
        ("客户动态", company_updates, "家"),
        ("精选资讯", total_picked, "条"),
    ]
    if new_count:
        metric_cards.append(("本次新增", new_count, "条"))
    html += """
                <div class="metric-row">"""
    for m_label, m_value, m_unit in metric_cards:
        html += f"""
                    <div class="metric-card">
                        <div class="metric-label">{m_label}</div>
                        <div class="metric-value">{m_value}<span class="metric-unit">{m_unit}</span></div>
                    </div>"""
    html += """
                </div>"""

    # 标注图例（页面最开头的读法说明）
    html += """
                <div class="legend-line">标注说明：<b>#n</b>＝该平台热榜排名（颜色越深越靠前，区间为当日波动）· <b>n次</b>＝当日累计上榜次数 · <b>RSS</b>＝订阅源文章（附摘要，点击展开）· <b>[n]</b>＝引用角标，悬停看标题与信源</div>"""

    # ── 运维指标（挪到页面底部展示） ──
    # 只统计热榜条目（RSS 已并入 stats，需排除，避免出现 12/9 这种口径错位）
    hot_news_count = sum(
        1
        for stat in report_data["stats"]
        for t in stat["titles"]
        if not t.get("is_rss")
    )
    hotlist_total = report_data.get("hotlist_total", total_titles)
    platform_total = report_data.get("platform_total", 0)
    failed_count = len(report_data.get("failed_ids", []))
    platform_success = platform_total - failed_count if platform_total else 0
    rss_matched = report_data.get("rss_matched_count", 0)
    rss_total = report_data.get("rss_total_count", 0)
    rss_source_total = report_data.get("rss_source_total", 0)
    rss_source_failed = report_data.get("rss_source_failed", 0)
    rss_source_success = max(0, rss_source_total - rss_source_failed)

    rss_value = f"{rss_matched} / {rss_total}" if rss_source_total > 0 else "未启用"
    platform_value = f"{platform_success}/{platform_total}" if platform_total > 0 else "--"
    rss_source_value = f"{rss_source_success}/{rss_source_total}" if rss_source_total > 0 else "--"

    if ai_analysis and getattr(ai_analysis, "success", False):
        hotlist_analyzed = getattr(ai_analysis, "hotlist_analyzed", 0)
        rss_analyzed = getattr(ai_analysis, "rss_analyzed", 0)
        standalone_analyzed = getattr(ai_analysis, "standalone_analyzed", 0)
        ai_include_rss = getattr(ai_analysis, "include_rss", True)
        ai_include_standalone = getattr(ai_analysis, "include_standalone", False)
        ai_parts = [str(hotlist_analyzed)]
        if ai_include_rss:
            ai_parts.append(str(rss_analyzed))
        if ai_include_standalone:
            ai_parts.append(str(standalone_analyzed))
        ai_value = " + ".join(ai_parts) if sum(int(x) for x in ai_parts) > 0 else "0"
    elif ai_analysis:
        ai_value = "已跳过" if getattr(ai_analysis, "skipped", False) else "待配置"
    else:
        ai_value = "未启用"

    run_stats_items = [
        ("报告类型", mode_display),
        ("生成时间", now.strftime("%m-%d %H:%M")),
        ("热榜命中", f"{hot_news_count} / {hotlist_total}"),
        ("RSS 命中", rss_value),
        ("热榜平台", platform_value),
        ("RSS 源", rss_source_value),
        ("新增热点", str(new_count) if new_count else "0"),
        ("AI 分析", ai_value),
    ]
    run_stats_html = """
                <div class="run-stats section-divider">
                    <div class="run-stats-title">运行统计</div>
                    <div class="run-stats-grid">"""
    for rs_label, rs_value in run_stats_items:
        run_stats_html += f"""
                        <div class="run-stat"><span class="run-stat-label">{rs_label}</span><span class="run-stat-value">{rs_value}</span></div>"""
    run_stats_html += """
                    </div>
                </div>"""

    # 历史报告导航（每天最后一份快照；邮件等无 JS 环境中保持隐藏）
    history_nav = report_data.get("history_nav") or []
    if history_nav:
        import re as _re

        html += """
                <div class="history-nav" style="display:none">
                    <span class="history-nav-label">历史</span>"""
        for h_idx, h in enumerate(history_nav):
            date_match = _re.search(r"(\d{1,4})年(\d{1,2})月(\d{1,2})日", h["date"])
            if date_match:
                short_date = f"{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
            else:
                short_date = h["date"]
            active_class = " active" if h_idx == 0 else ""
            html += f"""
                    <a class="history-chip{active_class}" href="#" data-hist-date="{html_escape(h["date"])}" data-hist-file="{html_escape(h["file"])}">{html_escape(short_date)}</a>"""
        html += """
                    <a class="history-chip history-chip-latest" href="#" data-latest-link style="display:none">↻ 最新报告</a>
                    <a class="history-chip" href="#" data-manager-link style="margin-left:auto">⚙ 订阅管理</a>
                </div>"""

    html += """
                <div class="search-bar">
                    <input type="text" class="search-input" placeholder="搜索新闻标题..." oninput="handleSearch(this.value)">
                </div>"""

    # 处理失败ID错误信息
    if report_data["failed_ids"]:
        html += """
                <div class="error-section">
                    <div class="error-title">⚠️ 请求失败的平台</div>
                    <ul class="error-list">"""
        for id_value in report_data["failed_ids"]:
            html += f'<li class="error-item">{html_escape(id_value)}</li>'
        html += """
                    </ul>
                </div>"""


    def render_news_item(j, title_data):
        """渲染单条新闻（热榜与 RSS 条目通用；RSS 条目附摘要，可点击展开）"""
        is_new = title_data.get("is_new", False)
        new_class = "new" if is_new else ""
        item_html = f"""
                    <div class="news-item {new_class}">
                        <div class="news-number">{j}</div>
                        <div class="news-content">
                            <div class="news-header">"""

        if display_mode == "keyword":
            item_html += f'<span class="source-name">{html_escape(title_data["source_name"])}</span>'
        else:
            matched_keyword = title_data.get("matched_keyword", "")
            if matched_keyword:
                item_html += f'<span class="keyword-tag">[{html_escape(matched_keyword)}]</span>'

        if title_data.get("is_rss"):
            item_html += '<span class="rss-chip">RSS</span>'

        # 排名徽标（RSS 条目的排名只是时序，不展示）
        ranks = title_data.get("ranks", [])
        if ranks and not title_data.get("is_rss"):
            min_rank = min(ranks)
            max_rank = max(ranks)
            rank_threshold = title_data.get("rank_threshold", 10)

            if min_rank <= 3:
                rank_class = "top"
            elif min_rank <= rank_threshold:
                rank_class = "high"
            else:
                rank_class = ""

            rank_text = str(min_rank) if min_rank == max_rank else f"{min_rank}-{max_rank}"

            rank_timeline = title_data.get("rank_timeline", [])
            trend = calculate_rank_trend(rank_timeline, ranks)
            trend_html = ""
            if trend == "up":
                trend_html = '<span class="trend-up">📈</span>'
            elif trend == "down":
                trend_html = '<span class="trend-down">📉</span>'

            item_html += f'<span class="rank-num {rank_class}" title="该平台热榜排名（数字越小越靠前，区间为当日排名波动范围）">#{rank_text}</span>{trend_html}'

        time_display = title_data.get("time_display", "")
        if time_display:
            simplified_time = (
                time_display.replace(" ~ ", "~").replace("[", "").replace("]", "")
            )
            item_html += f'<span class="time-info" title="上榜时间（区间为首次~最近）">{html_escape(simplified_time)}</span>'

        count_info = title_data.get("count", 1)
        if count_info > 1:
            item_html += f'<span class="count-info" title="当日累计上榜次数">{count_info}次</span>'

        item_html += """
                            </div>
                            <div class="news-title">"""

        escaped_title = html_escape(title_data["title"])
        link_url = title_data.get("mobile_url") or title_data.get("url", "")
        if link_url:
            escaped_url = html_escape(link_url)
            item_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
        else:
            item_html += escaped_title

        item_html += """
                            </div>"""

        # RSS 摘要（默认 4 行，点击展开）
        summary = (title_data.get("summary") or "").strip()
        if summary and summary != title_data.get("title", ""):
            item_html += f"""
                            <div class="rss-summary" onclick="this.classList.toggle('expanded')" title="点击展开/收起全文">{html_escape(summary)}</div>"""

        item_html += """
                        </div>
                    </div>"""
        return item_html

    def render_word_group(stat, extra_attr="", group_id=""):
        """渲染一个关键词组（组头 + 条目列表）"""
        count = stat["count"]
        if count >= 10:
            count_class = "hot"
        elif count >= 5:
            count_class = "warm"
        else:
            count_class = ""
        id_attr = f' id="{group_id}"' if group_id else ""
        group_html = f"""
                <div class="word-group"{id_attr} {extra_attr}>
                    <div class="word-header">
                        <div class="word-info">
                            <div class="word-name">{html_escape(stat["word"])}</div>
                            <div class="word-count {count_class}">{count} 条</div>
                        </div>
                        <div class="word-index"><span class="collapse-icon">▼</span></div>
                    </div>"""
        for j, title_data in enumerate(stat["titles"], 1):
            group_html += render_news_item(j, title_data)
        group_html += """
                </div>"""
        return group_html


    def build_cluster_cites(items):
        """构建引用角标（悬停显示标题/信源/时间，点击打开原文）"""
        cites = ""
        for ci, t in enumerate(items, 1):
            link = t.get("mobile_url") or t.get("url", "")
            tip = f"{t.get('title', '')} ｜ {t.get('source_name', '')}"
            time_disp = (t.get("time_display") or "").replace("[", "").replace("]", "")
            if time_disp:
                tip += f" · {time_disp}"
            if link:
                cites += f'<a class="cite" href="{html_escape(link)}" target="_blank" title="{html_escape(tip)}">[{ci}]</a>'
            else:
                cites += f'<span class="cite" title="{html_escape(tip)}">[{ci}]</span>'
        return cites

    # AI 判定的公司主体阵营排序：美国头部 → 中国头部 → 其他主题
    _SECTION_RANK = {"us": 0, "cn": 1}
    _SECTION_LABEL = {"us": "美国头部", "cn": "中国头部"}

    def render_industry_group(stat, extra_attr="", claimed_ids=None):
        """渲染行业词组：按 AI 判定的公司主体聚合产业实质资讯

        - 簇排序：美国头部厂商 → 中国头部厂商 → 其他公司/主题；
        - 市场涨跌类条目已被"投资市场动向"区认领（claimed_ids），此处跳过；
        - AI 未覆盖的条目折叠收纳，降低视觉信息量。
        """
        claimed_ids = claimed_ids or set()
        ai_clusters_all = (
            getattr(ai_analysis, "industry_clusters", None) or []
            if ai_analysis is not None
            else []
        )
        group_clusters = sorted(
            (
                c for c in ai_clusters_all
                if c.get("group") in ("", stat["word"]) and c.get("section") != "market"
            ),
            key=lambda c: _SECTION_RANK.get(c.get("section"), 2),
        )

        count = stat["count"]
        count_class = "hot" if count >= 10 else ("warm" if count >= 5 else "")
        group_html = (
            f'\n                <div class="word-group" {extra_attr}>'
            '<div class="word-header"><div class="word-info">'
            f'<div class="word-name">{html_escape(stat["word"])}</div>'
            f'<div class="word-count {count_class}">{count} 条</div>'
            '</div><div class="word-index"><span class="collapse-icon">▼</span></div></div>'
        )

        # 用 AI 返回的标题（逐字复制）匹配本组条目；精确优先、模糊兜底
        remaining = [t for t in stat["titles"] if id(t) not in claimed_ids]
        clusters_html = ""
        for c in group_clusters:
            items = []
            for ct in c.get("titles", []):
                match = next((t for t in remaining if t.get("title") == ct), None)
                if match is None:
                    match = next(
                        (t for t in remaining if _titles_similar(t.get("title", ""), ct)),
                        None,
                    )
                if match is not None:
                    remaining.remove(match)
                    items.append(match)
            if not items:
                continue
            region = _SECTION_LABEL.get(c.get("section"))
            region_html = f'<span class="cluster-region">{region}</span>' if region else ""
            clusters_html += (
                '<div class="cluster">'
                f'<div class="cluster-hd">{html_escape(c["company"])}{region_html}<span class="cluster-cnt">{len(items)} 条</span></div>'
                f'<div class="cluster-sum">{html_escape(c["summary"])}<span class="cites">{build_cluster_cites(items)}</span></div>'
                '</div>'
            )

        group_html += clusters_html

        # AI 未覆盖的条目：少量直接展示，多了折叠收纳（降低信息量，脉络优先）
        if remaining:
            if clusters_html and len(remaining) > 3:
                group_html += (
                    f'<details class="more-items"><summary>更多条目（{len(remaining)}）</summary>'
                )
                for j, t in enumerate(remaining, 1):
                    group_html += render_news_item(j, t)
                group_html += "</details>"
            else:
                if clusters_html:
                    group_html += '<div class="cluster-rest-label">其他条目</div>'
                for j, t in enumerate(remaining, 1):
                    group_html += render_news_item(j, t)

        group_html += "\n                </div>"
        return group_html

    # 生成热点分区 HTML（公司监控＝名单目录+资讯流；行业动态＝子行业页签）
    stats_html = ""
    if report_data["stats"]:
        active_stats = [s for s in report_data["stats"] if s.get("count", 0) > 0]
        stats_list, category_order = _order_stats_by_category(active_stats)
        empty_groups_all = report_data.get("empty_groups") or []

        def _is_company_cat(name):
            return bool(name) and any(h in name for h in ("公司", "客户", "监控"))

        if category_order:
            # 展示顺序：行业动态在前、公司监控在后（关键词匹配优先级仍以词表顺序为准）
            display_cat_order = sorted(
                category_order,
                key=lambda c: 1 if _is_company_cat(c if c is not None else "") else 0,
            )
            zone_idx = 0
            for cat in display_cat_order:
                cat_stats = [s for s in stats_list if s.get("category") == cat]
                cat_empty = [
                    g["word"] for g in empty_groups_all
                    if (g.get("category") if g.get("category") is not None else None) == cat
                ]
                if not cat_stats and not cat_empty:
                    continue
                cat_name = cat if cat is not None else "其他"
                total_items = sum(s["count"] for s in cat_stats)
                is_company = _is_company_cat(cat_name)
                zone_class = "zone-company" if is_company else "zone-industry"

                stats_html += f"""
                <div class="zone {zone_class}">
                    <div class="zone-header">
                        <span class="zone-icon">{_category_icon(cat_name, zone_idx)}</span>
                        <span class="zone-title">{html_escape(cat_name)}</span>
                        <span class="zone-meta">{len(cat_stats)} 组有更新 · {total_items} 条资讯</span>
                    </div>"""

                if is_company:
                    # ── 公司监控：左侧名单目录 + 右侧资讯流 ──
                    stats_html += """
                    <div class="company-layout">
                        <aside class="company-directory">
                            <div class="dir-title">监控名单</div>
                            <div class="dir-list">"""
                    for k, s in enumerate(cat_stats):
                        stats_html += f"""
                                <a class="dir-item" href="#company-grp-{zone_idx}-{k}">{html_escape(s["word"])}<span class="dir-count">{s["count"]}</span></a>"""
                    for w in cat_empty:
                        stats_html += f"""
                                <span class="dir-item dir-muted">{html_escape(w)}</span>"""
                    stats_html += """
                            </div>
                            <div class="dir-note">灰色名称＝今日无相关资讯。点击有更新的公司可跳转到对应资讯；名单可在页面底部「订阅管理」中增删。</div>
                        </aside>
                        <div class="company-feed">"""
                    if cat_stats:
                        for k, s in enumerate(cat_stats):
                            stats_html += render_word_group(s, group_id=f"company-grp-{zone_idx}-{k}")
                    else:
                        stats_html += """
                            <div class="zone-empty-feed">监控名单今日暂无资讯更新</div>"""
                    stats_html += """
                        </div>
                    </div>"""
                else:
                    # ── 行业动态：子行业页签 + 词组 ──
                    # 先让"投资市场动向"簇跨层级认领涨跌类条目，组内渲染时跳过
                    ai_clusters_all = (
                        getattr(ai_analysis, "industry_clusters", None) or []
                        if ai_analysis is not None
                        else []
                    )
                    market_clusters = [
                        c for c in ai_clusters_all if c.get("section") == "market"
                    ]
                    all_ind_items = [t for s_ in cat_stats for t in s_["titles"]]
                    claimed_ids = set()
                    market_blocks = []
                    for c in market_clusters:
                        m_items = []
                        for ct in c.get("titles", []):
                            match = next(
                                (t for t in all_ind_items
                                 if id(t) not in claimed_ids and t.get("title") == ct),
                                None,
                            )
                            if match is None:
                                match = next(
                                    (t for t in all_ind_items
                                     if id(t) not in claimed_ids
                                     and _titles_similar(t.get("title", ""), ct)),
                                    None,
                                )
                            if match is not None:
                                claimed_ids.add(id(match))
                                m_items.append(match)
                        if m_items:
                            market_blocks.append((c, m_items))

                    if cat_stats:
                        stats_html += f"""
                    <div class="ind-tabbar">
                        <button class="ind-tab active" data-ind="all">全部<span class="tab-count">{total_items}</span></button>"""
                        for k, s in enumerate(cat_stats):
                            stats_html += f"""
                        <button class="ind-tab" data-ind="{k}">{html_escape(s["word"])}<span class="tab-count">{s["count"]}</span></button>"""
                        stats_html += """
                    </div>
                    <div class="ind-groups">"""
                        for k, s in enumerate(cat_stats):
                            stats_html += render_industry_group(
                                s, extra_attr=f'data-ind-idx="{k}"', claimed_ids=claimed_ids
                            )
                        stats_html += """
                    </div>"""

                    # 投资市场动向：涨跌/资金类资讯统一收纳，与产业实质资讯分离
                    if market_blocks:
                        market_total = sum(len(items) for _, items in market_blocks)
                        stats_html += f"""
                    <div class="market-block">
                        <div class="market-hd">投资市场动向<span class="market-cnt">{market_total} 条</span></div>"""
                        for c, m_items in market_blocks:
                            stats_html += (
                                '<div class="cluster">'
                                f'<div class="cluster-hd">{html_escape(c["company"])}<span class="cluster-cnt">{len(m_items)} 条</span></div>'
                                f'<div class="cluster-sum">{html_escape(c["summary"])}<span class="cites">{build_cluster_cites(m_items)}</span></div>'
                                '</div>'
                            )
                        stats_html += """
                    </div>"""
                    if cat_empty:
                        stats_html += f"""
                    <div class="zone-empty">📭 今日无动态：{html_escape("、".join(cat_empty))}</div>"""

                stats_html += """
                </div>"""
                zone_idx += 1
        else:
            # 无分类配置：平铺渲染
            for stat in stats_list:
                stats_html += render_word_group(stat)

    # 给热点分区添加外层包装
    if stats_html:
        stats_html = f"""
                <div class="hotlist-section">{stats_html}
                </div>"""

    # 生成新增新闻区域的HTML
    new_titles_html = ""
    if show_new_section and report_data["new_titles"]:
        new_titles_html += f"""
                <div class="new-section">
                    <div class="new-section-title">本次新增热点 (共 {report_data['total_new_count']} 条)</div>
                    <div class="new-sources-grid">"""

        for source_data in report_data["new_titles"]:
            escaped_source = html_escape(source_data["source_name"])
            titles_count = len(source_data["titles"])

            new_titles_html += f"""
                    <div class="new-source-group">
                        <div class="new-source-title">{escaped_source} · {titles_count}条</div>"""

            # 为新增新闻也添加序号
            for idx, title_data in enumerate(source_data["titles"], 1):
                ranks = title_data.get("ranks", [])

                # 处理新增新闻的排名显示
                rank_class = ""
                if ranks:
                    min_rank = min(ranks)
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= title_data.get("rank_threshold", 10):
                        rank_class = "high"

                    if len(ranks) == 1:
                        rank_text = str(ranks[0])
                    else:
                        rank_text = f"{min(ranks)}-{max(ranks)}"
                else:
                    rank_text = "?"

                new_titles_html += f"""
                        <div class="new-item">
                            <div class="new-item-number">{idx}</div>
                            <div class="new-item-rank {rank_class}">{rank_text}</div>
                            <div class="new-item-content">
                                <div class="new-item-title">"""

                # 处理新增新闻的链接
                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    new_titles_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    new_titles_html += escaped_title

                new_titles_html += """
                                </div>
                            </div>
                        </div>"""

            new_titles_html += """
                    </div>"""

        new_titles_html += """
                    </div>
                </div>"""

    # 生成 RSS 统计内容
    def render_rss_stats_html(stats: List[Dict], title: str = "RSS 订阅更新") -> str:
        """渲染 RSS 统计区块 HTML

        Args:
            stats: RSS 分组统计列表，格式与热榜一致：
                [
                    {
                        "word": "关键词",
                        "count": 5,
                        "titles": [
                            {
                                "title": "标题",
                                "source_name": "Feed 名称",
                                "time_display": "12-29 08:20",
                                "url": "...",
                                "is_new": True/False
                            }
                        ]
                    }
                ]
            title: 区块标题

        Returns:
            渲染后的 HTML 字符串
        """
        if not stats:
            return ""

        # 计算总条目数
        total_count = sum(stat.get("count", 0) for stat in stats)
        if total_count == 0:
            return ""

        rss_html = f"""
                <div class="rss-section">
                    <div class="rss-section-header">
                        <div class="rss-section-title">{title}</div>
                        <div class="rss-section-count">{total_count} 条</div>
                    </div>
                    <div class="rss-feeds-grid">"""

        # 按分类归拢关键词组（如 行业动态 / 公司监控）
        ordered_stats, category_order = _order_stats_by_category(stats)
        category_counts = {}
        for stat in ordered_stats:
            cat = stat.get("category")
            category_counts[cat] = category_counts.get(cat, 0) + len(stat.get("titles", []))

        rendered_category = object()
        # 按关键词分组渲染（与热榜格式一致）
        for stat in ordered_stats:
            keyword = stat.get("word", "")
            titles = stat.get("titles", [])
            if not titles:
                continue

            # 分类切换时插入分类标签
            current_cat = stat.get("category")
            if category_order and current_cat != rendered_category:
                rendered_category = current_cat
                cat_idx = category_order.index(current_cat)
                cat_name = current_cat if current_cat is not None else "其他"
                rss_html += f"""
                    <div class="rss-category-label category-style-{cat_idx % 3}">
                        <span class="category-icon">{_category_icon(current_cat, cat_idx)}</span>
                        <span>{html_escape(cat_name)}</span>
                        <span class="rss-category-count">{category_counts.get(current_cat, 0)} 条</span>
                    </div>"""

            keyword_count = len(titles)

            rss_html += f"""
                    <div class="feed-group">
                        <div class="feed-header">
                            <div class="feed-name">{html_escape(keyword)}</div>
                            <div class="feed-count">{keyword_count} 条</div>
                        </div>"""

            for title_data in titles:
                item_title = title_data.get("title", "")
                url = title_data.get("url", "")
                time_display = title_data.get("time_display", "")
                source_name = title_data.get("source_name", "")
                is_new = title_data.get("is_new", False)
                summary = (title_data.get("summary") or "").strip()
                author = (title_data.get("author") or "").strip()

                rss_html += """
                        <div class="rss-item">
                            <div class="rss-meta">"""

                if time_display:
                    rss_html += f'<span class="rss-time">{html_escape(time_display)}</span>'

                if source_name:
                    rss_html += f'<span class="rss-author">{html_escape(source_name)}</span>'

                if author and author != source_name:
                    rss_html += f'<span class="rss-time">{html_escape(author)}</span>'

                if is_new:
                    rss_html += '<span class="rss-author" style="color: #16548f;">NEW</span>'

                rss_html += """
                            </div>
                            <div class="rss-title">"""

                escaped_title = html_escape(item_title)
                if url:
                    escaped_url = html_escape(url)
                    rss_html += f'<a href="{escaped_url}" target="_blank" class="rss-link">{escaped_title}</a>'
                else:
                    rss_html += escaped_title

                rss_html += """
                            </div>"""

                # 摘要（默认显示 4 行，点击展开全文，帮助判断是否值得点开原文）
                if summary and summary != item_title:
                    rss_html += f"""
                            <div class="rss-summary" onclick="this.classList.toggle('expanded')" title="点击展开/收起全文">{html_escape(summary)}</div>"""

                rss_html += """
                        </div>"""

            rss_html += """
                    </div>"""

        rss_html += """
                    </div>
                </div>"""
        return rss_html

    # 生成独立展示区内容
    def render_standalone_html(data: Optional[Dict]) -> str:
        """渲染独立展示区 HTML（复用热点词汇统计区样式）

        Args:
            data: 独立展示数据，格式：
                {
                    "platforms": [
                        {
                            "id": "zhihu",
                            "name": "知乎热榜",
                            "items": [
                                {
                                    "title": "标题",
                                    "url": "链接",
                                    "rank": 1,
                                    "ranks": [1, 2, 1],
                                    "first_time": "08:00",
                                    "last_time": "12:30",
                                    "count": 3,
                                }
                            ]
                        }
                    ],
                    "rss_feeds": [
                        {
                            "id": "hacker-news",
                            "name": "Hacker News",
                            "items": [
                                {
                                    "title": "标题",
                                    "url": "链接",
                                    "published_at": "2025-01-07T08:00:00",
                                    "author": "作者",
                                }
                            ]
                        }
                    ]
                }

        Returns:
            渲染后的 HTML 字符串
        """
        if not data:
            return ""

        platforms = data.get("platforms", [])
        rss_feeds = data.get("rss_feeds", [])

        if not platforms and not rss_feeds:
            return ""

        # 计算总条目数
        total_platform_items = sum(len(p.get("items", [])) for p in platforms)
        total_rss_items = sum(len(f.get("items", [])) for f in rss_feeds)
        total_count = total_platform_items + total_rss_items

        if total_count == 0:
            return ""

        # 收集所有分组信息用于生成 tab
        all_groups = []
        for p in platforms:
            items = p.get("items", [])
            if items:
                all_groups.append({"name": p.get("name", p.get("id", "")), "count": len(items)})
        for f in rss_feeds:
            items = f.get("items", [])
            if items:
                all_groups.append({"name": f.get("name", f.get("id", "")), "count": len(items)})

        standalone_html = f"""
                <div class="standalone-section">
                    <div class="standalone-section-header">
                        <div class="standalone-section-title">独立展示区</div>
                        <div class="standalone-section-count">{total_count} 条</div>
                    </div>"""

        # 生成 tab 栏（2+ 分组时）
        if len(all_groups) >= 2:
            standalone_html += """
                    <div class="tab-bar standalone-tab-bar">"""
            for idx, g in enumerate(all_groups):
                active = ' active' if idx == 0 else ''
                standalone_html += f"""
                        <button class="tab-btn{active}" data-standalone-tab="{idx}">{html_escape(g["name"])}<span class="tab-count">{g["count"]}</span></button>"""
            standalone_html += f"""
                        <button class="tab-btn" data-standalone-tab="all">全部<span class="tab-count">{total_count}</span></button>
                    </div>"""

        standalone_html += """
                    <div class="standalone-groups-grid">"""

        group_idx = 0
        # 渲染热榜平台（复用 word-group 结构）
        for platform in platforms:
            platform_name = platform.get("name", platform.get("id", ""))
            items = platform.get("items", [])
            if not items:
                continue

            standalone_html += f"""
                    <div class="standalone-group" data-standalone-tab="{group_idx}">
                        <div class="standalone-header">
                            <div class="standalone-name">{html_escape(platform_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

            # 渲染每个条目（复用 news-item 结构）
            for j, item in enumerate(items, 1):
                title = item.get("title", "")
                url = item.get("url", "") or item.get("mobileUrl", "")
                rank = item.get("rank", 0)
                ranks = item.get("ranks", [])
                first_time = item.get("first_time", "")
                last_time = item.get("last_time", "")
                count = item.get("count", 1)

                standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

                # 排名显示（复用 rank-num 样式，无 # 前缀）
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)

                    # 确定排名等级
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= 10:
                        rank_class = "high"
                    else:
                        rank_class = ""

                    if min_rank == max_rank:
                        rank_text = str(min_rank)
                    else:
                        rank_text = f"{min_rank}-{max_rank}"

                    standalone_html += f'<span class="rank-num {rank_class}">{rank_text}</span>'
                elif rank > 0:
                    if rank <= 3:
                        rank_class = "top"
                    elif rank <= 10:
                        rank_class = "high"
                    else:
                        rank_class = ""
                    standalone_html += f'<span class="rank-num {rank_class}">{rank}</span>'

                # 时间显示（复用 time-info 样式，将 HH-MM 转换为 HH:MM）
                if first_time and last_time and first_time != last_time:
                    first_time_display = convert_time_for_display(first_time)
                    last_time_display = convert_time_for_display(last_time)
                    standalone_html += f'<span class="time-info">{html_escape(first_time_display)}~{html_escape(last_time_display)}</span>'
                elif first_time:
                    first_time_display = convert_time_for_display(first_time)
                    standalone_html += f'<span class="time-info">{html_escape(first_time_display)}</span>'

                # 出现次数（复用 count-info 样式）
                if count > 1:
                    standalone_html += f'<span class="count-info">{count}次</span>'

                standalone_html += """
                                </div>
                                <div class="news-title">"""

                # 标题和链接（复用 news-link 样式）
                escaped_title = html_escape(title)
                if url:
                    escaped_url = html_escape(url)
                    standalone_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    standalone_html += escaped_title

                standalone_html += """
                                </div>
                            </div>
                        </div>"""

            standalone_html += """
                    </div>"""
            group_idx += 1

        # 渲染 RSS 源（复用相同结构）
        for feed in rss_feeds:
            feed_name = feed.get("name", feed.get("id", ""))
            items = feed.get("items", [])
            if not items:
                continue

            standalone_html += f"""
                    <div class="standalone-group" data-standalone-tab="{group_idx}">
                        <div class="standalone-header">
                            <div class="standalone-name">{html_escape(feed_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

            for j, item in enumerate(items, 1):
                title = item.get("title", "")
                url = item.get("url", "")
                published_at = item.get("published_at", "")
                author = item.get("author", "")

                standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

                # 时间显示（格式化 ISO 时间）
                if published_at:
                    try:
                        from datetime import datetime as dt
                        if "T" in published_at:
                            dt_obj = dt.fromisoformat(published_at.replace("Z", "+00:00"))
                            time_display = dt_obj.strftime("%m-%d %H:%M")
                        else:
                            time_display = published_at
                    except:
                        time_display = published_at

                    standalone_html += f'<span class="time-info">{html_escape(time_display)}</span>'

                # 作者显示
                if author:
                    standalone_html += f'<span class="source-name">{html_escape(author)}</span>'

                standalone_html += """
                                </div>
                                <div class="news-title">"""

                escaped_title = html_escape(title)
                if url:
                    escaped_url = html_escape(url)
                    standalone_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    standalone_html += escaped_title

                standalone_html += """
                                </div>
                            </div>
                        </div>"""

            standalone_html += """
                    </div>"""
            group_idx += 1

        standalone_html += """
                    </div>
                </div>"""
        return standalone_html

    # 生成 RSS 统计和新增 HTML
    # RSS 已并入热点分区时不再单独渲染，避免同一批信息出现两遍
    rss_stats_html = (
        render_rss_stats_html(rss_items, "RSS 订阅更新")
        if rss_items and not merged_rss
        else ""
    )
    rss_new_html = render_rss_stats_html(rss_new_items, "RSS 新增更新") if rss_new_items else ""

    # 生成独立展示区 HTML
    standalone_html = render_standalone_html(standalone_data)

    # 生成 AI 分析 HTML
    ai_html = render_ai_analysis_html_rich(ai_analysis) if ai_analysis else ""

    # 准备各区域内容映射
    region_contents = {
        "hotlist": stats_html,
        "rss": rss_stats_html,
        "new_items": (new_titles_html, rss_new_html),  # 元组，分别处理
        "standalone": standalone_html,
        "ai_analysis": ai_html,
    }

    def add_section_divider(content: str) -> str:
        """为内容的外层 div 添加 section-divider 类"""
        if not content or 'class="' not in content:
            return content
        first_class_pos = content.find('class="')
        if first_class_pos != -1:
            insert_pos = first_class_pos + len('class="')
            return content[:insert_pos] + "section-divider " + content[insert_pos:]
        return content

    # 按 region_order 顺序组装内容，动态添加分割线
    has_previous_content = False
    for region in region_order:
        content = region_contents.get(region, "")
        if region == "new_items":
            # 特殊处理 new_items 区域（包含热榜新增和 RSS 新增两部分）
            new_html, rss_new = content
            if new_html:
                if has_previous_content:
                    new_html = add_section_divider(new_html)
                html += new_html
                has_previous_content = True
            if rss_new:
                if has_previous_content:
                    rss_new = add_section_divider(rss_new)
                html += rss_new
                has_previous_content = True
        elif content:
            if has_previous_content:
                content = add_section_divider(content)
            html += content
            has_previous_content = True

    # 运行统计（运维指标，放页面底部，不占用阅读主区）
    html += run_stats_html

    # 订阅管理面板（固定在所有内容区之后、页脚之前；仅浏览器可见）
    if config_manager_data:
        html += _render_config_manager_section(config_manager_data)

    html += """
            </div>

            <div class="footer">
                <div class="footer-content">
                    由 <span class="project-name">Coco Wang</span> 制作"""

    if update_info:
        html += f"""
                    <br>
                    <span style="color: #4d8ec4; font-weight: 500;">
                        发现新版本 {update_info['remote_version']}，当前版本 {update_info['current_version']}
                    </span>"""

    html += """
                </div>
            </div>
        </div>

        <div class="fab-bar">
            <button class="fab-btn" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="返回顶部">↑</button>
            <button class="fab-btn fab-help">
                <span>?</span>
                <div class="fab-tooltip">
                    <div class="tip-row"><span>切换宽屏</span><span class="tip-key">W</span></div>
                    <div class="tip-row"><span>暗色模式</span><span class="tip-key">D</span></div>
                    <div class="tip-row"><span>搜索</span><span class="tip-key">/</span></div>
                    <div class="tip-row"><span>上一个 Tab</span><span class="tip-key">←</span></div>
                    <div class="tip-row"><span>下一个 Tab</span><span class="tip-key">→</span></div>
                    <div class="tip-row"><span>序号可复制</span><span class="tip-key">点击</span></div>
                </div>
            </button>
        </div>

        <script>
            // ===== 浏览器增强功能 =====

            function toggleWideMode() {
                document.body.classList.toggle('wide-mode');
                var isWide = document.body.classList.contains('wide-mode');
                try { localStorage.setItem('trendradar-wide-mode', isWide ? '1' : '0'); } catch(e) {}
                var btn = document.querySelector('.toggle-wide-btn');
                if (btn) btn.textContent = isWide ? '📱 手机版' : '🖥️ 电脑版';
                initTabVisibility();
                initCollapseVisibility();
                initStandaloneTabVisibility();
            }

            function toggleDarkMode() {
                var isDark = document.body.classList.toggle('dark-mode');
                try { localStorage.setItem('trendradar-dark-mode', isDark ? '1' : '0'); } catch(e) {}
                var btn = document.querySelector('.toggle-dark-btn');
                if (btn) btn.textContent = isDark ? '☀' : '☽';
            }

            function initTabScroll(tabBar) {
                var wrapper = tabBar.closest('.tab-bar-wrapper') || tabBar.parentNode;
                var leftArrow = wrapper.querySelector('.tab-arrow-left');
                var rightArrow = wrapper.querySelector('.tab-arrow-right');
                var indicator = wrapper.querySelector('.tab-scroll-indicator');
                if (!leftArrow) {
                    leftArrow = document.createElement('button');
                    leftArrow.className = 'tab-arrow tab-arrow-left';
                    leftArrow.innerHTML = '‹';
                    rightArrow = document.createElement('button');
                    rightArrow.className = 'tab-arrow tab-arrow-right';
                    rightArrow.innerHTML = '›';
                    indicator = document.createElement('div');
                    indicator.className = 'tab-scroll-indicator';
                    wrapper.insertBefore(leftArrow, tabBar);
                    tabBar.after(rightArrow);
                    wrapper.appendChild(indicator);
                }
                var scrollStep = 200;
                leftArrow.addEventListener('click', function(e) {
                    e.stopPropagation();
                    tabBar.scrollBy({ left: -scrollStep, behavior: 'smooth' });
                });
                rightArrow.addEventListener('click', function(e) {
                    e.stopPropagation();
                    tabBar.scrollBy({ left: scrollStep, behavior: 'smooth' });
                });
                function updateArrows() {
                    var sl = tabBar.scrollLeft;
                    var sw = tabBar.scrollWidth;
                    var cw = tabBar.clientWidth;
                    var noOverflow = sw <= cw + 1;
                    var atStart = sl <= 1;
                    var atEnd = sl + cw >= sw - 1;
                    leftArrow.classList.toggle('visible', !noOverflow && !atStart);
                    rightArrow.classList.toggle('visible', !noOverflow && !atEnd);
                    tabBar.classList.toggle('scroll-start', atStart);
                    tabBar.classList.toggle('scroll-end', atEnd);
                    tabBar.classList.toggle('no-overflow', noOverflow);
                    var progress = noOverflow ? 0 : sl / (sw - cw);
                    indicator.style.width = (progress * 100) + '%';
                }
                tabBar.addEventListener('scroll', updateArrows, { passive: true });
                tabBar.addEventListener('wheel', function(e) {
                    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                        tabBar.scrollLeft += e.deltaY;
                        e.preventDefault();
                    }
                }, { passive: false });
                updateArrows();
                new ResizeObserver(updateArrows).observe(tabBar);
            }

            function initTabs() {
                var wrapper = document.querySelector('.tab-bar-wrapper');
                var tabBar = wrapper ? wrapper.querySelector('.tab-bar') : null;
                if (!tabBar) return;
                var tabs = tabBar.querySelectorAll('.tab-btn');
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                initTabVisibility();
                initTabScroll(tabBar);

                function activateTab(index, scroll) {
                    tabs.forEach(function(t) { t.classList.remove('active'); });
                    if (index === 'all') {
                        var allBtn = tabBar.querySelector('[data-tab-index="all"]');
                        if (allBtn) {
                            allBtn.classList.add('active');
                            if (scroll !== false) allBtn.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
                        }
                        groups.forEach(function(g) { g.style.display = ''; });
                        document.querySelectorAll('[data-category-banner]').forEach(function(b) { b.style.display = ''; });
                        try { history.replaceState(null, '', '#all'); } catch(e) {}
                        return;
                    }
                    var idx = parseInt(index);
                    tabs.forEach(function(t) {
                        if (parseInt(t.dataset.tabIndex) === idx) t.classList.add('active');
                    });
                    if (document.body.classList.contains('wide-mode') && !wrapper.classList.contains('tab-hidden')) {
                        groups.forEach(function(g) {
                            g.style.display = (parseInt(g.dataset.tabIndex) === idx) ? '' : 'none';
                        });
                        document.querySelectorAll('[data-category-banner]').forEach(function(b) { b.style.display = 'none'; });
                    }
                    var activeBtn = tabBar.querySelector('.tab-btn.active');
                    if (scroll !== false && activeBtn) activeBtn.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
                    try { history.replaceState(null, '', '#tab-' + idx); } catch(e) {}
                }

                tabs.forEach(function(tab) {
                    tab.addEventListener('click', function() {
                        var idx = tab.dataset.tabIndex;
                        activateTab(idx === 'all' ? 'all' : parseInt(idx));
                    });
                });

                tabBar.addEventListener('keydown', function(e) {
                    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                        var tabsArr = Array.from(tabs);
                        var ci = tabsArr.findIndex(function(t) { return t.classList.contains('active'); });
                        var dir = e.key === 'ArrowRight' ? 1 : -1;
                        var ni = Math.max(0, Math.min(tabsArr.length - 1, ci + dir));
                        var nt = tabsArr[ni];
                        activateTab(nt.dataset.tabIndex === 'all' ? 'all' : parseInt(nt.dataset.tabIndex));
                        nt.focus();
                        e.preventDefault();
                    }
                });

                var hash = window.location.hash;
                if (hash === '#all') { activateTab('all'); }
                else if (hash.indexOf('#tab-') === 0) { activateTab(parseInt(hash.replace('#tab-', ''))); }
                else { activateTab('all', false); }
            }

            function initTabVisibility() {
                var wrapper = document.querySelector('.tab-bar-wrapper');
                if (!wrapper) return;
                var tabBar = wrapper.querySelector('.tab-bar');
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                var isWide = document.body.classList.contains('wide-mode');
                if (!isWide || groups.length <= 2) {
                    wrapper.classList.add('tab-hidden');
                    groups.forEach(function(g) { g.style.display = ''; });
                    document.querySelectorAll('[data-category-banner]').forEach(function(b) { b.style.display = ''; });
                } else {
                    wrapper.classList.remove('tab-hidden');
                    var activeTab = tabBar.querySelector('.tab-btn.active');
                    if (activeTab) { activeTab.click(); }
                    else {
                        var allTab = tabBar.querySelector('.tab-btn[data-tab-index="all"]');
                        if (allTab) allTab.click();
                    }
                }
            }

            var handleSearch = (function() {
                var timer = null;
                return function(query) {
                    clearTimeout(timer);
                    timer = setTimeout(function() {
                        query = query.toLowerCase();
                        document.querySelectorAll('.news-item').forEach(function(item) {
                            var title = (item.querySelector('.news-title') || {}).textContent || '';
                            item.style.display = (!query || title.toLowerCase().indexOf(query) !== -1) ? '' : 'none';
                        });
                        document.querySelectorAll('.rss-item').forEach(function(item) {
                            var title = (item.querySelector('.rss-title') || {}).textContent || '';
                            var summary = (item.querySelector('.rss-summary') || {}).textContent || '';
                            var haystack = (title + ' ' + summary).toLowerCase();
                            item.style.display = (!query || haystack.indexOf(query) !== -1) ? '' : 'none';
                        });
                    }, 200);
                };
            })();

            function initBackToTop() {
                var fabBar = document.querySelector('.fab-bar');
                if (!fabBar) return;
                var ticking = false;
                window.addEventListener('scroll', function() {
                    if (!ticking) {
                        requestAnimationFrame(function() {
                            fabBar.classList.toggle('visible', window.scrollY > 300);
                            ticking = false;
                        });
                        ticking = true;
                    }
                });
            }

            function initCollapse() {
                document.querySelectorAll('.word-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var wrapper = document.querySelector('.tab-bar-wrapper');
                        if (document.body.classList.contains('wide-mode') && wrapper && !wrapper.classList.contains('tab-hidden')) return;
                        var group = header.closest('.word-group');
                        if (group) group.classList.toggle('collapsed');
                    });
                });
                initCollapseVisibility();
            }

            function initCollapseVisibility() {
                var headers = document.querySelectorAll('.word-header');
                var wrapper = document.querySelector('.tab-bar-wrapper');
                var isTabMode = document.body.classList.contains('wide-mode') && wrapper && !wrapper.classList.contains('tab-hidden');
                headers.forEach(function(h) {
                    if (isTabMode) { h.classList.remove('collapsible'); }
                    else { h.classList.add('collapsible'); }
                });
                if (isTabMode) {
                    document.querySelectorAll('.word-group.collapsed').forEach(function(g) {
                        g.classList.remove('collapsed');
                    });
                }
            }

            // 独立展示区 Tab 切换
            function initStandaloneTabs() {
                var tabBar = document.querySelector('.standalone-tab-bar');
                if (!tabBar) return;
                var groups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
                var btns = tabBar.querySelectorAll('.tab-btn[data-standalone-tab]');
                initTabScroll(tabBar);

                function activateStandaloneTab(val) {
                    btns.forEach(function(b) {
                        var bVal = b.getAttribute('data-standalone-tab');
                        b.classList.toggle('active', bVal === String(val));
                    });
                    groups.forEach(function(g) {
                        var gVal = g.getAttribute('data-standalone-tab');
                        g.style.display = (val === 'all' || gVal === String(val)) ? '' : 'none';
                    });
                }

                btns.forEach(function(btn) {
                    btn.addEventListener('click', function() {
                        activateStandaloneTab(btn.getAttribute('data-standalone-tab'));
                    });
                });

                // 初始状态
                initStandaloneTabVisibility();
            }

            function initStandaloneTabVisibility() {
                var tabBar = document.querySelector('.standalone-tab-bar');
                if (!tabBar) return;
                var groups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
                var isWide = document.body.classList.contains('wide-mode');
                if (!isWide || groups.length <= 1) {
                    tabBar.classList.add('tab-hidden');
                    groups.forEach(function(g) { g.style.display = ''; });
                } else {
                    tabBar.classList.remove('tab-hidden');
                    var activeBtn = tabBar.querySelector('.tab-btn.active');
                    if (activeBtn) activeBtn.click();
                    else { var first = tabBar.querySelector('.tab-btn'); if (first) first.click(); }
                }
            }

            function prepareForScreenshot() {
                var state = {
                    wasWide: document.body.classList.contains('wide-mode'),
                    hiddenGroups: []
                };
                document.body.classList.remove('wide-mode');
                state.wasDark = document.body.classList.contains('dark-mode');
                document.body.classList.remove('dark-mode');
                document.querySelectorAll('.word-group[data-tab-index]').forEach(function(g, i) {
                    if (g.style.display === 'none') {
                        state.hiddenGroups.push(i);
                        g.style.display = '';
                    }
                });
                state.hiddenStandaloneGroups = [];
                document.querySelectorAll('.standalone-group[data-standalone-tab]').forEach(function(g, i) {
                    if (g.style.display === 'none') {
                        state.hiddenStandaloneGroups.push(i);
                        g.style.display = '';
                    }
                });
                document.querySelectorAll('.tab-bar-wrapper, .standalone-tab-bar, .search-bar, .fab-bar, .toggle-wide-btn').forEach(function(el) {
                    el.dataset.prevDisplay = el.style.display || '';
                    el.style.display = 'none';
                });
                document.querySelectorAll('.toggle-dark-btn').forEach(function(el) {
                    el.dataset.prevDisplay = el.style.display || ''; el.style.display = 'none';
                });
                document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = 'none'; });
                document.querySelectorAll('.header-watermark').forEach(function(el) { el.style.display = 'none'; });
                return state;
            }

            function restoreAfterScreenshot(state) {
                if (state.wasWide) document.body.classList.add('wide-mode');
                if (state.wasDark) document.body.classList.add('dark-mode');
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                state.hiddenGroups.forEach(function(i) {
                    if (groups[i]) groups[i].style.display = 'none';
                });
                var standaloneGroups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
                if (state.hiddenStandaloneGroups) {
                    state.hiddenStandaloneGroups.forEach(function(i) {
                        if (standaloneGroups[i]) standaloneGroups[i].style.display = 'none';
                    });
                }
                document.querySelectorAll('.tab-bar-wrapper, .standalone-tab-bar, .search-bar, .fab-bar, .toggle-wide-btn').forEach(function(el) {
                    el.style.display = el.dataset.prevDisplay || '';
                    delete el.dataset.prevDisplay;
                });
                document.querySelectorAll('.toggle-dark-btn').forEach(function(el) {
                    el.style.display = el.dataset.prevDisplay || ''; delete el.dataset.prevDisplay;
                });
                document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = ''; });
                document.querySelectorAll('.header-watermark').forEach(function(el) { el.style.display = ''; });
                initTabVisibility();
                initCollapseVisibility();
                initStandaloneTabVisibility();
                var fabBar = document.querySelector('.fab-bar');
                if (fabBar && window.scrollY > 300) fabBar.classList.add('visible');
            }

            // ===== 截图功能 =====

            async function saveAsImage(e) {
                const button = e.target.closest('.save-dropdown-item') || e.target;
                const originalHTML = button.innerHTML;
                var screenshotState = null;

                try {
                    button.textContent = '生成中...';
                    button.disabled = true;
                    window.scrollTo(0, 0);

                    // 等待页面稳定
                    await new Promise(resolve => setTimeout(resolve, 200));

                    // 截图前准备：切回窄屏布局
                    screenshotState = prepareForScreenshot();

                    // 截图前隐藏按钮
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // 再次等待确保按钮完全隐藏
                    await new Promise(resolve => setTimeout(resolve, 100));

                    const container = document.querySelector('.container');

                    const canvas = await html2canvas(container, {
                        backgroundColor: '#ffffff',
                        scale: 1.5,
                        useCORS: true,
                        allowTaint: false,
                        imageTimeout: 10000,
                        removeContainer: false,
                        foreignObjectRendering: false,
                        logging: false,
                        width: container.offsetWidth,
                        height: container.offsetHeight,
                        x: 0,
                        y: 0,
                        scrollX: 0,
                        scrollY: 0,
                        windowWidth: window.innerWidth,
                        windowHeight: window.innerHeight
                    });

                    buttons.style.visibility = 'visible';
                    restoreAfterScreenshot(screenshotState);

                    const link = document.createElement('a');
                    const now = new Date();
                    const filename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.png`;

                    link.download = filename;
                    link.href = canvas.toDataURL('image/png', 1.0);

                    // 触发下载
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);

                    button.textContent = '保存成功!';
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);

                } catch (error) {
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    if (screenshotState) { restoreAfterScreenshot(screenshotState); }
                    button.textContent = '保存失败';
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);
                }
            }

            async function saveAsMultipleImages(e) {
                const button = e.target.closest('.save-dropdown-item') || e.target;
                const originalHTML = button.innerHTML;
                const container = document.querySelector('.container');
                const scale = 1.5;
                const maxHeight = 5000 / scale;
                var screenshotState2 = null;

                try {
                    screenshotState2 = prepareForScreenshot();
                    button.textContent = '分析中...';
                    button.disabled = true;

                    // 获取所有可能的分割元素
                    const newsItems = Array.from(container.querySelectorAll('.news-item'));
                    const wordGroups = Array.from(container.querySelectorAll('.word-group'));
                    const newSection = container.querySelector('.new-section');
                    const errorSection = container.querySelector('.error-section');
                    const header = container.querySelector('.header');
                    const footer = container.querySelector('.footer');

                    // 计算元素位置和高度
                    const containerRect = container.getBoundingClientRect();
                    const elements = [];

                    // 添加header作为必须包含的元素
                    elements.push({
                        type: 'header',
                        element: header,
                        top: 0,
                        bottom: header.offsetHeight,
                        height: header.offsetHeight
                    });

                    // 添加错误信息（如果存在）
                    if (errorSection) {
                        const rect = errorSection.getBoundingClientRect();
                        elements.push({
                            type: 'error',
                            element: errorSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }

                    // 按word-group分组处理news-item
                    wordGroups.forEach(group => {
                        const groupRect = group.getBoundingClientRect();
                        const groupNewsItems = group.querySelectorAll('.news-item');

                        // 添加word-group的header部分
                        const wordHeader = group.querySelector('.word-header');
                        if (wordHeader) {
                            const headerRect = wordHeader.getBoundingClientRect();
                            elements.push({
                                type: 'word-header',
                                element: wordHeader,
                                parent: group,
                                top: groupRect.top - containerRect.top,
                                bottom: headerRect.bottom - containerRect.top,
                                height: headerRect.height
                            });
                        }

                        // 添加每个news-item
                        groupNewsItems.forEach(item => {
                            const rect = item.getBoundingClientRect();
                            elements.push({
                                type: 'news-item',
                                element: item,
                                parent: group,
                                top: rect.top - containerRect.top,
                                bottom: rect.bottom - containerRect.top,
                                height: rect.height
                            });
                        });
                    });

                    // 添加新增新闻部分
                    if (newSection) {
                        const rect = newSection.getBoundingClientRect();
                        elements.push({
                            type: 'new-section',
                            element: newSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }

                    // 添加footer
                    const footerRect = footer.getBoundingClientRect();
                    elements.push({
                        type: 'footer',
                        element: footer,
                        top: footerRect.top - containerRect.top,
                        bottom: footerRect.bottom - containerRect.top,
                        height: footer.offsetHeight
                    });

                    // 计算分割点
                    const segments = [];
                    let currentSegment = { start: 0, end: 0, height: 0, includeHeader: true };
                    let headerHeight = header.offsetHeight;
                    currentSegment.height = headerHeight;

                    for (let i = 1; i < elements.length; i++) {
                        const element = elements[i];
                        const potentialHeight = element.bottom - currentSegment.start;

                        // 检查是否需要创建新分段
                        if (potentialHeight > maxHeight && currentSegment.height > headerHeight) {
                            // 在前一个元素结束处分割
                            currentSegment.end = elements[i - 1].bottom;
                            segments.push(currentSegment);

                            // 开始新分段
                            currentSegment = {
                                start: currentSegment.end,
                                end: 0,
                                height: element.bottom - currentSegment.end,
                                includeHeader: false
                            };
                        } else {
                            currentSegment.height = potentialHeight;
                            currentSegment.end = element.bottom;
                        }
                    }

                    // 添加最后一个分段
                    if (currentSegment.height > 0) {
                        currentSegment.end = container.offsetHeight;
                        segments.push(currentSegment);
                    }

                    button.textContent = `生成中 (0/${segments.length})...`;

                    // 隐藏保存按钮
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // 为每个分段生成图片
                    const images = [];
                    for (let i = 0; i < segments.length; i++) {
                        const segment = segments[i];
                        button.textContent = `生成中 (${i + 1}/${segments.length})...`;

                        // 创建临时容器用于截图
                        const tempContainer = document.createElement('div');
                        tempContainer.style.cssText = `
                            position: absolute;
                            left: -9999px;
                            top: 0;
                            width: ${container.offsetWidth}px;
                            background: white;
                        `;
                        tempContainer.className = 'container';

                        // 克隆容器内容
                        const clonedContainer = container.cloneNode(true);

                        // 移除克隆内容中的保存按钮
                        const clonedButtons = clonedContainer.querySelector('.save-buttons');
                        if (clonedButtons) {
                            clonedButtons.style.display = 'none';
                        }

                        tempContainer.appendChild(clonedContainer);
                        document.body.appendChild(tempContainer);

                        // 等待DOM更新
                        await new Promise(resolve => setTimeout(resolve, 100));

                        // 使用html2canvas截取特定区域
                        const canvas = await html2canvas(clonedContainer, {
                            backgroundColor: '#ffffff',
                            scale: scale,
                            useCORS: true,
                            allowTaint: false,
                            imageTimeout: 10000,
                            logging: false,
                            width: container.offsetWidth,
                            height: segment.end - segment.start,
                            x: 0,
                            y: segment.start,
                            windowWidth: window.innerWidth,
                            windowHeight: window.innerHeight
                        });

                        images.push(canvas.toDataURL('image/png', 1.0));

                        // 清理临时容器
                        document.body.removeChild(tempContainer);
                    }

                    // 恢复按钮显示
                    buttons.style.visibility = 'visible';

                    // 下载所有图片
                    const now = new Date();
                    const baseFilename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;

                    for (let i = 0; i < images.length; i++) {
                        const link = document.createElement('a');
                        link.download = `${baseFilename}_part${i + 1}.png`;
                        link.href = images[i];
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);

                        // 延迟一下避免浏览器阻止多个下载
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }

                    button.textContent = `已保存 ${segments.length} 张图片!`;
                    restoreAfterScreenshot(screenshotState2);
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);

                } catch (error) {
                    console.error('分段保存失败:', error);
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    if (screenshotState2) { restoreAfterScreenshot(screenshotState2); }
                    button.textContent = '保存失败';
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);
                }
            }

            function saveAsMarkdown() {
                var lines = [];
                var now = new Date();
                var dateStr = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
                var timeStr = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');

                // 标题
                var headerTitle = document.querySelector('.header-title');
                lines.push('# ' + (headerTitle ? headerTitle.textContent.trim() : 'TrendRadar'));
                lines.push('');

                // 报告元信息
                var infoItems = document.querySelectorAll('.header-info .info-item');
                if (infoItems.length) {
                    infoItems.forEach(function(item) {
                        var label = item.querySelector('.info-label');
                        var value = item.querySelector('.info-value');
                        if (label && value) {
                            lines.push('- **' + label.textContent.trim() + '**: ' + value.textContent.trim());
                        }
                    });
                    lines.push('');
                }

                // 提取 news-item 通用函数
                function extractItem(item, idx) {
                    var titleEl = item.querySelector('.news-title a');
                    var titleText = '';
                    var url = '';
                    if (titleEl) {
                        titleText = titleEl.textContent.trim();
                        url = titleEl.href || '';
                    } else {
                        var titleDiv = item.querySelector('.news-title') || item.querySelector('.new-item-title');
                        if (titleDiv) titleText = titleDiv.textContent.trim();
                    }
                    if (!titleText) return '';

                    var meta = [];
                    var rank = item.querySelector('.rank-num, .new-item-rank');
                    if (rank && rank.textContent.trim() && rank.textContent.trim() !== '?') meta.push('#' + rank.textContent.trim());
                    var source = item.querySelector('.source-name');
                    if (source) meta.push(source.textContent.trim());
                    var keyword = item.querySelector('.keyword-tag');
                    if (keyword) meta.push(keyword.textContent.trim());
                    var time = item.querySelector('.time-info');
                    if (time) meta.push(time.textContent.trim());
                    var count = item.querySelector('.count-info');
                    if (count) meta.push(count.textContent.trim());

                    var line = idx + '. ';
                    if (url) {
                        line += '[' + titleText.replace(/[[\\]]/g, '') + '](' + url + ')';
                    } else {
                        line += titleText;
                    }
                    if (meta.length) line += '  `' + meta.join(' | ') + '`';
                    return line;
                }

                // 热点关键词区
                var wordGroups = document.querySelectorAll('.hotlist-section > .word-group');
                if (wordGroups.length) {
                    lines.push('## 热点新闻');
                    lines.push('');
                    wordGroups.forEach(function(group) {
                        var wordName = group.querySelector('.word-name');
                        var wordCount = group.querySelector('.word-count');
                        if (wordName) {
                            lines.push('### ' + wordName.textContent.trim() + (wordCount ? ' (' + wordCount.textContent.trim() + ')' : ''));
                            lines.push('');
                        }
                        var items = group.querySelectorAll('.news-item');
                        items.forEach(function(item, i) {
                            var line = extractItem(item, i + 1);
                            if (line) lines.push(line);
                        });
                        lines.push('');
                    });
                }

                // 新增热点区
                var newSection = document.querySelector('.new-section');
                if (newSection) {
                    var newTitle = newSection.querySelector('.new-section-title');
                    lines.push('## ' + (newTitle ? newTitle.textContent.trim() : '本次新增热点'));
                    lines.push('');
                    var sourceGroups = newSection.querySelectorAll('.new-source-group');
                    sourceGroups.forEach(function(sg) {
                        var srcTitle = sg.querySelector('.new-source-title');
                        if (srcTitle) {
                            lines.push('### ' + srcTitle.textContent.trim());
                            lines.push('');
                        }
                        var items = sg.querySelectorAll('.new-item');
                        items.forEach(function(item, i) {
                            var line = extractItem(item, i + 1);
                            if (line) lines.push(line);
                        });
                        lines.push('');
                    });
                }

                // RSS 订阅更新区
                var rssSection = document.querySelector('.rss-section');
                if (rssSection) {
                    var rssSectionTitle = rssSection.querySelector('.rss-section-title');
                    lines.push('## ' + (rssSectionTitle ? rssSectionTitle.textContent.trim() : 'RSS 订阅更新'));
                    lines.push('');
                    var feedGroups = rssSection.querySelectorAll('.feed-group');
                    feedGroups.forEach(function(group) {
                        var feedName = group.querySelector('.feed-name');
                        var feedCount = group.querySelector('.feed-count');
                        if (feedName) {
                            lines.push('### ' + feedName.textContent.trim() + (feedCount ? ' (' + feedCount.textContent.trim() + ')' : ''));
                            lines.push('');
                        }
                        var items = group.querySelectorAll('.rss-item');
                        items.forEach(function(item, i) {
                            var titleEl = item.querySelector('.rss-title a');
                            var titleText = titleEl ? titleEl.textContent.trim() : '';
                            var url = titleEl ? (titleEl.href || '') : '';
                            if (!titleText) return;
                            var meta = [];
                            var time = item.querySelector('.rss-time');
                            if (time) meta.push(time.textContent.trim());
                            var author = item.querySelector('.rss-author');
                            if (author) meta.push(author.textContent.trim());
                            var line = (i + 1) + '. ';
                            if (url) { line += '[' + titleText.replace(/[\\[\\]]/g, '') + '](' + url + ')'; }
                            else { line += titleText; }
                            if (meta.length) line += '  `' + meta.join(' | ') + '`';
                            lines.push(line);
                        });
                        lines.push('');
                    });
                }

                // AI 热点分析区
                var aiSection = document.querySelector('.ai-section');
                if (aiSection) {
                    var aiError = aiSection.querySelector('.ai-error') || aiSection.querySelector('.ai-warning');
                    var aiInfo = aiSection.querySelector('.ai-info');
                    if (aiError) {
                        lines.push('## AI 分析');
                        lines.push('');
                        lines.push('> ' + aiError.textContent.trim());
                        lines.push('');
                    } else if (aiInfo) {
                        // 跳过 info 提示（如"跳过"）
                    } else {
                        var aiTitle = aiSection.querySelector('.ai-section-title');
                        lines.push('## ' + (aiTitle ? aiTitle.textContent.trim() : 'AI 热点分析'));
                        lines.push('');
                        var aiBlocks = aiSection.querySelectorAll('.ai-block');
                        aiBlocks.forEach(function(block) {
                            var blockTitle = block.querySelector('.ai-block-title');
                            var blockContent = block.querySelector('.ai-block-content');
                            if (blockTitle) {
                                lines.push('### ' + blockTitle.textContent.trim());
                                lines.push('');
                            }
                            if (blockContent) {
                                lines.push(blockContent.textContent.trim());
                                lines.push('');
                            }
                        });
                    }
                }

                // 独立展示区（热榜平台 + RSS）
                var standaloneSection = document.querySelector('.standalone-section');
                if (standaloneSection) {
                    var standaloneTitle = standaloneSection.querySelector('.standalone-section-title');
                    lines.push('## ' + (standaloneTitle ? standaloneTitle.textContent.trim() : '独立展示区'));
                    lines.push('');
                    var groups = standaloneSection.querySelectorAll('.standalone-group');
                    groups.forEach(function(group) {
                        var name = group.querySelector('.standalone-name');
                        var cnt = group.querySelector('.standalone-count');
                        if (name) {
                            lines.push('### ' + name.textContent.trim() + (cnt ? ' (' + cnt.textContent.trim() + ')' : ''));
                            lines.push('');
                        }
                        var items = group.querySelectorAll('.news-item');
                        items.forEach(function(item, i) {
                            var line = extractItem(item, i + 1);
                            if (line) lines.push(line);
                        });
                        lines.push('');
                    });
                }

                // 错误区
                var errorSection = document.querySelector('.error-section');
                if (errorSection) {
                    var errorItems = errorSection.querySelectorAll('.error-item');
                    if (errorItems.length) {
                        lines.push('## 抓取异常');
                        lines.push('');
                        errorItems.forEach(function(item) {
                            lines.push('- ' + item.textContent.trim());
                        });
                        lines.push('');
                    }
                }

                // 页脚
                lines.push('---');
                lines.push('*Generated by TrendRadar*');

                // 下载
                var md = lines.join('\\n');
                var blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
                var link = document.createElement('a');
                var filename = 'TrendRadar_' + dateStr + '_' + timeStr.replace(':', '') + '.md';
                link.download = filename;
                link.href = URL.createObjectURL(blob);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(link.href);
            }

            document.addEventListener('DOMContentLoaded', function() {
                window.scrollTo(0, 0);

                // 自动检测宽屏模式
                var savedMode = null;
                try { savedMode = localStorage.getItem('trendradar-wide-mode'); } catch(e) {}
                if (savedMode === '1' || (savedMode === null && window.innerWidth > 768)) {
                    document.body.classList.add('wide-mode');
                    var btn = document.querySelector('.toggle-wide-btn');
                    if (btn) btn.textContent = '📱 手机版';
                } else {
                    var btnNarrow = document.querySelector('.toggle-wide-btn');
                    if (btnNarrow) btnNarrow.textContent = '🖥️ 电脑版';
                }

                // 暗色模式恢复
                var savedDark = null;
                try { savedDark = localStorage.getItem('trendradar-dark-mode'); } catch(e) {}
                if (savedDark === '1') {
                    document.body.classList.add('dark-mode');
                    var darkBtn = document.querySelector('.toggle-dark-btn');
                    if (darkBtn) darkBtn.textContent = '☀';
                }

                // 行业动态子页签：点击筛选该分区内的词组
                document.querySelectorAll('.ind-tabbar').forEach(function(bar) {
                    bar.addEventListener('click', function(e) {
                        var btn = e.target.closest('.ind-tab');
                        if (!btn) return;
                        bar.querySelectorAll('.ind-tab').forEach(function(b) { b.classList.remove('active'); });
                        btn.classList.add('active');
                        var zone = bar.closest('.zone');
                        var v = btn.dataset.ind;
                        zone.querySelectorAll('.word-group[data-ind-idx]').forEach(function(g) {
                            g.style.display = (v === 'all' || g.dataset.indIdx === v) ? '' : 'none';
                        });
                    });
                });

                // 历史报告导航：按当前部署位置计算相对路径后显示
                var histNav = document.querySelector('.history-nav');
                if (histNav) {
                    var p = location.pathname;
                    var prefix;
                    if (/\\/html\\/[^/]+\\/[^/]+\\.html$/.test(p)) {
                        prefix = '../';            // 位于 output/html/<日期>/ 或 html/latest/ 内
                    } else if (/\\/output\\/(index\\.html)?$/.test(p)) {
                        prefix = 'html/';          // 位于 output/index.html
                    } else {
                        prefix = 'output/html/';   // 位于仓库根 index.html（GitHub Pages 入口）
                    }
                    histNav.querySelectorAll('.history-chip[data-hist-date]').forEach(function(chip) {
                        chip.href = prefix + encodeURIComponent(chip.dataset.histDate) + '/' + encodeURIComponent(chip.dataset.histFile);
                    });
                    var managerChip = histNav.querySelector('[data-manager-link]');
                    if (managerChip) managerChip.href = prefix + 'manager.html';
                    // 「最新报告」入口：仅在浏览历史快照时显示，永远指向根 index.html
                    var latestChip = histNav.querySelector('[data-latest-link]');
                    if (latestChip) {
                        var snapMatch = p.match(/^(.*?)(?:output\\/)?html\\/[^/]+\\/[^/]+\\.html$/);
                        if (snapMatch) {
                            latestChip.href = snapMatch[1] + 'index.html';
                            latestChip.style.display = '';
                        }
                    }
                    histNav.style.display = 'flex';
                }

                // 启用搜索栏
                var searchBar = document.querySelector('.search-bar');
                if (searchBar) searchBar.style.display = 'block';

                // 显示顶部工具按钮（导出/手机版/暗色）——邮件客户端无 JS，保持隐藏
                var saveButtons = document.querySelector('.save-buttons');
                if (saveButtons) saveButtons.style.display = 'flex';

                // 初始化增强功能
                initTabs();
                initBackToTop();
                initCollapse();
                initStandaloneTabs();

                // 键盘快捷键
                document.addEventListener('keydown', function(e) {
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
                    var helpBtn = document.querySelector('.fab-help');
                    switch(e.key) {
                        case '?':
                            if (helpBtn) {
                                helpBtn.classList.toggle('show-tip');
                                var fabBar = document.querySelector('.fab-bar');
                                if (fabBar) fabBar.classList.add('visible');
                            }
                            break;
                        case 'Escape':
                            if (helpBtn) helpBtn.classList.remove('show-tip');
                            break;
                        case 'w': case 'W': toggleWideMode(); break;
                        case 'd': case 'D': toggleDarkMode(); break;
                        case '/': e.preventDefault(); var si = document.querySelector('.search-input'); if (si) si.focus(); break;
                    }
                });

                // 阅读进度条
                var progressBar = document.querySelector('.reading-progress');
                if (progressBar) {
                    var progressTicking = false;
                    window.addEventListener('scroll', function() {
                        if (!progressTicking) {
                            requestAnimationFrame(function() {
                                var h = document.documentElement.scrollHeight - window.innerHeight;
                                progressBar.style.width = (h > 0 ? (window.scrollY / h * 100) : 0) + '%';
                                progressTicking = false;
                            });
                            progressTicking = true;
                        }
                    });
                }

                // 一键复制：hover 时数字变复制图标
                var copySvg = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M5 11H3.5A1.5 1.5 0 012 9.5v-7A1.5 1.5 0 013.5 1h7A1.5 1.5 0 0112 2.5V5"/></svg>';
                var checkSvg = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="#22c55e" stroke-width="2"><path d="M3 8.5l3.5 3.5 7-7"/></svg>';
                document.querySelectorAll('.news-item .news-number').forEach(function(numEl) {
                    var item = numEl.closest('.news-item');
                    var titleEl = item ? item.querySelector('.news-title a') : null;
                    if (!titleEl) return;
                    var numText = numEl.textContent.trim();
                    numEl.innerHTML = '<span class="num-text">' + numText + '</span><span class="copy-icon">' + copySvg + '</span>';
                    numEl.title = '点击复制标题和链接';
                    numEl.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var text = titleEl.textContent.trim() + ' ' + titleEl.href;
                        function onCopySuccess() {
                            numEl.classList.add('copied');
                            numEl.querySelector('.copy-icon').innerHTML = checkSvg;
                            setTimeout(function() {
                                numEl.classList.remove('copied');
                                numEl.querySelector('.copy-icon').innerHTML = copySvg;
                            }, 1500);
                        }
                        function fallbackCopy(str, cb) {
                            var ta = document.createElement('textarea');
                            ta.value = str; ta.style.position = 'fixed'; ta.style.opacity = '0';
                            document.body.appendChild(ta); ta.select();
                            try { document.execCommand('copy'); cb(); } catch(ex) {}
                            document.body.removeChild(ta);
                        }
                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            navigator.clipboard.writeText(text).then(onCopySuccess).catch(function() {
                                fallbackCopy(text, onCopySuccess);
                            });
                        } else {
                            fallbackCopy(text, onCopySuccess);
                        }
                    });
                });



                // Header watermark 鼠标跟随揭示
                (function() {
                    var header = document.querySelector('.header');
                    var watermark = document.querySelector('.header-watermark');
                    if (!header || !watermark) return;

                    var radius = 100;

                    header.addEventListener('mousemove', function(e) {
                        var rect = watermark.getBoundingClientRect();
                        var x = e.clientX - rect.left;
                        var y = e.clientY - rect.top;
                        var maskVal = 'radial-gradient(circle ' + radius + 'px at ' + x + 'px ' + y + 'px, rgba(0,0,0,1) 0%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0) 100%)';
                        watermark.style.webkitMaskImage = maskVal;
                        watermark.style.maskImage = maskVal;
                        watermark.style.color = 'rgba(255, 255, 255, 0.25)';
                    });

                    header.addEventListener('mouseleave', function() {
                        watermark.style.webkitMaskImage = 'radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)';
                        watermark.style.maskImage = 'radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)';
                        watermark.style.color = 'rgba(255, 255, 255, 0.15)';
                    });
                })();
            });
        </script>
    </body>
    </html>
    """

    return html
