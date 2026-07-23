#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 产业情报简报 · 本地预览按钮
#
# 用法：在 Finder 里双击本文件（或终端里 ./本地预览.command）
# 效果：本机抓取一次最新数据 → 生成完整网页报告 → 自动在浏览器打开
#
# 特性：
#   - 绝不发送邮件/推送（ENABLE_NOTIFICATION=false 硬性关闭）
#   - 不受调度时段限制（test_mode：任何时间运行都生成完整报告）
#   - 首次运行会自动创建本地环境并安装依赖（约 2-5 分钟，仅一次）
#   - 想在本地预览里看到 AI 分析：在同目录建一个 .env.local 文件，写入
#         AI_API_KEY=你的key
#         AI_MODEL=模型名
#         AI_ANALYSIS_ENABLED=true
#     （该文件已被 .gitignore 忽略，不会提交到仓库）
# ═══════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"

echo "══════════════════════════════════════"
echo "  产业情报简报 · 本地预览"
echo "══════════════════════════════════════"

# 首次运行：创建本地环境（只装轻量依赖，约 1 分钟）
if [ ! -f .venv-local/bin/python ]; then
  echo "[首次运行] 创建本地 Python 环境并安装依赖（约 1 分钟，仅此一次）..."
  python3 -m venv .venv-local
  .venv-local/bin/pip install -q --upgrade pip
  .venv-local/bin/pip install -q requests pytz PyYAML feedparser json-repair tenacity
  echo "[首次运行] 环境就绪。"
fi

# 可选：加载本地 AI 配置（不存在则跳过，AI 分析显示"待配置"）
if [ -f .env.local ]; then
  set -a; source .env.local; set +a
  echo "[配置] 已加载 .env.local（AI 分析将运行）"
  # AI 调用需要 litellm（体积较大，仅在配置了 AI 时才安装一次）
  if ! .venv-local/bin/python -c "import litellm" 2>/dev/null; then
    echo "[首次 AI] 安装 litellm（约 2-3 分钟，仅此一次）..."
    .venv-local/bin/pip install -q litellm
  fi
else
  echo "[配置] 未找到 .env.local，本次预览不含 AI 分析（页面结构不受影响）"
fi

# 本地预览专用开关
export ENABLE_NOTIFICATION=false   # 硬性禁止发邮件/推送
export SCHEDULE_PRESET=preview_24h # 24h晨报同款配置：daily+跨天回看，不受时段限制

echo "[运行] 抓取数据并生成报告（完成后自动在浏览器打开）..."
.venv-local/bin/python -m trendradar

echo ""
echo "提示：邮件版预览在 output/html/<日期>/ 下的 *.email.html"
echo "　　　订阅管理页在 output/html/manager.html"
read -p "按回车关闭本窗口..."
