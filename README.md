# 回复军师 ——新手人类社会化指北

​     这里是徐欣睿的人机交互课程大项目。

​     这是一个面向不同聊天场景的回复辅助工具。在面对心动对象、导师、面试官、长辈这类容易使人不知所措的对话里，军师帮你解读对方消息里的潜台词、估一估翻车风险，再结合你和对方的性格，生成几档不同语气的得体回复；也可以把自己想发的草稿丢进来让它点评。同时，存档功能赋予其结构化存储对话对象的能力，随着文本量和上下文的积累，军师可以随时完善调整双方画像，也可以判断聊天状态和当前需要注意的问题。

---

## 一、技术栈

- 后端：Python 3.9 + FastAPI + Uvicorn
- 存储：SQLite（标准库 `sqlite3`，零额外依赖，运行时自动建库）
- 前端：原生 HTML / CSS / JavaScript（无前端框架，无需构建）
- 生成引擎：以**大模型（LLM）为核心**
  - **LLM 引擎**：配置 API Key 后由大模型生成回复，是产品的真实运行模式
  - **离线规则引擎**：仅作断网/异常时的兜底，输出为模板化结果，不代表真实效果

> ⚠️ 本项目是 AI 生成应用，**运行前需要配置一个大模型 API Key**（见「四、配置 API Key」）。
> 未配置时系统会回退到离线规则引擎，仅能展示界面与流程，回复内容是占位模板。

---

## 二、目录结构

```
.
├── backend/              后端
│   ├── main.py           FastAPI 入口，定义所有 API 路由 + 托管前端静态文件
│   ├── engine.py         回复生成引擎（离线规则 + LLM 双模式）
│   ├── personas.py       场景定义、性格滑轨维度、画像描述生成
│   └── db.py             SQLite 读写（历史记录 + 聊天归档，支持分页）
├── frontend/             前端（被后端静态托管，无需单独启动）
│   ├── index.html
│   ├── style.css
│   └── app.js
├── seed_demo.py          演示数据脚本：灌入 18 段档案，填满分页
├── test_chat.txt         示例聊天记录，可直接粘贴体验
├── requirements.txt      依赖清单
├── .env.example          环境变量样例（如需启用 LLM 模式时参考）
└── README.md
```

---

## 三、环境要求

- Python 3.9 及以上（开发环境为 3.9.6）
- 依赖见 `requirements.txt`
- 操作系统不限（macOS / Windows / Linux）
- **一个大模型 API Key**（Claude 或阿里云通义千问，二选一）——产品的回复生成依赖它

---

## 四、配置 API Key

本项目的核心是用大模型生成回复，**运行前必须配置一个 API Key**。复制样例文件并填入你的 Key：

```bash
cp .env.example .env
```

然后编辑 `.env`，在下面两种方案里**任选其一**填写（同时填写时优先使用通义千问）：

| 变量 | 说明 |
| --- | --- |
| `ANTHROPIC_API_KEY` | 方案一：启用 Claude 生成 |
| `ANTHROPIC_BASE_URL` | 可选，使用第三方中转时填其 Base URL |
| `ANTHROPIC_MODEL` | 可选，默认 `claude-sonnet-4-6` |
| `DASHSCOPE_API_KEY` | 方案二：启用阿里云通义千问（默认 `qwen-vl-max`，支持截图识别） |

> 启动后首页右上角的引擎角标会显示当前实际使用的引擎。若显示 `offline`，说明 Key 没读到，
> 请检查 `.env` 是否在项目根目录、变量名是否拼对。**离线模式下的回复是占位模板，不是真实生成结果。**

---

## 五、安装与运行

在项目根目录下执行：

```bash
# 1. （建议）创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 确认已按「第四步」配置好 .env，然后启动服务
uvicorn backend.main:app --reload --port 8000
#   或等价地：python3 -m backend.main
```

启动后浏览器打开 **http://localhost:8000** 即可。

---

## 六、灌入演示数据（用于检查分页等功能）

默认数据库是空的。**保持服务在 8000 端口运行**，另开一个终端执行：

```bash
python3 seed_demo.py            # 清空旧档案并灌入 18 段演示档案
python3 seed_demo.py --keep     # 不清空，仅追加
```

灌完后首页档案列表共 18 段、分 3 页（每页 8 条），可用于演示数据过多时的分页展示能力。																																																																																																																																																																					

---

## 七、API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/meta` | 返回场景、关系阶段、性别、语气等元数据 |
| POST | `/api/generate` | 生成回复建议 |
| POST | `/api/summary` | 关系分析 |
| POST | `/api/consult` | 向军师提问咨询 |
| POST | `/api/critique` | 点评用户草稿 |
| POST | `/api/profile` | 生成画像描述 |
| GET | `/api/history` | 历史记录 |
| GET | `/api/archives?page=N&page_size=8` | 分页拉取聊天归档 |
| POST / PUT / DELETE | `/api/archives` | 归档的增改删（含隐藏/恢复） |

---

## 八、核心功能演示路径

1. 打开首页，仪表盘展示「在聊的 / 本周问军师 / 需要关注」三项实时指标
2. 点左上角 ☰ 展开侧边导航（推开式，主内容右移）
3. 进入档案列表，演示分页（每页 8 条，共 3 页）
4. 点首页中央「问一问」→ 选择场景 → 拖动性格滑轨配置画像
5. 填入对方消息 → 生成 3 档不同语气的回复
6. 命名存档 → 返回首页「继续上次」可一键恢复
7. 隐藏 / 恢复档案
8. 切换配色，全站即时生效
