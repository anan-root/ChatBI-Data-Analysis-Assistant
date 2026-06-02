# ChatBI 数据分析助手设计与开发 Trace

## 0. 从零开发逐步 Trace

这一节按“从 0 到 1 开发一个 ChatBI 项目”的方式写。每一步都说明：做什么、为什么做、用了什么技术、产生了什么文件。它不是简单记录当前项目改过什么，而是把这个项目拆成一条可复现的工程路径。

项目目标不是“做一个能聊天的 Demo”，而是做一个完整的企业级 ChatBI 原型：用户上传业务数据后，系统自动清洗、识别业务类型、建立业务空间、生成数据画像和质量评分，再输出诊断型业务报告、图表和可继续追问的自然语言问数能力。

### Step 0.1: 创建 Git 仓库

执行命令：

```bash
git init
```

这一步做了什么：

- 在项目根目录创建 `.git/` 隐藏目录。
- 让 Git 开始追踪源代码、文档和配置文件。
- 后续可以通过 `git status` 查看变更，通过 `git diff` 审查修改，通过 `git commit` 保存阶段版本。

为什么第一步做 Git：

- ChatBI 项目会同时涉及前端、后端、数据库、MCP、Docker、测试和文档。
- 如果没有版本控制，很难区分“功能开发”“界面调整”“安全修复”“部署配置”分别改了什么。
- 对 AI 辅助开发项目来说，Git 是防止修改失控的最基本边界。

当前项目对应状态：

- 已使用 Git 管理。
- GitHub 远端仓库为 ChatBI 项目仓库。
- 简略版 `readme.md` 已用于 GitHub 展示。
- 本地详细文档 `README_FULL.md` 通过本地 exclude 排除，不上传 GitHub。

### Step 0.2: 创建 `.gitignore`

创建文件：

```text
.gitignore
```

这一步做了什么：

- 忽略 Python 虚拟环境：`.venv/`、`venv/`、`__pycache__/`。
- 忽略前端依赖和构建产物：`chatbi-react-ui/node_modules/`、`chatbi-react-ui/dist/`。
- 忽略环境变量：`.env`、`.env.*`，但保留 `.env.example`、`.env.docker.example`。
- 忽略运行数据：日志、上传任务、导出文件、PostgreSQL 数据目录、图表输出目录。
- 忽略私有课程资料和大文件。

为什么要做：

- `.env` 里可能包含 API Key、数据库密码，不应该提交。
- 上传的 Excel / CSV 是用户业务数据，不属于源代码。
- PostgreSQL 数据目录、日志、缓存会不断变化，提交后会污染仓库。
- `node_modules` 和虚拟环境体积很大，应由依赖文件重新安装。

这一步对应的工程能力：

- 敏感信息保护。
- 源码和运行数据分离。
- Git 仓库治理。
- 可复现依赖管理。

### Step 0.3: 明确项目目标

项目目标可以拆成四层：

1. **数据层目标**：支持业务表格上传、清洗、画像、质量评分和可选入库。
2. **分析层目标**：根据不同业务类型生成专属分析路径，而不是只做通用描述统计。
3. **智能体层目标**：让用户可以通过自然语言在当前业务空间内问数、解释图表和追问报告。
4. **工程层目标**：具备前后端分离、MCP 工具层、安全边界、审计日志、测试和 Docker 部署。

为什么先写目标：

- ChatBI 很容易写成“功能堆叠”：上传、聊天、图表、报告各写一块，但没有统一业务链路。
- 先定义目标，可以决定哪些能力是核心，哪些能力只是预留。
- 当前版本先把核心闭环跑通：上传 → 清洗 → 空间 → 报告 → 图表 → 问数。
- 登录、多租户、完整权限、企业 RAG、异步任务等能力先作为后续扩展。

### Step 0.4: 设计整体架构

从零设计时，可以采用以下分层：

```text
React 前端工作台
  ↓ HTTP API
FastAPI 后端服务
  ↓ 服务层 / 仓储层
导入清洗、画像、报告、图表、导出、审计、元数据
  ↓ Agent 调度
LangGraph 数据分析 Agent
  ↓ MCP 工具协议
业务分流 MCP / 数据库 MCP / Python 图表 MCP / 机器学习 MCP / 业务空间 MCP
  ↓
PostgreSQL / 本地 JSON 元数据 / 文件系统
```

为什么这样分：

- 前端只负责交互和展示，不直接操作数据库。
- FastAPI 提供稳定接口，便于前端、测试和未来第三方系统调用。
- 分析逻辑放在 services，避免 API 文件变成巨石。
- Agent 不直接写死所有能力，而是通过 MCP 调工具。
- MCP 让数据库查询、Python 执行、机器学习、业务空间上下文成为可插拔工具。
- 安全治理放在工具层和服务层，不能只靠提示词约束模型。

对应主要目录：

```text
chatbi-react-ui/
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/
langGraph_agent/smart_data_analysis_assistant/mcp_server/
langGraph_agent/smart_data_analysis_assistant/core/
tests/
docker/
```

### Step 0.5: 设计目录结构

建议从零创建如下目录：

```text
.
├── chatbi-react-ui
│   └── src
│       ├── features
│       └── shared
├── langGraph_agent
│   └── smart_data_analysis_assistant
│       ├── chatbi_graph
│       │   ├── repositories
│       │   └── services
│       ├── core
│       └── mcp_server
├── tests
├── docker
├── docs
├── readme.md
├── README_FULL.md
├── requirements.txt
├── .env.example
├── .env.docker.example
└── docker-compose.yml
```

每个目录的职责：

