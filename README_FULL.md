# ChatBI 数据分析助手

基于 **LangGraph + MCP + 大模型工具调用** 构建的对话式 BI 数据分析智能体示例项目。用户可以用自然语言完成业务数据查询、统计分析、Python 计算、图表绘制、评论分析和销量预测等任务。

## 项目简介

本项目面向电商业务分析场景，用智能体替代传统「业务提需求 → 数据分析师取数 → 算法/报表交付」的长链路流程。

系统会先识别用户意图，再按任务类型路由到不同能力：

- **纯 Python 编码/计算**：如数学计算、算法代码生成、直接基于给定数据绘图。
- **业务数据查询分析**：如商品销量查询、用户画像分析、评论满意度分析、销量预测。
- **普通对话**：无需工具时直接由大模型回复。

## 核心能力

- 自然语言业务分流：判断用户问题属于 Python 编程还是业务数据分析。
- Text-to-SQL：基于数据库表结构、字段注释生成并执行 SQL。
- NL2Python：生成 Python 脚本并自动执行，返回计算结果或图表路径。
- 图表生成：通过 `matplotlib` 生成统计图并保存到本地。
- 机器学习分析：支持评论满意度分析、评分相关性分析、销量预测。
- LangGraph 流程编排：通过状态图管理多节点、多工具调用流程。
- MCP 工具服务：将数据库查询、Python 执行、机器学习能力拆成独立 MCP Server。
- FastAPI 封装：提供 HTTP 接口供外部系统调用。
- React 工作台：提供浅纸色米白主题、柔和大标题、低对比卡片、可折叠侧边栏、企业级数据问答、分层业务空间、项目组检索、报告封面、看板、指标、异常、增长、变现、导入导出和可选 RAG 模块。

## 技术栈

- **Agent 编排**：LangGraph
- **工具协议**：MCP、langchain-mcp-adapters
- **大模型调用**：DeepSeek、通义千问兼容 OpenAI SDK 接口
- **后端服务**：FastAPI、Uvicorn
- **前端界面**：React、Vite
- **前端可视化**：轻量 SVG 图表组件、lucide-react
- **数据库**：PostgreSQL
- **数据处理**：pandas、numpy、scipy
- **可视化**：matplotlib
- **安全治理**：只读 SQL 网关、workspace 表/字段白名单、CORS 白名单、Python 执行默认关闭、危险输入安全解析
- **审计留痕**：SQL 放行/拦截、越权表引用和 workspace 查询边界写入 JSONL，可选同步到 PostgreSQL 审计表

## 目录结构

```text
.
├── requirements.txt
├── chatbi-react-ui
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src
│       ├── main.jsx
│       └── styles.css
└── langGraph_agent
    ├── project_data
    │   ├── 商品表.xlsx
    │   ├── 用户表.xlsx
    │   ├── 用户活跃表.xlsx
    │   └── 销量表.xlsx
    ├── langGraph_basic_learning
    │   ├── langGraph_code.py
    │   ├── langGraph_practise.py
    │   └── mcp_example_server.py
    └── smart_data_analysis_assistant
        ├── chatbi_graph
        │   ├── build_graph.py
        │   ├── config.py
        │   ├── execute_graph.py
        │   ├── chat_api.py
        │   ├── chat_context.py
        │   ├── my_llm.py
        │   ├── my_state.py
        │   ├── repositories
        │   │   └── database.py
        │   ├── services
        │   │   ├── analysis_utils.py
        │   │   ├── charts.py
        │   │   ├── diagnostics.py
        │   │   ├── exporters.py
        │   │   ├── import_cleaning.py
        │   │   ├── methodology.py
        │   │   ├── profiling.py
        │   │   └── workspace_context.py
        │   └── tools_node.py
        └── mcp_server
            ├── statistic_db_mcp_tools.py
            ├── python_chart_mcp.py
            ├── machine_learning_mcp.py
            ├── ywfl_mcp.py
            ├── multi_mcp_client.py
            └── public_function.py
```

## 整体流程

```text
用户输入
  ↓
LangGraph: call_identify_intention
  ↓
MCP: ywfl_tool 业务分流
  ├── 纯python编码
  │     ↓
  │   run_python_script_tool
  │     ↓
  │   返回代码执行结果或图片路径
  │
  └── 业务数据查询分析
        ↓
      list_tables_tool 获取表结构与字段注释
        ↓
      data_analysis_agent ReAct 子图
        ↓
      按需调用 db_sql_tool / Python 绘图 / 机器学习工具
        ↓
      返回分析结论、查询结果或图表路径
```

## 关键文件说明

