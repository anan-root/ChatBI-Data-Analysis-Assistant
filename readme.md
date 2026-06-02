# ChatBI Data Analysis AI Agent

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Vite-61DAFB?style=flat-square&logo=react&logoColor=111827)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent-1F2937?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-Tooling-7C3AED?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/status-MVP-0EA5E9?style=flat-square)

ChatBI Data Analysis AI Agent 是一个面向企业内部数据分析场景的智能体系统原型。它围绕“上传业务数据、自动清洗、生成独立业务空间、构建诊断型分析报告、通过自然语言问数和追问洞察”这一条主流程，帮助业务人员和数据分析人员降低取数、看数、解释数据和沉淀报告的重复成本。

本项目当前定位为企业内部 MVP：适合用于流程验证、业务样例测试、数据分析助手能力演示和后续产品化开发；不建议在未补齐权限、审计、数据脱敏和生产运维体系前，直接作为正式生产级 BI 系统。

> 安全提醒：真实业务数据、API Key、数据库文件、审计日志、上传文件、生成报告和运行产物不应提交到 Git。公开仓库前请再次检查 `.env`、`.env.docker`、`pgdata/`、`import_jobs/`、`exports/`、`audit_logs/`、`logs/` 和历史提交。

## 项目亮点

- **自然语言问数**：通过大模型理解业务问题，并调用 SQL / Python / 分析工具完成回答。
- **自动导入清洗**：支持 CSV、XLSX、XLS 文件上传，自动处理空值、重复行、字段标准化和类型转换。
- **业务空间管理**：上传数据后自动形成独立业务空间，避免不同业务数据混用。
- **诊断型报告**：报告结构从描述统计升级为「现象 → 对比 → 异常 → 归因假设 → 行动建议」。
- **图表分析**：支持柱形图、折线图、饼图、散点图，并说明每张图回答的业务问题。
- **企业安全治理**：内置只读 SQL 网关、workspace 表/字段白名单、CORS 白名单、Python 执行隔离和审计日志。
- **可选审计落库**：SQL 审计事件默认写入 JSONL，也可同步到 PostgreSQL 审计表。
- **增强 MCP 工具层**：新增业务空间 MCP，可向 Agent 暴露空间列表、字段画像、质量评分、分析方案和报告摘要。
- **Agent 可观测性**：聊天接口返回 `trace` 和 `evidence`，前端可折叠展示意图识别、工具调用、SQL 校验和回答依据。
- **RAG-lite 指标口径**：内置本地指标字典，支持 GMV、销售额、ROI、转化率、留存率等业务口径关键词检索。
- **Text-to-SQL 规则评测**：提供固定评测集和 `/bi/ai-eval` 接口，验证只读 SQL、workspace 范围、字段白名单和未入库拦截。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 智能体编排 | LangGraph |
| 工具协议 | MCP |
| 后端服务 | FastAPI、Uvicorn |
| 前端界面 | React、Vite |
| 数据处理 | pandas、numpy、scipy |
| 数据库 | PostgreSQL |
| 图表 | 轻量 SVG 图表、matplotlib |
| 安全治理 | 只读 SQL、字段白名单、审计日志、CORS 白名单 |
| 知识增强 | 本地指标字典、关键词检索 |
| 测试验证 | pytest、Text-to-SQL 规则样例、Vite build |

## 功能模块

- 数据问答
- 批量导入与自动清洗
- 业务空间
- 业务分析报告
- BI 看板
- 指标体系
- 异常分析
- 用户增长分析
- 变现 / ROI 分析
- SQL 分析模板
- 审计日志
- 业务空间 MCP 工具
- Agent 执行链路
- 回答依据展示
- RAG-lite 指标口径
- AI 评测

## AI 应用能力

### Agent Trace 与 Evidence

`POST /chatbi_service` 保持原有 `message` 字段兼容，同时新增：

- `trace`：记录 traceId、意图、workspace、工具计划、工具结果、SQL 摘要和拦截原因。
- `evidence`：返回当前 workspace、使用字段、SQL 证据和命中的指标口径。

前端聊天消息会在回答下方展示可折叠的「执行链路」和「回答依据」，方便面试或演示时说明 Agent 不是黑盒回答。

### RAG-lite 指标口径