- `chatbi-react-ui/`：React + Vite 前端项目。
- `features/`：业务功能模块，例如导入、业务空间、报告、聊天。
- `shared/`：共享 API client、图表组件、基础组件。
- `chatbi_graph/`：FastAPI、LangGraph、业务 API 和分析编排。
- `services/`：导入清洗、画像、方法论、诊断、图表、导出、workspace 策略。
- `repositories/`：PostgreSQL 元数据、审计事件、数据库访问。
- `core/`：安全网关、审计日志等横切能力。
- `mcp_server/`：独立 MCP 工具服务。
- `tests/`：pytest 测试。
- `docker/`：Dockerfile、Nginx 和容器启动脚本。
- `docs/`：设计 trace、架构说明等工程文档。

为什么这样分：

- 前后端分离，部署边界清晰。
- services 和 repositories 分离，便于测试和后续重构。
- MCP 服务独立，便于新增工具。
- docs 独立，可以沉淀项目经验，不污染 README。

### Step 0.6: 搭建后端依赖和配置

创建文件：

```text
requirements.txt
.env.example
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/config.py
```

核心依赖包括：

- `fastapi`：提供 HTTP API。
- `uvicorn[standard]`：运行 ASGI 服务。
- `pandas`、`numpy`、`scipy`：表格处理、统计计算、相关性检验。
- `psycopg2`：连接 PostgreSQL。
- `langgraph`、`langchain-mcp-adapters`、`mcp`：Agent 编排和 MCP 工具接入。
- `openai`：兼容 DeepSeek / 通义千问等 OpenAI 风格接口。
- `python-multipart`：支持文件上传。
- `python-dotenv`：读取 `.env`。
- `matplotlib`：生成 Python 图表。

`.env.example` 管理：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
QWEN_API_KEY=your_qwen_api_key

db_host=127.0.0.1
db_port=5432
user=postgres
password=your_postgres_password
dbname=sales_chat

server_url=127.0.0.1
server_api_url=http://127.0.0.1:9008/chatbi_service

CHATBI_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
CHATBI_SQL_MAX_ROWS=200
CHATBI_SQL_TIMEOUT_MS=5000
CHATBI_ENABLE_PYTHON_EXEC=false
CHATBI_AUDIT_ENABLED=true
CHATBI_USE_POSTGRES_METADATA=false
CHATBI_USE_POSTGRES_AUDIT=false
```

为什么配置要集中：

- 大模型 Key、数据库地址、CORS、安全开关都不应该写死在代码里。
- Docker、本地开发、生产部署需要不同配置。
- 安全策略必须能通过环境变量关闭或收紧。

### Step 0.7: 搭建 FastAPI API 层

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/chat_api.py
```

这一步做了什么：

- 创建 FastAPI app。
- 配置 CORS 白名单。
- 注册 ChatBI 主对话接口。
- 注册 BI 看板、指标、报告、导入清洗、业务空间、导出、审计和元数据接口。

核心接口：

```text
POST /chatbi_service
GET  /bi/dashboard
GET  /bi/metrics
GET  /bi/anomalies
GET  /bi/report
GET  /bi/workspaces
GET  /bi/workspaces/{workspace_id}/report
POST /bi/import-clean/upload
POST /bi/import-clean/upload-batch
POST /bi/import-clean/jobs/{job_id}/commit
POST /bi/import-clean/jobs/batch-commit
GET  /bi/audit
POST /bi/metadata/init
POST /bi/audit/init
```

为什么先搭 API：

- 前端需要稳定接口才能开发。
- 测试可以直接验证接口行为。
- 后续 Agent、清洗、报告都可以挂到统一 API 下。

当前还可以继续优化的地方：

- `chat_api.py` 承担了较多路由聚合职责。
- 后续可拆成 `routes/imports.py`、`routes/workspaces.py`、`routes/audit.py`、`routes/chat.py`。

### Step 0.8: 编写文件导入与自动清洗服务

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/import_cleaning.py
```

核心函数：

- `read_dataset(file_path)`：读取 CSV / Excel。
- `normalize_identifier(value, fallback)`：规范化字段名和表名。
- `deduplicate_columns(columns)`：处理重复字段名。
- `json_safe(value)` / `json_ready(value)`：处理 Timestamp、NaN、Inf 等 JSON 序列化问题。
- `classify_field_role(column_name, dtype)`：识别字段角色。
- `build_schema_profile(df, original_filename)`：构建字段画像。
- `infer_business_type_from_schema(schema_profile)`：根据 schema 判断业务类型。
- `clean_dataframe(raw_df)`：执行清洗。
- `process_import_file(file_path, original_filename)`：生成完整导入任务。

这一步做了什么：

- 支持 `.csv`、`.xlsx`、`.xls`。
- 标准化字段名。
- 识别日期、数值、分类、ID 字段。
- 处理缺失值和重复行。
- 生成清洗后的预览数据。
- 生成 schema profile。
- 生成业务类型初判。
- 把导入任务保存为本地元数据。

为什么清洗必须先做：

- 后续业务类型识别只传字段和文件名，要求字段质量较高。
- 图表和报告依赖字段类型，如果日期或数值识别错误，报告会偏。
- Excel 日期如果不转成字符串，FastAPI 返回 JSON 会失败。
- 企业数据经常字段名混乱、空值多、类型不一致，必须先治理。

### Step 0.9: 设计业务空间 Workspace

业务空间不是普通文件夹，而是 ChatBI 的上下文隔离单元。

每个 workspace 需要包含：

```text
workspace_id
business_type
original_filename
cleaned_filename
schema_profile
data_profile
quality_score
recommended_paths
report_summary
metrics
db_table
commit_status
created_at
```

为什么要设计 workspace：

- 用户可能上传销售、财务、库存、用户运营等完全不同的数据。
- 如果全部混在一个聊天上下文里，Agent 很容易串场。
- 企业 BI 必须知道“当前分析的是哪个业务空间、哪张表、哪些字段”。
- 后续权限、审计、指标口径、RAG 都应该挂在 workspace 上。

当前实现涉及文件：

```text
services/import_cleaning.py
services/workspace_context.py
services/workspace_sql_scope.py
repositories/workspace_metadata.py
```

### Step 0.10: 编写数据画像和质量评分

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/profiling.py
```