| 文件 | 作用 |
| --- | --- |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/build_graph.py` | 构建 LangGraph 主流程，连接多个 MCP Server，并定义节点与路由 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/config.py` | 后端基础路径、导入任务目录和导出目录配置 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/execute_graph.py` | 命令行交互式运行入口 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/chat_api.py` | FastAPI 接口服务入口 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/chat_context.py` | ChatBI 请求模型与 workspace 上下文系统消息 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/my_llm.py` | 大模型配置 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/my_state.py` | LangGraph 状态定义 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/repositories/database.py` | PostgreSQL 连接和基础查询访问层 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/analysis_utils.py` | 报告生成通用分析工具，包括字段识别、主指标选择、监控项和 SQL 模板 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/import_cleaning.py` | 导入清洗、字段标准化、Schema 画像、业务类型识别和导入任务元数据服务 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/charts.py` | 业务图表方案、图表数据集和交互图表配置服务 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/diagnostics.py` | 对比基准、归因假设、异常诊断、显著性判断和策略优先级服务 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/exporters.py` | 报告 Markdown、指标 CSV、看板 CSV 导出服务 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/methodology.py` | 销售、用户、财务、库存、运营和通用业务的方法论与分析方案服务 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/profiling.py` | 数据画像、质量评分和推荐分析路径服务 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/workspace_context.py` | 将业务空间报告压缩成 Agent 可用的 workspace 上下文 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/ywfl_mcp.py` | 业务分流 MCP 服务 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/statistic_db_mcp_tools.py` | 数据库查询 MCP 服务 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/python_chart_mcp.py` | Python 代码执行与绘图 MCP 服务 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/machine_learning_mcp.py` | 评论分析、相关性分析、销量预测 MCP 服务 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/multi_mcp_client.py` | 多 MCP Server 客户端测试示例 |
| `chatbi-react-ui/src/main.jsx` | React 应用入口和页面编排层 |
| `chatbi-react-ui/src/shared/api/client.js` | 前端统一 API 客户端，封装 ChatBI、导入清洗、业务空间报告和批量入库请求 |
| `chatbi-react-ui/src/shared/api/useBiData.js` | BI 模块数据加载 Hook，统一 loading/error 写入方式 |
| `chatbi-react-ui/src/shared/components/EmptyState.jsx` | 通用空状态组件 |
| `chatbi-react-ui/src/shared/components/MarkdownLite.jsx` | 轻量 Markdown 渲染组件 |
| `chatbi-react-ui/src/shared/charts/EChart.jsx` | 项目内轻量 SVG 图表组件，支持柱形图、折线图、饼图和散点图 |
| `chatbi-react-ui/src/features/bi/BiModuleViews.jsx` | 看板、指标、SQL 分析、异常、增长、变现和 RAG 说明视图 |
| `chatbi-react-ui/src/features/chat/ChatMessages.jsx` | 对话消息列表组件 |
| `chatbi-react-ui/src/features/import/ImportCleanView.jsx` | 批量上传、自动清洗、确认入库、批量入库和独立报告生成模块 |
| `chatbi-react-ui/src/features/report/ReportViews.jsx` | 全局分析报告、业务空间报告、空间模块面板和交互式图表视图 |
| `chatbi-react-ui/src/features/templates/TemplateView.jsx` | 快速查询和分析模板卡片视图 |
| `chatbi-react-ui/src/features/workspaces/WorkspacesView.jsx` | 业务空间入口、项目组、文件列表、报告封面和空间内模块导航 |
| `chatbi-react-ui/src/features/workspaces/grouping.js` | 业务空间分组、排序、本地手动分组和时间格式化工具 |

## 环境准备

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS：

```bash
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

根目录已提供 `.env.example` 模板。建议先复制一份到实际读取目录：

```powershell
Copy-Item .env.example langGraph_agent/smart_data_analysis_assistant/.env
```

在 `langGraph_agent/smart_data_analysis_assistant/.env` 中配置：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
QWEN_API_KEY=你的通义千问 API Key

server_url=127.0.0.1

db_host=127.0.0.1
db_port=5432
user=postgres
password=你的数据库密码
dbname=sales_chat