项目内置轻量指标字典：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/knowledge/metric_dictionary.json
```

后端会基于用户问题和 workspace 字段做关键词匹配，将命中的业务口径注入 Agent 上下文，并通过 `/bi/rag` 返回当前可用知识条目。

### Text-to-SQL 规则评测

评测样例位于：

```text
tests/fixtures/text2sql_cases.json
```

`GET /bi/ai-eval` 会返回规则层评测结果，重点验证 SQL 安全和 workspace 边界，不宣称真实模型 SQL 生成准确率。

## 快速启动

### 1. 安装后端依赖

```bash
python -m venv .venv
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量模板：

```powershell
Copy-Item .env.example langGraph_agent/smart_data_analysis_assistant/.env
```

主要配置项：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
QWEN_API_KEY=你的通义千问 API Key

db_host=127.0.0.1
db_port=5432
user=postgres
password=你的数据库密码
dbname=sales_chat

CHATBI_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
CHATBI_ENABLE_PYTHON_EXEC=false
CHATBI_AUDIT_ENABLED=true
CHATBI_USE_POSTGRES_METADATA=false
CHATBI_USE_POSTGRES_AUDIT=false
```

### 3. 启动后端服务

需要分别启动 MCP 服务和主 API：

```bash
cd langGraph_agent/smart_data_analysis_assistant/mcp_server
python ywfl_mcp.py
python python_chart_mcp.py
python machine_learning_mcp.py
python statistic_db_mcp_tools.py
python workspace_mcp.py
```

启动 API：

```bash
cd langGraph_agent/smart_data_analysis_assistant/chatbi_graph
uvicorn chat_api:app --host 0.0.0.0 --port 9008
```

### 4. 启动前端

```bash
cd chatbi-react-ui
npm install
npm run dev
```

浏览器访问：

```text
http://127.0.0.1:5173/
```

## Docker 启动

项目已提供 Docker Compose，适合快速启动完整演示环境：

```bash
cp .env.docker.example .env.docker
docker compose up --build
```

启动后访问：

```text
http://127.0.0.1:5173/
```

Compose 会启动：

- `postgres`：PostgreSQL 数据库
- `backend`：FastAPI + 5 个 MCP 服务
- `workspace_mcp`：业务空间、字段画像、质量评分和报告摘要工具
- `frontend`：React 静态页面 + Nginx 反向代理

停止服务：

```bash
docker compose down
```

如需同时删除 Docker 数据卷：

```bash
docker compose down -v
```

## 验证命令

后端测试：

```bash
python -m pytest tests -q
```

前端构建：

```bash
npm --prefix chatbi-react-ui run build
```

Windows PowerShell 如遇到 npm 脚本执行策略限制，可使用：

```powershell
npm.cmd --prefix chatbi-react-ui run build
```

## 项目文档

- `docs/design_trace.md`：从零开发视角的设计与开发 Trace，详细说明每一步做法、原因、产物，以及 MCP、Agent、RAG 后续设计思路。
- `README_FULL.md`：本地详细架构文档，不上传 GitHub，用于记录完整产品、接口、部署、安全和后续规划。

## 安全说明

- 数据库查询默认只允许 `SELECT / WITH / EXPLAIN`。
- workspace 模式下只能访问当前业务空间的数据表和字段。
- workspace 模式下禁止 `SELECT *`，并校验引用字段是否在当前空间画像中。
- 默认关闭任意 Python 代码执行。
- 审计日志默认写入本地 JSONL，可选同步到 PostgreSQL。
- `/bi/ai-eval` 评测只覆盖规则层安全边界，不代表真实 LLM Text-to-SQL 准确率。
- `.env`、上传数据、日志、PostgreSQL 数据目录和构建产物已通过 `.gitignore` 排除。

## 常见排查

- 前端出现 502：通常是后端、MCP 服务或 PostgreSQL 未启动，先确认 Docker / 本地服务状态。
- Docker PostgreSQL 默认密码来自 `.env.docker`，本地 `.env` 的 `password` 必须和实际数据库密码一致。
- 业务空间显示已入库但查询报表不存在：检查清洗任务是否已执行 `commit`，必要时重新提交入库。
- 使用 Docker 演示时建议先确认 `docker compose ps` 中 `postgres`、`backend`、`frontend` 均为运行状态。

## 项目定位

本项目适合作为：

- ChatBI / AI BI 原型项目
- 企业数据分析助手 Demo
- LangGraph + MCP 工具调用实践
- Agent 可观测性、RAG-lite、Text-to-SQL 安全评测展示
- 数据清洗、业务报告和自然语言问数的一体化样例

## 后续规划

- 审计日志权限体系
- 租户级数据隔离
- 异步导入任务
- 更完整的指标口径管理
- 向量化企业知识库接入
- 更完整的 Text-to-SQL 准确率评测