核心函数：

- `build_data_profile(...)`：生成数据画像。
- `build_quality_score(...)`：计算质量评分。
- `build_recommended_paths(...)`：生成推荐分析路径。

数据画像包含：

- 行数、列数。
- 数值字段数量。
- 分类字段数量。
- 日期字段数量。
- 缺失值情况。
- 重复值情况。
- 主指标候选。
- 主维度候选。
- 数据限制说明。

质量评分用于判断：

- 是否有可分析指标。
- 是否有维度字段。
- 是否有时间字段。
- 缺失值是否过高。
- 重复行是否影响判断。
- 结论可信度是否需要降级。

为什么要做质量评分：

- 企业报告不能只要“看起来完整”，还要说明数据是否可靠。
- 如果缺少时间字段，就不能硬做趋势分析。
- 如果缺少成本字段，就不能硬做 ROI。
- 数据质量直接决定报告结论的可信度。

### Step 0.11: 编写业务分析方案库

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/methodology.py
```

这一步做了什么：

- 为不同业务类型建立不同分析框架。
- 根据 schema profile 推荐分析路径。
- 根据字段情况判断哪些模块可用、哪些模块缺字段。

当前支持的业务框架：

```text
销售经营：销售漏斗、产品结构、区域效率、复购线索、趋势异常
用户运营：用户分层、留存、活跃、转化、增长路径
财务经营：收入成本、毛利结构、ROI、费用效率、预算偏差
库存管理：库存周转、滞销识别、缺货风险、库存结构
运营分析：指标监控、活动效果、渠道效率、异常波动
通用业务：指标树拆解、维度贡献、趋势观察、异常识别
```

为什么不能只做通用分析：

- 销售数据关心漏斗、产品结构、区域效率。
- 用户数据关心分层、留存、复购、活跃。
- 财务数据关心收入、成本、毛利、ROI。
- 库存数据关心周转、滞销、缺货。
- 不同业务问题要用不同方法论，否则报告会变成普通描述统计。

### Step 0.12: 编写诊断型报告服务

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/diagnostics.py
```

核心函数：

- `build_benchmark_summary(...)`：构建对比基准。
- `build_driver_analysis(...)`：生成驱动因素分析。
- `build_anomaly_diagnosis(...)`：生成异常诊断。
- `build_significance_tests(...)`：轻量显著性 / 可信度判断。
- `build_priority_actions(...)`：按优先级生成行动建议。
- `build_diagnostic_story(...)`：生成“现象 → 对比 → 异常 → 归因假设 → 行动建议”。

报告结构：

```text
1. 执行摘要
2. 数据画像
3. 数据质量评分
4. 推荐分析路径
5. 指标体系
6. 图表分析
7. 现象描述
8. 对比基准
9. 异常识别
10. 归因假设
11. 行动建议
12. 数据限制和下一步验证
```

为什么这样写报告：

- 描述统计只能回答“发生了什么”。
- 企业分析还需要回答“是否异常、为什么、下一步做什么”。
- 归因必须是“假设”，不能把相关性直接写成因果。
- 行动建议要有优先级，否则不可落地。

### Step 0.13: 编写图表生成和图表解释

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/charts.py
```

核心函数：

- `build_chart_blueprints(...)`：根据业务和字段生成图表蓝图。
- `build_workspace_charts(...)`：生成图表数据。
- `build_interactive_chart_config(...)`：生成前端交互式图表配置。

支持图表：

- 柱形图：回答“哪个类别贡献最高”。
- 饼图：回答“结构占比如何”。
- 折线图：回答“趋势是否变化”。
- 散点图：回答“两个指标是否相关”。

每张图表都应该带三类说明：

```text
question：这张图回答什么业务问题
why：为什么使用这种图
interpretation：如何解读图表
```

为什么要写图表解释：

- 单纯展示图表容易模板化。
- 业务用户需要知道这张图解决什么问题。
- 图表选择本身就是分析方法的一部分。
- 解释可以降低用户误读图表的风险。

### Step 0.14: 设计 PostgreSQL 元数据持久化

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/repositories/database.py
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/repositories/workspace_metadata.py
```

这一步做了什么：

- 封装 PostgreSQL 连接。
- 设计 workspace、data_asset、import_job、analysis_report、metric_definition 等表。
- 支持本地 JSON 元数据和 PostgreSQL 元数据双轨模式。

为什么采用双轨：

- 本地演示时不应该强依赖 PostgreSQL 元数据表。
- Docker 或企业化部署时，需要把元数据落到数据库。
- 双轨可以兼顾易用性和可治理性。

相关环境变量：

```env
CHATBI_USE_POSTGRES_METADATA=false
```

如果设为 `true`：

- 导入任务同步到 PostgreSQL。
- 业务空间同步到 PostgreSQL。
- 报告摘要同步到 PostgreSQL。
- 指标目录同步到 PostgreSQL。

### Step 0.15: 编写安全网关

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/core/security.py
```

这一步做了什么：

- 解析 CORS 白名单。
- 校验只读 SQL。
- 禁止危险 SQL。
- 限制 SQL 最大返回行数。
- 设置 SQL 超时。
- 控制 Python 执行开关。
- 校验 Python AST 风险。
- 以临时目录执行 Python 脚本。

SQL 网关规则：

- 允许：`SELECT`、`WITH`、`EXPLAIN`。
- 禁止：`INSERT`、`UPDATE`、`DELETE`、`DROP`、`ALTER`、`TRUNCATE`、`COPY`、`CALL`。
- 禁止多语句。
- 自动加 `LIMIT`。
- 限制查询超时。

为什么不能只靠提示词：

- 大模型可能生成危险 SQL。
- 用户也可能直接输入危险 SQL。
- 安全边界必须落在代码层和工具层。
- Agent 工具的输入输出都应该被验证。

### Step 0.16: 编写审计日志

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/core/audit.py
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/repositories/audit_events.py
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/audit_persistence.py
```