CHATBI_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
CHATBI_SQL_MAX_ROWS=200
CHATBI_SQL_TIMEOUT_MS=5000
CHATBI_ENABLE_PYTHON_EXEC=false
CHATBI_AUDIT_ENABLED=true
CHATBI_AUDIT_LOG_PATH=
CHATBI_AUDIT_ADMIN_TOKEN=
CHATBI_USE_POSTGRES_AUDIT=false
CHATBI_USE_POSTGRES_METADATA=false
```

> 注意：`my_llm.py` 会读取大模型密钥；如果本地运行时读取不到环境变量，可以把同样的 `.env` 复制到 `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/`，或在启动前手动导出环境变量。数据库密码不再提供默认弱密码，未设置 `password` 时后端会拒绝连接。

> 安全开关：`CHATBI_CORS_ORIGINS` 用于限制允许访问后端的前端地址；`CHATBI_SQL_MAX_ROWS` 和 `CHATBI_SQL_TIMEOUT_MS` 用于限制 Agent SQL 查询返回量和执行时长；`CHATBI_ENABLE_PYTHON_EXEC` 默认必须保持 `false`，只有本地演示且确认风险时才临时设为 `true`。

> 审计开关：`CHATBI_AUDIT_ENABLED=true` 时会把 SQL 安全决策写入 `langGraph_agent/smart_data_analysis_assistant/audit_logs/security_audit.jsonl`；如需自定义位置，可设置 `CHATBI_AUDIT_LOG_PATH`。如配置 `CHATBI_AUDIT_ADMIN_TOKEN`，访问 `/bi/audit`、`/bi/audit/init`、`/bi/audit/migrate` 必须携带请求头 `X-ChatBI-Admin-Token`，前端审计页也提供令牌输入框。设置 `CHATBI_USE_POSTGRES_AUDIT=true` 后，审计事件会在写 JSONL 的同时同步到 PostgreSQL `chatbi_audit_event` 表，审计查询也会优先读取 PostgreSQL；如果落库失败会自动保留 JSONL 兜底。审计日志属于本地运行数据，已在 `.gitignore` 中排除。

> 元数据持久化：默认使用本地 JSON 文件保存上传任务和业务空间元数据；如需企业化落库，设置 `CHATBI_USE_POSTGRES_METADATA=true`，再调用 `POST /bi/metadata/init` 创建元数据表，必要时调用 `POST /bi/metadata/migrate` 将历史 JSON 任务迁移到 PostgreSQL。

> GitHub 上传注意：真实 `.env`、PostgreSQL 数据目录 `pgdata/`、日志 `logs/`、本地演示上传目录 `demo_upload_files/`、上传清洗数据 `import_jobs/`、导出报告 `exports/`、前端依赖 `node_modules/`、构建产物 `dist/`、课程 PDF/Word/Excel 数据和生成图片已在 `.gitignore` 中排除，避免泄露密钥、提交本地运行数据或公开私有学习资料。

### 4. 准备数据库

项目代码默认连接 PostgreSQL，并依赖表注释和字段注释帮助大模型理解业务语义。

建议准备以下业务表：

- 商品表
- 用户表
- 用户活跃表
- 销量表

示例 Excel 数据位于：

```text
langGraph_agent/project_data/
```

需要将这些数据导入 PostgreSQL，并为表和字段添加清晰注释，否则 Text-to-SQL 效果会明显下降。

## 启动方式

需要先启动 4 个 MCP Server，再启动 ChatBI API 或命令行入口。

### 0. 启动 PostgreSQL（本机 D 盘示例）

本机已验证 PostgreSQL 位于：

```powershell
D:\postgresql-16.13-3-windows-x64-binaries\pgsql\bin
```

在项目根目录下使用当前 `pgdata` 启动数据库：

```powershell
D:\postgresql-16.13-3-windows-x64-binaries\pgsql\bin\pg_ctl.exe -D pgdata start
```

检查运行状态：

```powershell
D:\postgresql-16.13-3-windows-x64-binaries\pgsql\bin\pg_ctl.exe -D pgdata status
```

### 1. 启动业务分流 MCP

```bash
cd langGraph_agent/smart_data_analysis_assistant/mcp_server
python ywfl_mcp.py
```

默认端口：`9005`

### 2. 启动 Python 绘图 MCP

```bash
cd langGraph_agent/smart_data_analysis_assistant/mcp_server
python python_chart_mcp.py
```

默认端口：`9002`

出于企业安全考虑，`run_python_script_tool` 默认不会执行任意 Python 代码，只返回安全策略提示。若仅用于本机课程演示，可以在 `.env` 中临时设置 `CHATBI_ENABLE_PYTHON_EXEC=true`，工具会改走受限沙箱执行，并限制模块、超时和危险调用；生产环境不建议开启。

### 3. 启动机器学习 MCP

```bash
cd langGraph_agent/smart_data_analysis_assistant/mcp_server
python machine_learning_mcp.py
```

默认端口：`9003`

### 4. 启动数据库查询 MCP

```bash
cd langGraph_agent/smart_data_analysis_assistant/mcp_server
python statistic_db_mcp_tools.py
```

默认端口：`9004`

数据库查询工具已接入只读 SQL 安全网关：只允许 `SELECT`、`WITH`、`EXPLAIN`，禁止 `INSERT`、`UPDATE`、`DELETE`、`DROP`、`ALTER`、`TRUNCATE`、`COPY`、`CALL` 等危险语句，同时拒绝多语句 SQL，并自动限制最大返回行数和查询超时。workspace-aware 模式还会做表级和字段级白名单校验，禁止跨空间表引用、未知字段引用和 `SELECT *`。

### 5. 命令行运行智能体

```bash
cd langGraph_agent/smart_data_analysis_assistant/chatbi_graph
python execute_graph.py
```

### 6. 启动 API 服务

```bash
cd langGraph_agent/smart_data_analysis_assistant/chatbi_graph
uvicorn chat_api:app --host 0.0.0.0 --port 9008
```

接口地址：

```text
POST http://127.0.0.1:9008/chatbi_service
```

### 7. 启动 React 前端界面

前端位于 `chatbi-react-ui/`，采用接近纸张的浅米白工作区 UI，侧边栏使用更深一层的米灰色以区分导航层，并支持一键收起为图标栏。页面标题弱化字号和字重，避免与下方模块标题抢层级；整体卡片降低阴影和色块对比。功能包含：

- `数据问答`：普通聊天式业务查询与分析。
- `业务空间`：按 `业务空间入口 → 项目分组 → 文件列表 → 报告封面` 分层检索；入口页只保留业务空间名称，避免暴露说明字段、文件数量和大量文件内容。
- `SQL 分析`：沉淀自然语言查数、聚合统计、对比分析和环比模板。
- `BI 看板`：展示商品数量、年度销量、平均价格、平均活跃时长、月度销量趋势、Top 商品销量。
- `指标体系`：维护年度销量、月度销量、商品均价、用户活跃时长、Top 商品销量等指标口径。
- `异常分析`：基于月度销量均值、环比、偏离度识别异常月份并给出解释。
- `用户增长`：围绕用户数、活跃用户、高活跃用户和分层运营动作做分析。
- `变现成本`：估算商品收入贡献，并预留成本、ROI、毛利率等企业分析口径。
- `分析报告`：自动生成“现象 → 原因拆解 → 异常关注 → 建议”的结构化报告。
- `导入导出`：导入 Excel/CSV 后自动识别字段并执行去重、缺失值、类型和字段标准化清洗，支持下载清洗文件、确认入库和导出报告/指标/看板数据。
- `RAG 知识库`：企业知识库增强模块，默认不启用、不参与 SQL 问答链路，可按需接入指标口径、数据字典、历史报告。
- `快速查询`：常用查询卡片，可一键填入输入框或立即执行。
- `分析模板`：销量趋势、图表生成、销量预测、用户画像等模板。

首次运行安装依赖：

```powershell
cd chatbi-react-ui
npm.cmd install
```

启动前端：

```powershell
npm.cmd run dev
```

浏览器访问：

```text
http://127.0.0.1:5173/
```

前端通过 Vite 代理调用后端 `/api/chatbi_service`，界面不会显示后端域名或端口。

生产构建校验：

```bash
cd chatbi-react-ui
npm run build
```

新增 BI 模块接口：

| 接口 | 作用 |
| --- | --- |
| `GET /bi/sql-analysis` | 返回 SQL 分析能力、自然语言查数模板和 SQL 示例 |
| `GET /bi/dashboard` | 返回 BI 看板指标卡、月度销量趋势和 Top 商品销量 |
| `GET /bi/metrics` | 返回业务指标体系定义 |
| `GET /bi/anomalies` | 返回核心指标异常波动分析 |
| `GET /bi/user-growth` | 返回用户增长指标和分层运营建议 |
| `GET /bi/monetization` | 返回收入估算、Top 收入商品和成本分析预留口径 |
| `GET /bi/report` | 返回结构化业务分析报告 |
| `GET /bi/workspaces` | 返回上传文件形成的业务空间列表，默认最多读取最近 200 个空间 |
| `GET /bi/workspaces/{workspace_id}/report` | 返回某个上传表的独立分析报告 |
| `GET /bi/workspaces/{workspace_id}/export-report` | 导出某个上传表的独立报告 Markdown |
| `GET /bi/import-clean` | 返回导入、自动清洗、字段映射和导出流程 |
| `GET /bi/import-clean/jobs` | 返回最近导入清洗任务 |
| `POST /bi/import-clean/upload` | 上传 CSV/XLSX/XLS 文件并自动清洗，返回清洗报告和预览 |
| `POST /bi/import-clean/upload-batch` | 批量上传多个 CSV/XLSX/XLS 文件并分别生成业务空间 |
| `GET /bi/import-clean/jobs/{job_id}` | 查询单个导入清洗任务详情 |
| `GET /bi/import-clean/jobs/{job_id}/download` | 下载清洗后的 CSV 文件 |
| `POST /bi/import-clean/jobs/{job_id}/commit` | 将清洗后的数据确认写入 PostgreSQL 新表 |
| `POST /bi/import-clean/jobs/batch-commit` | 将多个清洗任务批量确认入库 |
| `POST /bi/metadata/init` | 初始化 PostgreSQL 元数据表，用于保存业务空间、数据资产、导入任务、报告和指标定义 |
| `POST /bi/metadata/migrate` | 将本地 JSON 导入任务迁移到 PostgreSQL 元数据表，支持传入 `limit` 控制迁移数量 |
| `GET /bi/export/report` | 导出结构化分析报告 Markdown |
| `GET /bi/export/metrics` | 导出指标体系 CSV |
| `GET /bi/export/dashboard` | 导出看板核心数据 CSV |
| `GET /bi/rag` | 返回可选 RAG 知识库定位、场景和建议技术栈 |
| `GET /bi/audit` | 返回最近 SQL 安全审计事件，支持按 `allowed`、`workspace_id`、`source`、`event_type`、`limit` 过滤；配置管理员令牌后需请求头鉴权 |
| `POST /bi/audit/init` | 初始化 PostgreSQL 审计表 `chatbi_audit_event`，配置管理员令牌后需请求头鉴权 |
| `POST /bi/audit/migrate` | 将本地 JSONL 审计日志迁移到 PostgreSQL 审计表，支持传入 `limit` 控制迁移数量 |

## 安全与验证

本项目已补充第一阶段 P0 安全治理：

- `SQL 安全网关`：`db_sql_tool` 只允许单条只读查询，默认最多返回 `200` 行，并通过 PostgreSQL `statement_timeout` 限制慢查询。
- `字段白名单`：workspace-aware 查询必须显式访问当前空间授权表，且只能引用字段画像中的字段；`SELECT *` 和未知字段会被拦截。
- `Python 执行隔离`：任意 Python 执行默认关闭；显式开启后也会先做 AST 安全检查，再进入临时目录沙箱执行。
- `CORS 白名单`：FastAPI 不再使用 `*`，默认只允许 `http://127.0.0.1:5173` 和 `http://localhost:5173`。
- `弱密码治理`：后端和 MCP 不再使用 `123456` 作为数据库密码兜底，必须通过 `.env` 明确配置。
- `安全解析`：机器学习相关列表入参使用 `json.loads` / `ast.literal_eval`，不再使用 `eval` 解析输入。
- `审计留痕`：SQL 安全网关和 workspace SQL 范围校验会写入 JSONL 事件，记录放行/拦截、原因、来源、业务空间、表引用、查询预览和查询哈希；审计接口支持可选管理员令牌保护和条件过滤，并可将事件同步到 PostgreSQL 审计表。

