# 回复军师 ReplyCoach 🛡️

> 高风险聊天回复助手 —— 在 crush、导师、面试官、长辈这些"一句话定生死"的聊天场景里，
> 帮你解读对方的潜台词、评估翻车风险，并按你和对方的性格生成三档语气的得体回复。

人机交互课程大项目。

## 功能一览

| 模块 | 说明 |
|---|---|
| 🎭 四大高风险场景 | 心动对象 / 导师 / 面试官 / 长辈亲戚 |
| 📷 聊天截图识别 | 点击/拖拽/Ctrl+V 粘贴截图，LLM 模式自动识别对方消息（离线模式优雅降级） |
| 👥 双方性格画像 | 我方 4 种 × 对方 4 种，影响回复风格与策略建议 |
| 🔍 潜台词解读 | 识别「在吗」「呵呵」「改天吧」等信号并给出解读 |
| 🌡️ 翻车风险仪表盘 | 0–100 风险分 + 安全区/谨慎区/高危区 |
| 🗂️ 三档语气回复 | 稳妥 / 自然 / 大胆，每条附表情建议和"为什么这样回" |
| 📱 手机预览 | 发送前在模拟聊天界面里看效果，降低手滑成本 |
| 🕘 历史记录 | SQLite 持久化，可回看、恢复、删除 |
| 🌗 深浅色主题 | 一键切换，本地记忆 |

## 快速开始（零配置，离线可跑）

```bash
cd reply-coach
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

打开 <http://127.0.0.1:8000> 即可。默认使用**离线规则引擎**，不需要任何 API Key，
课堂演示不依赖网络（这同时也是 HCI 方法里的 Wizard-of-Oz 降级路径）。

## 可选：接入 LLM 真实生成

引擎可插拔，**按设置的 Key 自动选择提供方**（DashScope 优先于 Anthropic）：

### A. 阿里通义千问（推荐，国内可直连）

```bash
pip install openai
export DASHSCOPE_API_KEY=sk-xxx           # 阿里云百炼控制台获取
export QWEN_MODEL=qwen-vl-max             # 可选，默认即此（带视觉，支持截图识别）
uvicorn backend.main:app --reload --port 8000
```

Key 获取：登录[阿里云百炼控制台](https://bailian.console.aliyun.com) → API-KEY → 创建。
走的是 DashScope 的 OpenAI 兼容接口，因此用标准 `openai` 库即可，无需额外 SDK。
设置后顶栏徽章变为「🤖 通义千问已连接」。

> 想用纯文本模型（更便宜）可设 `QWEN_MODEL=qwen-plus`，但截图识别需要视觉模型（`qwen-vl-max` / `qwen-vl-plus`）。

### B. Claude（Anthropic 官方或兼容中转）

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export ANTHROPIC_BASE_URL=https://api.anthropic.com  # 第三方中转时改为其 Base URL
export ANTHROPIC_MODEL=claude-sonnet-4-6   # 可选，默认即此
uvicorn backend.main:app --reload --port 8000
```

使用第三方中转时，中转服务需兼容 Anthropic Messages API（`POST /v1/messages`）。
Anthropic SDK 会自动追加 `/v1/messages`，因此 `ANTHROPIC_BASE_URL` 通常只填写域名，
例如 `https://gateway.example.com`，不要在末尾重复填写 `/v1`。

两种引擎任一调用失败（断网、限流、Key 失效），后端都会**自动降级**回离线引擎并在前端提示，演示永不翻车。

## 项目结构

```
reply-coach/
├── backend/
│   ├── main.py        # FastAPI 路由 + 静态文件托管
│   ├── engine.py      # 双引擎：离线规则 / Claude LLM（含潜台词分析、风险评分）
│   ├── personas.py    # 场景、画像、语气档位定义
│   └── db.py          # SQLite 历史记录
├── frontend/
│   ├── index.html     # 单页应用（无构建步骤）
│   ├── style.css      # 设计系统：暗色玻璃拟态 + 浅色主题
│   └── app.js         # 原生 JS 交互逻辑
├── requirements.txt
└── README.md
```

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/meta` | 场景/画像/语气定义 + 当前引擎模式 |
| POST | `/api/generate` | 生成方案：`{scenario, my_persona, their_persona, received, intent}` |
| GET | `/api/history` | 历史记录列表 |
| DELETE | `/api/history/{id}` / `/api/history` | 删除单条 / 清空 |

## 设计决策 ↔ HCI 评分点对照

这些是写进课程报告的素材，每个界面元素都对应一个可论证的设计决策：

- **三档语气而非单一答案** —— 保留用户的自主权（user agency），系统是建议者不是代笔者。
- **风险仪表盘可视化** —— 把抽象的社交焦虑转译为可感知的视觉信号（情感化设计）。
- **军师点评（rationale）** —— 可解释性：告诉用户"为什么这样回"，帮助长期能力养成而非依赖。
- **手机预览** —— 模拟真实发送语境，提供低成本的"反悔机会"（错误预防，Nielsen 启发式 #5）。
- **示例消息一键填入** —— 降低首次使用门槛（recognition rather than recall，启发式 #6）。
- **双引擎 + 自动降级** —— 系统状态可见性（启发式 #1）：顶栏徽章始终如实显示当前引擎。
- **伦理立场内置** —— 界面与提示词中均声明"辅助真诚表达，不教操纵"，这是 HCI 伦理章节的落点。

## 用户测试方案（建议）

情景任务法：给被试一组聊天截图情景（如"导师周五晚上发来『来我办公室一趟』"），
对照组直接回复，实验组使用本工具，测量：

1. 决策时间（从看到消息到确定回复）
2. 回复信心自评（1–7 Likert）
3. 第三方评分员对回复得体度的盲评