这一步做了什么：

- SQL 放行和拦截都写审计。
- workspace 越权表或未知字段引用写审计。
- 审计默认落 JSONL。
- 可选同步到 PostgreSQL。
- 提供审计查询接口。

审计事件应该记录：

```text
event_type
workspace_id
allowed
reason
query_hash
query_redacted
source
timestamp
```

为什么要做审计：

- 企业 BI 需要知道谁查了什么数据。
- 安全拦截需要可追溯。
- Debug Agent 行为需要查看工具调用和失败原因。
- 后续权限系统也需要审计数据作为基础。

### Step 0.17: 设计 MCP 工具层

MCP 是本项目的核心扩展方式。创建目录：

```text
langGraph_agent/smart_data_analysis_assistant/mcp_server/
```

当前 MCP 服务：

```text
ywfl_mcp.py                 业务分流
python_chart_mcp.py         Python 计算与图表
machine_learning_mcp.py     评论分析、相关性、预测
statistic_db_mcp_tools.py   数据库查询
workspace_mcp.py            业务空间上下文
```

#### 0.17.1 业务分流 MCP

文件：

```text
ywfl_mcp.py
```

工具：

```text
ywfl_tool(user_input)
```

作用：

- 判断用户意图属于普通对话、Python 编程、业务数据查询、数据分析等。
- 帮 LangGraph 决定下一步走哪个节点。

为什么单独做成 MCP：

- 分流逻辑可以独立调试。
- 后续可以替换成更强的分类模型或规则模型。
- 主 Agent 不需要硬编码所有意图判断。

#### 0.17.2 数据库 MCP

文件：

```text
statistic_db_mcp_tools.py
```

工具：

```text
list_tables_tool()
db_sql_tool(query)
```

作用：

- 返回数据库表结构。
- 执行只读 SQL 查询。
- 接入 SQL 安全网关和审计日志。

关键边界：

- 只能查，不能写。
- workspace 模式下只能查当前空间授权表。
- workspace 模式下只能引用授权字段。

#### 0.17.3 Python 图表 MCP

文件：

```text
python_chart_mcp.py
```

工具：

```text
run_python_script_tool(script_content)
```

作用：

- 执行受控 Python 计算。
- 生成 matplotlib 图表。
- 返回计算结果或图表路径。

安全策略：

- 默认 `CHATBI_ENABLE_PYTHON_EXEC=false`。
- 执行前做 AST 校验。
- 使用临时目录。
- 控制超时。
- 限制危险 import 和危险函数。

当前生产建议：

- 如果要生产使用，必须迁移到容器级沙箱。
- 禁止模型任意生成系统命令。
- 输出文件应上传对象存储并返回 URL。

#### 0.17.4 机器学习 MCP

文件：

```text
machine_learning_mcp.py
```

工具：

```text
analysis_product_reviews_tool(reviews_list)
reviews_stars_correlation_test_tool(ItemName, reviews, stars)
sales_predict_tool(ItemName, sales_data_list)
```

作用：

- 评论好坏分析。
- 星级和评论相关性分析。
- 销量预测。

为什么放 MCP：

- 机器学习能力相对独立。
- 后续可以替换为更专业模型。
- Agent 只需要知道工具说明，不需要关心内部算法。

#### 0.17.5 业务空间 MCP

文件：

```text
workspace_mcp.py
```

工具：

```text
list_workspaces_tool(limit)
get_workspace_schema_tool(workspace_id)
get_workspace_analysis_context_tool(workspace_id)
get_workspace_report_summary_tool(workspace_id)
```

作用：

- 让 Agent 主动读取业务空间列表。
- 让 Agent 获取某个空间的字段画像。
- 让 Agent 获取分析上下文、质量评分、推荐路径和报告摘要。
- 让 Agent 在问答前知道当前业务空间有什么数据。

为什么这个 MCP 很重要：

- 早期 Agent 只会查默认样例库。
- 企业 ChatBI 必须知道当前 workspace。
- workspace MCP 把“业务空间”变成工具层可读取资源。
- 后续 RAG、指标口径、字段字典都可以挂到这个 MCP 上。

### Step 0.18: 编写 LangGraph Agent

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/build_graph.py
```

这一步做了什么：

- 连接 5 个 MCP 服务。
- 加载 MCP tools。
- 通过业务分流判断用户意图。
- 对 Python 类任务绑定 Python 工具。
- 对业务数据分析任务绑定数据库、机器学习、图表和 workspace 工具。
- 在 workspace 模式下替换数据库工具为 scoped database tools。

Agent 逻辑可以理解为：

```text
用户问题
  ↓
业务分流节点
  ↓
普通回答 / Python 编程 / 数据分析
  ↓
加载对应工具
  ↓
ReAct Agent 多步调用工具
  ↓
汇总答案
```

workspace-aware 模式额外做：

```text
读取 workspace report
  ↓
构造 workspace chat context
  ↓
构造 workspace SQL policy
  ↓
限制 list_tables_tool 和 db_sql_tool
  ↓