第一阶段 P1 拆分也已开始：

- `配置层`：`config.py` 统一维护导入任务、清洗文件和导出目录。
- `Repository 层`：`repositories/database.py` 承担 PostgreSQL 连接与基础查询。
- `Service 层`：`services/import_cleaning.py` 承担导入清洗、字段角色画像、业务类型识别和任务元数据管理。
- `Charts 层`：`services/charts.py` 承担图表方案、图表解释、ECharts 数据集和交互式图表配置。
- `Exporters 层`：`services/exporters.py` 承担 Markdown/CSV 文件生成，避免导出逻辑继续堆在 API 文件。
- `Context 层`：`chat_context.py` 承担 `/chatbi_service` 请求模型和业务空间上下文消息构造。
- `Workspace Context 层`：`services/workspace_context.py` 将完整报告压缩为 Agent 可消费的 schema/profile/report 摘要。
- `Workspace SQL Scope 层`：`services/workspace_sql_scope.py` 为当前业务空间生成 SQL 策略、授权表结构、字段白名单和查询范围校验，避免 Agent 跨空间查表或访问未知字段。
- `Methodology 层`：`services/methodology.py` 承担业务分析方案库、专属方法论、分析计划和执行摘要。
- `Profiling 层`：`services/profiling.py` 承担数据画像、质量评分和推荐分析路径。
- `Diagnostics 层`：`services/diagnostics.py` 承担问题诊断链路、归因假设、异常原因、轻量显著性和策略优先级。
- `Metadata Repository 层`：`repositories/workspace_metadata.py` 承担业务空间、数据资产、导入任务、分析报告和指标定义的 PostgreSQL 表结构与读写。
- `Reporting Persistence 层`：`services/reporting_persistence.py` 在元数据落库模式下同步业务空间报告摘要和指标目录，默认关闭时不触碰 PostgreSQL。
- `兼容策略`：现有 API 路径、响应字段和前端调用方式保持不变，`bi_api.py` 逐步退化为报表装配与接口兼容层。

