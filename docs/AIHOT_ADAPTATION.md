# AIHOT 机制适配与信源清单

本分支从 `cfo-intelligence-v2` 分出，**不覆盖 master 或原分支**。借鉴 [AIHOT](https://github.com/KKKKhazix/AIHOT) 的预筛、两次独立注意力评分、事件聚簇和合并复核思路；实现为本项目现有 Python + GitHub Actions + 静态 HTML 流水线，并非完整搬运 AIHOT 的 TypeScript/PostgreSQL 网站。

AIHOT 公开仓库明确说明：线上完整信源清单与运营数据**没有开源**；`industry/sources.json` 只提供 18 个海外 AI 示范 RSS。因此下表就是可直接沿用的**全部公开示范 RSS**，不是 AIHOT 线上全部热源。具体源以其 [原始配置](https://github.com/KKKKhazix/AIHOT/blob/main/industry/sources.json) 为准。

| 级别 | 来源 | RSS URL |
| --- | --- | --- |
| T1 | OpenAI News | https://openai.com/news/rss.xml |
| T1 | Google DeepMind | https://deepmind.google/blog/rss.xml |
| T1 | Google Research | https://research.google/blog/rss/ |
| T1 | Hugging Face Blog | https://huggingface.co/blog/feed.xml |
| T1 | Microsoft Research | https://www.microsoft.com/en-us/research/feed/ |
| T1 | NVIDIA Blog | https://blogs.nvidia.com/feed/ |
| T1 | AWS Machine Learning Blog | https://aws.amazon.com/blogs/machine-learning/feed/ |
| T1 | GitHub Blog · AI & ML | https://github.blog/ai-and-ml/feed/ |
| T1 | Mistral AI | https://mistral.ai/news/rss |
| T1 | Berkeley AI Research | https://bair.berkeley.edu/blog/feed.xml |
| T2 | The Verge · AI | https://www.theverge.com/rss/ai-artificial-intelligence/index.xml |
| T2 | TechCrunch · AI | https://techcrunch.com/category/artificial-intelligence/feed/ |
| T2 | Ars Technica · AI | https://arstechnica.com/ai/feed/ |
| T2 | MIT Technology Review · AI | https://www.technologyreview.com/topic/artificial-intelligence/feed |
| T2 | The Decoder | https://the-decoder.com/feed/ |
| T2 | Simon Willison | https://simonwillison.net/atom/everything/ |
| T2 | Import AI | https://importai.substack.com/feed |
| T2 | Latent Space | https://www.latent.space/feed |

这 18 个 RSS 已纳入 `config/config.yaml`。为避免客户监控失焦，保留 IT之家、机器之心、量子位、InfoQ 等中文源、NVIDIA Developer 原有技术博客、原有财经/科技热榜，以及原本的 Anthropic 非官方镜像。移除上次实跑出现持续错误的 36氪、虎嗅、Yahoo RSS 和 VentureBeat。2026-10-31 在本机对 18 个示范地址做了 10 秒连通性探测，13 个返回 HTTP 200，5 个超时（NVIDIA Blog、Google Research、Hugging Face、Mistral、Import AI）；超时不等于源失效，GitHub Actions 的网络结果可能不同。抓取失败会单独记录，不阻断其他源。

## 22 组公司监控

正式名单仍以 `config/frequency_words.txt` 的「公司监控」为准：工商银行、中国银行、建设银行、农业银行、邮储银行、招商银行、交通银行、中信集团、税务总局、国家电网、南方电网、国铁集团、中国石油、美团、腾讯、字节跳动、沙特电力、NEOM、墨西哥联邦电力、星展银行、大众汽车、埃及国防部。测试会检查组数为 22，防止改源时漏掉公司。

但这不等于“互联网上这 22 家的新闻均已抓全”：AIHOT 的海外 AI RSS 本身几乎不覆盖银行、电力、铁路、石油、海外政企客户。当前仍依赖原有财经热榜、中文 RSS 与关键词匹配。后续若追求更高召回率，应逐家加入可验证的官网公告、招采/投资者关系源或付费数据库，不能仅靠新增英文 AI RSS 保证覆盖。

## 阅读与成本口径

候选来自本轮已经按关键词/AI 兴趣筛过的资讯。两次评分在相同规则下分别请求模型，规则明确以**公司发生的实质事件**为主，纯论文、教程和例行技术更新低分。页首候选与精选位置原则上 75% 留给 22 组公司；公司新闻平均分至少 55，AI 行业新闻仅在影响客户采购或商业格局时入选（T1 官方源至少 70，T2 媒体源至少 80）。低分公司条目不会从完整监控区删除，只是不占页首阅读位置。聚簇把同一事件的不同报道合成一个阅读位置，再独立复核合并；复核失败时拆开，避免误并。网页页首显示平均分、事件摘要和所有可点击的来源，下方的公司/行业详情保持原样。若模型故障则不做分数筛选，用保守标题相似度聚簇并标注回退。

每轮最多评分 60 条候选，默认显示最多 16 个事件，正常情况下约增加 4 次模型请求。该机制不改变每天晨间/晚间的发送时刻，也不把 48 小时热度指数伪装成 24 小时晨报的分数。

AIHOT 代码使用 [MIT 许可](https://github.com/KKKKhazix/AIHOT/blob/main/LICENSE)；本项目没有使用 AIHOT 的名字、Logo 或字体资产。