Agent 只能基于当前 workspace 回答
```

为什么这样设计：

- LangGraph 适合把 Agent 流程显式成图。
- MCP 工具让能力扩展更清晰。
- workspace scoped tools 把安全边界下沉到工具层。
- 如果只在 prompt 里说“不要跨空间”，是不可靠的。

### Step 0.19: 编写前端 React 工作台

创建目录：

```text
chatbi-react-ui/
```

核心文件：

```text
chatbi-react-ui/src/main.jsx
chatbi-react-ui/src/styles.css
chatbi-react-ui/src/shared/api/client.js
chatbi-react-ui/src/shared/api/useBiData.js
chatbi-react-ui/src/shared/charts/EChart.jsx
chatbi-react-ui/src/features/import/ImportCleanView.jsx
chatbi-react-ui/src/features/workspaces/WorkspacesView.jsx
chatbi-react-ui/src/features/report/ReportViews.jsx
chatbi-react-ui/src/features/chat/ChatMessages.jsx
```

前端从零要实现：

- API client。
- 导航布局。
- 可折叠侧边栏。
- 首页概览。
- 导入清洗页面。
- 业务空间页面。
- 项目组页面。
- 文件列表。
- 报告封面。
- 报告详情。
- 图表组件。
- 聊天组件。
- 错误、加载、空状态。

为什么页面要分层：

- 如果业务空间入口直接展示所有文件和报告，文件一多就不可用。
- 企业用户更习惯“空间 → 项目组 → 文件 → 报告”的结构。
- 报告默认只展示标题，避免一次性暴露大量内容。

UI 设计原则：

- 米色低饱和背景。
- 左侧导航与主内容区颜色区分。
- 大标题柔和，不做厚重方块感。
- 卡片边框轻、阴影弱。
- 操作按钮少而明确。
- 页面中加入少量英文标签提升精致感，但不影响中文主体阅读。

### Step 0.20: 编写导出能力

创建文件：

```text
langGraph_agent/smart_data_analysis_assistant/chatbi_graph/services/exporters.py
```

这一步做了什么：

- 导出 workspace 报告为 Markdown。
- 导出指标 CSV。
- 导出看板 CSV。
- 提供下载接口。

为什么需要导出：

- 企业分析结果需要进入周报、会议材料或复盘文档。
- 报告只停留在页面里，不利于沉淀。
- 导出能力也是从 Demo 到产品的关键一步。

### Step 0.21: 编写 Docker 部署

创建文件：

```text
.dockerignore
.env.docker.example
docker-compose.yml
docker/backend.Dockerfile
docker/frontend.Dockerfile
docker/nginx.conf
docker/start-backend.sh
```

Docker Compose 服务：

```text
postgres：PostgreSQL 16
backend：FastAPI + 5 个 MCP 服务
frontend：React 静态页面 + Nginx
```

backend 启动脚本会启动：

```text
ywfl_mcp.py
python_chart_mcp.py
machine_learning_mcp.py
statistic_db_mcp_tools.py
workspace_mcp.py
chat_api.py
```

为什么需要 Docker：

- 本地开发依赖多，容易受 Python、Node、PostgreSQL 环境影响。
- Docker Compose 可以一键启动完整演示环境。
- GitHub 项目如果没有部署说明，可复现性会差。
- 企业部署也需要容器化作为基础。

### Step 0.22: 编写测试

创建目录：

```text
tests/
```

当前测试覆盖：

```text
test_security.py                 SQL 和 Python 安全网关
test_audit.py                    JSONL 审计
test_audit_persistence.py        审计 PostgreSQL 持久化
test_import_cleaning.py          导入清洗和 JSON 序列化
test_metadata_persistence.py     元数据持久化
test_reporting_services.py       报告服务
test_services_split.py           服务层拆分行为
test_workspace_sql_scope.py      workspace SQL 边界
test_chat_workspace_context.py   workspace-aware 对话上下文
test_workspace_tools.py          workspace MCP 工具辅助函数
```

为什么测试优先级很高：

- ChatBI 链路长，回归风险高。
- 安全网关、导入清洗、workspace 隔离不能只靠人工点页面。
- Timestamp JSON 序列化这类问题，适合写成测试长期保护。
- 每次架构调整后，测试可以判断是否破坏已有能力。

常用验证命令：

```bash
python -m pytest tests -q
npm --prefix chatbi-react-ui run build
python -m compileall -q langGraph_agent/smart_data_analysis_assistant/chatbi_graph langGraph_agent/smart_data_analysis_assistant/core langGraph_agent/smart_data_analysis_assistant/mcp_server
docker compose config --quiet
```

### Step 0.23: 编写文档

文档至少分三类：

```text
readme.md          GitHub 简略展示文档
README_FULL.md     本地详细说明文档，不上传 GitHub
docs/design_trace.md  从零开发 Trace 和设计说明
```

为什么要分文档：

- GitHub 首页需要短，方便别人快速理解项目。
- 本地详细文档需要长，用来记录架构、接口、安全、部署、规划。
- trace 文档用来解释“为什么这样做”和“从零怎么做”。

文档更新规则：

- 每次代码修改都更新 `readme.md`。
- 如果涉及架构、接口、安全、部署、业务流程，也更新 `README_FULL.md`。
- 如果涉及开发路线或设计思路，也更新 `docs/design_trace.md`。

### Step 0.24: GitHub 提交流程

推荐流程：

```bash
git status --short
git diff --stat
git add <明确文件列表>
git diff --cached --name-only
git commit -m "feat: xxx"
git push origin main
```

项目约束：

- commit / push 必须经过用户确认。
- 不提交 `.env`、`.env.docker`、日志、数据库、本地上传文件、构建产物。
- 不提交 `README_FULL.md`，它是本地详细文档。
- 示例数据可以提交，但需要明确确认。

为什么要先列清单：

- AI 改代码可能产生额外文件。
- GitHub 一旦推送敏感文件，后续清理成本高。
- 明确清单是最基础的工程协作边界。

## 1. 当前项目目标

当前 ChatBI 项目的目标是：

- 支持业务数据上传。
- 自动清洗和字段识别。
- 按业务类型建立业务空间。
- 生成数据画像和质量评分。
- 推荐专属分析路径。
- 生成诊断型业务报告。
- 生成图表并解释图表选择。
- 支持自然语言问数。
- 在 workspace 范围内限制 SQL 查询。
- 提供审计日志。
- 支持 Docker Compose 一键启动。

这个目标对应的是“企业 BI 原型”，不是普通 C 端聊天助手。

## 2. 当前实现 Trace

### Step 1: 工程骨架

已实现：

- Python 后端目录。
- React 前端目录。
- MCP 工具目录。
- 测试目录。
- Docker 目录。
- 简略和详细文档。

关键文件：

```text
chatbi-react-ui/
langGraph_agent/smart_data_analysis_assistant/
tests/
docker/
readme.md
README_FULL.md
```

### Step 2: 后端 API

已实现：

- FastAPI 主服务。
- BI 数据接口。
- 导入清洗接口。
- 业务空间接口。
- 导出接口。
- 审计接口。
- ChatBI 对话接口。

关键文件：

```text
chatbi_graph/chat_api.py
chatbi_graph/bi_api.py
```

当前不足：

- `bi_api.py` 仍偏大。
- 后续应继续拆 routes 和 schemas。

### Step 3: 数据导入清洗

已实现：

- Excel / CSV 上传。
- 批量上传。
- 自动清洗。
- JSON 安全转换。
- 字段角色识别。
- 业务类型识别。
- 入库提交。

关键文件：

```text
services/import_cleaning.py
```

### Step 4: 业务空间

已实现：

- 业务空间列表。
- 业务空间报告。
- workspace-aware 对话上下文。
- workspace SQL 范围控制。
- workspace MCP 工具。

关键文件：

```text
services/workspace_context.py
services/workspace_sql_scope.py
services/workspace_tools.py
mcp_server/workspace_mcp.py
```

### Step 5: 分析报告

已实现：

- 数据画像。
- 质量评分。
- 推荐分析路径。
- 业务方法论。
- 诊断型报告。
- 图表解释。
- 行动建议优先级。

关键文件：

```text
services/profiling.py
services/methodology.py
services/diagnostics.py
services/charts.py
```

### Step 6: Agent 和 MCP

已实现：

- LangGraph Agent。
- 业务分流 MCP。
- 数据库 MCP。
- Python 图表 MCP。
- 机器学习 MCP。
- 业务空间 MCP。
- workspace scoped database tools。

关键文件：

```text
chatbi_graph/build_graph.py
mcp_server/*.py
```

### Step 7: 前端工作台

已实现：

- React + Vite。
- 米色企业工作台 UI。
- 可折叠侧边栏。
- 业务空间分层。
- 导入清洗页面。
- 报告页面。
- 图表页面。
- 聊天页面。

关键文件：

```text
chatbi-react-ui/src/main.jsx
chatbi-react-ui/src/styles.css
chatbi-react-ui/src/features/
chatbi-react-ui/src/shared/
```

### Step 8: 安全和审计

已实现：

- 只读 SQL。
- 危险 SQL 拦截。
- SQL 超时和行数限制。
- workspace 表字段白名单。
- Python 执行默认关闭。
- 审计 JSONL。
- 可选 PostgreSQL 审计。

关键文件：

```text
core/security.py
core/audit.py
repositories/audit_events.py
services/audit_persistence.py
```

### Step 9: Docker 和部署

已实现：

- 后端 Dockerfile。
- 前端 Dockerfile。
- Nginx 配置。
- Docker Compose。
- Docker 环境变量模板。

关键文件：

```text
docker-compose.yml
docker/backend.Dockerfile
docker/frontend.Dockerfile
docker/nginx.conf
docker/start-backend.sh
.env.docker.example
```

### Step 10: 测试

已实现：

- pytest 测试集。
- 前端 build 验证。
- compileall 验证。
- Docker Compose config 验证。

最近验证：

```text
python -m pytest tests -q  → 60 passed
npm --prefix chatbi-react-ui run build  → passed
docker compose config --quiet  → passed
```

## 3. 兜底机制

当前项目已经有部分兜底机制，但还可以继续增强。

### 3.1 导入清洗兜底

已有做法：

- 文件读取失败时返回错误。
- 字段名为空时生成 fallback 字段名。
- 重复字段自动去重。
- Timestamp、NaN、Inf 转成 JSON 安全值。
- 无法识别业务类型时归入通用业务。

后续思路：

- 增加文件大小限制。
- 增加上传格式白名单和 MIME 校验。
- 增加导入任务异步状态。
- 增加清洗前后差异报告。

### 3.2 Agent 兜底

已有做法：

- 先做业务分流。
- workspace 模式下注入空间上下文。
- 数据库工具做二次校验。
- 未入库 workspace 拒绝明细 SQL 查询。

后续思路：

- 限制最大工具调用轮次。
- 工具连续失败时停止而不是继续重试。
- 返回“需要补充字段 / 需要先入库 / 数据不足”的结构化错误。
- 为每次 Agent 执行生成 trace_id。

### 3.3 报告兜底

已有做法：

- 缺少时间字段时不强行做趋势分析。
- 缺少成本字段时不强行做 ROI。
- 数据质量不足时给出限制说明。
- 推荐补充字段。

后续思路：

- 每个结论绑定证据字段和计算口径。
- 为结论增加置信度等级。
- 建立报告评估集。
- 增加人工确认或编辑报告能力。

## 4. 质量校验

项目质量校验分四类。

### 4.1 单元测试

```bash
python -m pytest tests -q
```

覆盖安全、清洗、审计、元数据、报告、workspace 边界。

### 4.2 前端构建

```bash
npm --prefix chatbi-react-ui run build
```

验证 React 代码可构建。

### 4.3 Python 编译

```bash
python -m compileall -q langGraph_agent/smart_data_analysis_assistant/chatbi_graph langGraph_agent/smart_data_analysis_assistant/core langGraph_agent/smart_data_analysis_assistant/mcp_server
```

验证 Python 语法和 import 基础正确。

### 4.4 Docker 配置

```bash
docker compose config --quiet
```

验证 Docker Compose 配置合法。

## 5. 后续可扩展点

优先级建议：

### P0: 权限和租户

- 增加用户登录。
- 增加 workspace owner / member / role。
- 增加字段脱敏。
- 增加行级权限。

### P1: 异步任务

- 导入清洗改成异步任务。
- 报告生成改成异步任务。
- 前端轮询或 WebSocket 查看状态。

### P1: 报告证据链

- 每条结论绑定指标证据。
- 输出计算口径。
- 输出置信度。
- 输出限制和下一步验证。

### P2: 前端架构

- 继续瘦身 `main.jsx`。
- 建立统一状态管理。
- 抽象通用表格、筛选器、图表容器。

### P2: 指标治理

- 指标口径管理。
- 字段字典管理。
- 指标血缘。
- 指标版本。

### P3: 企业 RAG

当前 RAG 先保留入口，等有高质量材料后再做：

- 指标口径文档。
- 字段字典。
- 历史报告。
- 业务术语库。
- 决策复盘。

## 6. MCP 深度设计：为什么要用 MCP，怎么做，边界在哪里

### 6.1 MCP 在本项目里解决什么问题

MCP 解决的是“Agent 工具边界和可扩展性”问题。

如果没有 MCP，所有工具函数都可能写在 Agent 文件里：

```text
build_graph.py
  ├── 查库函数
  ├── Python 执行函数
  ├── 机器学习函数
  ├── 业务空间函数
  └── 分流函数
```

这样会导致：

- Agent 文件越来越大。
- 工具难以独立测试。
- 工具无法独立启动或替换。
- 安全策略容易散落。
- 后续接新工具成本高。

使用 MCP 后：

```text
Agent 只负责决策和调度
MCP Server 负责具体工具能力
安全校验放在工具内部
工具可以独立启动、独立调试、独立扩展
```

### 6.2 当前 MCP 服务边界

| MCP | 负责什么 | 不负责什么 |
| --- | --- | --- |
| 业务分流 MCP | 判断任务类型 | 不直接查库、不生成报告 |
| 数据库 MCP | 表结构、只读 SQL | 不做写入、不绕过 SQL 网关 |
| Python 图表 MCP | 受控计算和绘图 | 默认不允许任意执行 |
| 机器学习 MCP | 评论分析、相关性、预测 | 不负责业务空间隔离 |
| 业务空间 MCP | 空间上下文、schema、报告摘要 | 不直接修改 workspace |

这个边界的原则是：

- 一个 MCP 做一类事情。
- 工具输入尽量结构化。
- 工具内部必须做安全校验。
- Agent 不能绕过工具直接访问底层资源。

### 6.3 新增 MCP 的标准流程

如果后续要新增一个 MCP，例如“指标口径 MCP”，建议流程：

1. 在 `mcp_server/` 下创建新文件，例如 `metric_catalog_mcp.py`。
2. 用 `FastMCP` 创建服务，指定 host 和 port。
3. 用 `@mcp.tool()` 暴露工具函数。
4. 工具函数只返回必要数据，不返回敏感字段。
5. 在 `build_graph.py` 的 MCP 配置中加入该服务。
6. 启动脚本 `docker/start-backend.sh` 加入该 MCP。
7. Docker Compose 暴露必要端口，或仅容器内部访问。
8. 为工具逻辑补测试。
9. 更新 `readme.md`、`README_FULL.md` 和本 trace 文档。

示例结构：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="metric_catalog_mcp",
    instructions="指标口径 MCP",
    host="0.0.0.0",
    port=9007,
)

@mcp.tool()
async def get_metric_definition_tool(metric_name: str) -> str:
    """查询指标口径。"""
    ...

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### 6.4 MCP 工具安全要求

每个 MCP 工具至少要考虑：

- 输入类型校验。
- 空值和异常输入处理。
- 权限边界。
- 最大返回长度。
- 超时。
- 审计日志。
- 是否会访问文件系统。
- 是否会访问数据库。
- 是否可能执行代码。

数据库 MCP 的安全优先级最高：

- 必须只读。
- 必须限制行数。
- 必须限制超时。
- 必须审计。
- workspace 模式必须限制表和字段。

Python MCP 的安全风险也很高：

- 默认关闭。
- 生产必须容器隔离。
- 禁止系统命令。
- 禁止任意文件读写。
- 限制 import。
- 限制输出目录。

### 6.5 MCP 和 RAG 的关系

RAG 暂时不深入做，但后续可以通过 MCP 接入。

推荐做法：

```text
rag_mcp.py
  ├── search_metric_docs_tool(query, workspace_id)
  ├── search_data_dictionary_tool(query, workspace_id)
  ├── search_report_history_tool(query, workspace_id)
  └── get_term_definition_tool(term)
```

边界：

- RAG 用于解释口径、补充背景、查历史报告。
- RAG 不替代 SQL 查询。
- 数值结论必须来自数据库或上传数据计算。
- RAG 返回内容必须带来源。
- 如果没有来源，不能当事实写入报告。

## 7. Agent 深度设计：业务价值、工具边界、自主决策和防循环

### 7.1 Agent 解决什么业务问题

Agent 的价值不是“聊天”，而是把多步分析流程自动化：

```text
用户问题：为什么这个业务空间销售额下滑？
  ↓
判断问题属于业务分析
  ↓
读取 workspace schema 和报告摘要
  ↓
判断需要查趋势、维度贡献、异常周期
  ↓
调用数据库工具查询当前空间数据
  ↓
必要时调用 Python 或统计工具
  ↓
形成解释和下一步建议
```

传统 BI 用户需要自己知道表、字段、SQL、图表和分析方法。Agent 的作用是把这些步骤串起来。

### 7.2 Agent 什么时候自主决策

适合自主决策：

- 选择查询哪些字段。
- 选择调用哪个工具。
- 选择图表类型。
- 选择先看趋势还是先看维度贡献。
- 对已有数据做解释。

不适合自主决策：

- 删除或修改数据。
- 执行写 SQL。
- 打开 Python 任意执行。
- 跨 workspace 查询。
- 使用没有来源的 RAG 内容当事实。
- 在数据不足时编造结论。

### 7.3 工具边界怎么做

工具边界分三层：

1. **Prompt 层**：告诉 Agent 应该怎么做。
2. **工具层**：工具自己校验输入，拒绝危险操作。
3. **服务层**：SQL、安全、审计、workspace scope 做最终兜底。

不能只做第 1 层。

原因：

- Prompt 不是安全边界。
- 模型可能误解或忽略约束。
- 用户可以诱导模型生成危险请求。
- 工具层和服务层必须强制执行规则。

### 7.4 什么情况必须人工介入

建议人工介入的场景：

- 数据质量评分过低。
- 缺少核心指标字段。
- 缺少时间字段但用户要求趋势分析。
- 用户要求跨业务空间合并分析。
- 用户要求执行写入、删除或修改数据。
- 需要解释企业内部专有指标但没有指标口径文档。
- 模型连续工具调用失败。

此时系统应该返回清晰提示，而不是继续胡乱分析。

### 7.5 怎么防止 Agent 无限循环

当前可以继续增强：

- 限制最大工具调用次数。
- 同一工具相同参数失败后不重复调用。
- 连续 SQL 被拦截后停止。
- 连续缺字段后要求用户补充数据。
- 每次 Agent 执行生成 trace。
- 工具调用日志写入审计或 trace 表。

### 7.6 Agent trace 应记录什么

建议记录：

```text
trace_id
user_id
workspace_id
user_message
intent
selected_tools
tool_calls
tool_inputs_redacted
tool_outputs_summary
sql_decisions
errors
final_answer
created_at
```

为什么要记录：

- 方便排查错误回答。
- 方便评估 Agent 是否乱调工具。
- 方便安全审计。
- 方便后续做评估集。

当前已有审计日志，但还不是完整 Agent trace。后续可以新增 `chatbi_agent_trace` 表。

## 8. RAG 设计思路：目前不做，后续怎么做

当前 RAG 不作为重点，因为没有高质量业务知识库。强行做 RAG 会引入噪声。

### 8.1 RAG 应该接什么数据

适合接入：

- 指标口径文档。
- 字段字典。
- 数据表说明。
- 历史分析报告。
- 业务术语。
- 经营复盘。
- SOP 和分析模板。

不适合接入：

- 未清洗的聊天记录。
- 过时口径。
- 没有来源的总结。
- 与当前业务无关的资料。

### 8.2 RAG 在 ChatBI 里的边界

RAG 只负责：

- 解释业务术语。
- 解释指标口径。
- 补充背景知识。
- 推荐分析方法。
- 查找历史类似报告。

RAG 不负责：

- 直接生成数值结论。
- 替代 SQL 查询。
- 替代上传数据计算。
- 在没有来源时编造事实。

### 8.3 推荐实现路径

后续可以这样做：

1. 建立 `knowledge_source` 表。
2. 建立 `knowledge_chunk` 表。
3. 为每个 chunk 保存 source、workspace_id、doc_type、updated_at。
4. 接入 embedding 模型。
5. 增加 hybrid search：关键词 + 向量。
6. 增加 rerank。
7. 返回引用来源。
8. 把 RAG 工具做成 `rag_mcp.py`。
9. Agent 使用 RAG 时必须说明来源。

## 9. 当前项目不足和下一步优先级

### P0: 企业安全

- 用户登录和租户隔离。
- workspace 角色权限。
- 字段脱敏。
- 更强 Python 沙箱。
- 审计检索权限。

### P1: 工程结构

- 继续拆 `bi_api.py`。
- 继续拆 `main.jsx`。
- 建立更清晰的 routes / schemas。
- 导入和报告改异步任务。

### P1: 分析质量

- 报告结论绑定证据链。
- 建立评估集。
- 指标口径管理。
- 报告人工编辑能力。

### P2: 产品体验

- workspace 搜索和筛选。
- 项目组后端持久化。
- 图表 drill-down。
- 报告版本管理。

### P3: 企业 RAG

- 等高质量知识库资料准备好后再做。
- 优先接指标口径和字段字典，不要先接杂乱文档。

## 10. 总结

从零开发这个项目的关键不是先写聊天框，而是先建立正确链路：

```text
数据治理 → 业务空间 → 分析方法论 → 诊断报告 → 图表解释 → workspace-aware Agent → 安全审计 → 可部署验证
```

这个项目目前已经具备 ChatBI 原型的主要骨架：

- React 前端工作台。
- FastAPI 后端。
- LangGraph Agent。
- 5 个 MCP 服务。
- 文件导入和自动清洗。
- 业务空间隔离。
- 数据画像和质量评分。
- 诊断型报告。
- 图表和图表解释。
- workspace-aware 问数。
- SQL 安全网关。
- 审计日志。
- Docker Compose。
- pytest 测试。

如果继续推进，下一阶段应该优先做：权限体系、异步任务、报告证据链、指标口径管理和更完整的 Agent trace。这样项目会从“可展示原型”继续向“可治理企业级产品”靠近。