前端 P2 拆分也已开始：

- `shared/api`：统一封装 `fetch`、错误处理、ChatBI 对话、上传清洗、业务空间报告、单个/批量入库等请求。
- `shared/components`：沉淀 `EmptyState`、`MarkdownLite` 等跨页面复用组件。
- `features/bi`：承接看板、指标、SQL 分析、异常、增长、变现和 RAG 说明等通用 BI 模块视图。
- `features/bi/AuditView`：在通用 BI 模块中展示最近 SQL 审计摘要和事件明细，支持按放行状态、业务空间 ID、来源和管理员令牌筛选，便于企业排查跨空间查表与危险查询。
- `features/chat`：承接对话消息列表，后续可继续拆出输入框、上下文卡片和会话状态。
- `features/import`：承接批量上传、自动清洗、确认入库、批量入库和独立报告生成，主入口只负责传入数据和报告展示组件。
- `features/report`：承接全局分析报告、业务空间报告、空间模块面板和交互式图表，主入口不再承载大段报告 JSX。
- `features/templates`：承接快速查询和分析模板卡片，后续可把模板配置迁移到后端或 JSON 配置。
- `features/workspaces`：承接业务空间入口、项目组、文件列表、报告封面、模块导航、分组策略、手动分组 localStorage 和时间格式化工具，避免主入口继续膨胀。
- `性能优化`：前端采用 `React.lazy + Suspense` 对业务空间、导入、报告和 BI 模块做路由级懒加载；图表改为项目内轻量 SVG 渲染，移除 `echarts/echarts-for-react` 大依赖，生产构建不再出现大包体积 warning。
- `兼容策略`：本轮只做结构迁移，不改变页面路由、接口路径和视觉表现。

逐步测试命令：

```bash
python -m pytest tests -q
npm --prefix chatbi-react-ui run build
```

审计接口验证：

```powershell
Invoke-RestMethod "http://127.0.0.1:9008/bi/audit?limit=20"
```

如配置了 `CHATBI_AUDIT_ADMIN_TOKEN`：

```powershell
Invoke-RestMethod "http://127.0.0.1:9008/bi/audit?allowed=false&limit=20" -Headers @{"X-ChatBI-Admin-Token"="你的令牌"}
```

启用 PostgreSQL 审计表：

```powershell
# .env 中设置 CHATBI_USE_POSTGRES_AUDIT=true 后执行
Invoke-RestMethod "http://127.0.0.1:9008/bi/audit/init" -Method Post -Headers @{"X-ChatBI-Admin-Token"="你的令牌"}
Invoke-RestMethod "http://127.0.0.1:9008/bi/audit/migrate" -Method Post -Headers @{"X-ChatBI-Admin-Token"="你的令牌"} -ContentType "application/json" -Body '{"limit":1000}'
```

导入清洗接口会在 `langGraph_agent/smart_data_analysis_assistant/import_jobs/` 下保存任务元数据和清洗后的 CSV 文件；确认入库时会新建 `import_` 前缀的数据表，避免覆盖原业务表。

元数据存储采用双轨策略：默认只依赖本地 JSON，便于本机演示和测试；启用 `CHATBI_USE_POSTGRES_METADATA=true` 后，上传、清洗、入库状态会同步写入 `chatbi_workspace`、`chatbi_data_asset`、`chatbi_import_job` 等表，业务空间报告生成后会同步报告摘要到 `chatbi_analysis_report`，并把该空间指标目录写入 `chatbi_metric_definition`。未安装或未配置 `psycopg2/PostgreSQL` 时，默认模式不会阻塞测试和前端开发。

Excel 导入时，日期字段会自动转换为可 JSON 序列化的时间字符串，避免 `Timestamp is not JSON serializable` 这类错误。

上传文件默认会形成一个独立业务空间。前端采用四层空间结构：

1. `业务空间入口`：只显示 `销售经营`、`用户运营`、`财务经营`、`库存管理`、`运营分析`、`通用业务` 等业务空间名称，不显示说明字段、文件数量，也不展开文件和报告；入口卡片采用米色低对比背景、纤细编号和悬浮层次增强设计感。
2. `业务空间内项目组`：进入某个业务空间后，只显示该空间内的项目分组，支持按 `上传时间`、`名称`、`入库状态` 自动分组，也支持在前端本地做手动分组调整。
3. `项目组文件列表`：进入项目组后，再显示该组内的上传文件、行列规模、入库状态和报告入口，便于文件数变多后检索。
4. `报告封面`：点击报告后默认只展示报告名称和展开按钮；用户主动展开后，才显示该空间专属的 `空间总览`、`诊断报告`、`BI 看板`、`指标体系`、`异常监控`、`增长分析`、`变现/ROI`、`库存诊断` 和 `导出与入库`。

不同业务空间会根据业务类型、字段角色和时间字段自动显示不同模块，避免所有模块都堆在首页，也避免在业务空间入口直接暴露大量文件内容。

批量导入支持一次选择多个 CSV/XLSX/XLS 文件。系统会逐个执行清洗、业务类型识别和业务空间创建；批量入库会把多个业务空间对应的数据表写入 PostgreSQL，已入库任务会自动跳过，避免重复创建。

业务空间报告会先执行一个轻量的 AI 前期判断步骤：根据文件名、行列规模、字段名、字段角色画像和业务关键词识别业务类型、主指标、核心维度，并选择合适的分析方案。该预判阶段采用 `schema-only` 策略，只传输文件名、行列数、字段名和字段角色，不传输数据明细，以提升判断速度并减少 token 消耗。

为了支撑 `schema-only` 预判，导入清洗会先做字段标准化、空白值处理、类型识别、日期转换、数值转换、去重和字段角色提取。字段角色包括 `metric`、`dimension`、`time`、`identifier`，后续报告再基于清洗后的聚合数据生成图表和详细结论。

业务空间报告会尽量串联现有业务模块：`指标体系`、`BI 看板口径`、`业务监控与异常`、`用户/客户增长分析`、`变现与成本分析`、`SQL 分析模板`、`导入清洗质量` 和 `报告导出`。如果上传表缺少某类字段，例如成本字段或时间字段，对应模块会给出补字段建议，而不是混用默认样例业务数据。

当 `/chatbi_service` 传入 `workspace_id` 时，系统会进入 workspace-aware 模式：后端先构造该业务空间的字段画像、报告摘要和 SQL 策略，再把数据库工具替换为当前空间作用域工具。`list_tables_tool` 只返回当前业务空间授权表和字段画像；`db_sql_tool` 会二次校验 SQL，只允许查询当前空间入库后的 `dbTable`，并且只能引用字段画像中的字段。未入库空间会拒绝明细查询并提示先确认入库；`SELECT *`、越权表引用和未知字段引用都会被拦截。这一层是工具级约束，不只依赖大模型提示词。所有 SQL 放行、拦截、越权表/字段引用和未入库拒绝都会进入审计日志，并可在前端 `审计日志` 页面查看；开启 `CHATBI_USE_POSTGRES_AUDIT=true` 后还会同步到 PostgreSQL，方便备份、检索和后续接企业审计系统。

业务空间报告新增 Tableau 式诊断层：每份报告会根据业务类型选择专属方法论，例如 `销售漏斗`、`客户分层`、`区域效率`、`产品结构`、`ROI`、`留存`、`复购`、`指标树拆解` 和 `趋势异常`。报告不只输出描述统计，还会补充 `归因诊断`、`异常原因假设`、`对比基准`、`轻量显著性/可信度判断` 和 `策略建议优先级`，方便企业经营例会直接讨论。

业务空间报告内置 `业务分析方案库`，目前覆盖 `销售经营`、`用户运营`、`财务经营`、`库存管理`、`运营分析` 和 `通用业务`。每个方案都有专属分析目标、必需字段信号和默认推荐路径，上传表会自动匹配方案库，并生成 `数据画像`、`质量评分`、`扣分原因` 和 `推荐分析路径`。

报告结构已升级为问题诊断型链路：`现象 → 对比 → 异常 → 归因假设 → 行动建议`。系统会先描述发生了什么，再对比头部集中度、趋势波动率等基准，随后识别异常周期，提出可验证的归因假设，并给出 P0/P1/P2/P3 优先级行动建议。

业务空间报告会按数据特征自动选择图表：维度贡献适合 `柱形图`，结构占比适合 `饼状图`，时间字段适合 `折线图`，两个数值字段适合 `散点图`。前端使用轻量 SVG 图表组件渲染这些图表，并在每张图上展示 `该图回答什么业务问题`、`为什么使用这个图` 和 `如何解读`，减少模板化图表堆叠。

前端新增交互式分析视图，支持在报告内切换 `指标`、`维度`、`时间字段`、`时间粒度（月/季/年）` 和散点图 Y 轴指标，用同一份上传数据快速验证不同业务假设。

请求示例：

```json
{
  "user_id": "session_1",
  "message": "查询商品洗碗布的月销量数据，并绘制一张柱状图",
  "history": [],
  "workspace_id": "可选，业务空间 ID"
}
```

`workspace_id` 为可选字段。不传时保持默认样例库对话；传入后，后端会先读取该业务空间的 Schema 画像、字段角色、指标目录、数据质量评分、报告摘要和推荐分析路径，并以系统消息注入 Agent。Agent 回答必须限定在当前业务空间内，并说明使用的数据资产，避免不同业务文件之间串场。

Windows PowerShell 接口验证示例：

```powershell
@'
import json
import urllib.request

payload = {"user_id": "demo", "message": "\u67e5\u8be2\u5947\u591a\u7684\u4ef7\u683c\u662f\u591a\u5c11", "history": []}
data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:9008/chatbi_service", data=data, headers={"Content-Type": "application/json"}, method="POST")

with urllib.request.urlopen(req, timeout=120) as resp:
    print(resp.status)
    print(resp.read().decode("utf-8"))
'@ | .\.venv\Scripts\python.exe -
```

响应示例：

```json
{
  "message": "查询到结果如下：\n\n**奇多的价格为：5.5元** 🎉"
}
```

## 示例问题

### Python 计算/编码

- `计算一下 365882 * 876545 等于多少`
- `写一段 Python 冒泡排序代码并执行`
- `有 5 个月销量数据 [1,3,5,7,9]，绘制一个销量饼图`

### 业务数据查询

- `查询健身手套价格是多少`
- `查询运动类商品有多少`
- `运动用品平均价格与食品平均价格哪个高`
- `抽纸近 12 个月的总销量和洗手液的总销量哪个更高`

### 数据分析与建模

- `分析一下王一珂的用户画像`
- `查询商品洗碗布的月销量数据，绘制一张以月为维度的销量柱状图`
- `查询保鲜袋历史 12 个月的销量，预测一下下个月销量`
- `查询银耳的用户评论和星级数据，并分析评论好坏与星级是否相关`

## 设计亮点

- **职责拆分清晰**：业务分流、查库、代码执行、机器学习分析分别封装为独立 MCP 服务。
- **可扩展性强**：新增能力时，只需要新增 MCP Tool，并在 LangGraph 节点中绑定即可。
- **上下文可控**：先通过 `list_tables_tool` 获取数据库元数据，再让 Agent 基于真实表结构生成 SQL。
- **支持多步推理**：数据分析节点使用 ReAct Agent，可根据中间结果继续调用 SQL、Python 或算法工具。

## 当前限制

- Python 任意代码执行已默认关闭；当前沙箱仍是进程级隔离，生产环境建议进一步放入 Docker/Firecracker 级隔离并限制网络和资源。
- SQL 工具已接入只读安全网关、workspace 表/字段白名单、JSONL 审计日志和可选 PostgreSQL 审计表；后续还需要补租户级权限、字段脱敏和审计检索权限。
- 会话历史目前主要由请求侧传入或内存维护，生产环境建议落库并做摘要压缩。
- 图表结果当前返回本地路径，生产环境建议上传对象存储并返回 URL。
- 部分文件中存在 Linux 服务器绝对路径示例，本地运行时可能需要调整 `sys.path` 或工作目录。

## 后续优化方向

- P1：拆分 `bi_api.py` 巨石文件，将导入清洗、Schema 画像、分析计划、报告生成、图表、导出和持久化拆成 service/repository/schema 层。
- P1：继续增强 `/chatbi_service` 的 workspace-aware 能力，把租户身份、字段脱敏策略和审计检索权限一起下推到数据库工具层。
- P2：前端拆成 `features/import`、`features/workspaces`、`features/report`、`features/chat`、`shared/api`、`shared/components`。
- P2：把报告升级成证据链报告，补充结论、指标证据、置信度、限制和下一步验证建议。
- P3：补充异步任务、缓存、日志追踪、Docker Compose 和端到端评估集。
- 暂缓：企业 RAG 模块先保留可选入口，等有高质量指标口径、字段字典、历史报告和业务术语后再建设。
- 增加 Prompt 配置化和版本管理。
- 增加任务状态流式输出或 WebSocket 推送。
- 增加缓存层，复用高频查询结果。
- 增加测试集和 Eval 流程，稳定评估 Text-to-SQL、图表生成和总结质量。
