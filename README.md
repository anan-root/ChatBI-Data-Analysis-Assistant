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
- React 工作台：提供 Notion 风格的企业级数据问答、业务空间、看板、指标、异常、增长、变现、导入导出和可选 RAG 模块。

## 技术栈

- **Agent 编排**：LangGraph
- **工具协议**：MCP、langchain-mcp-adapters
- **大模型调用**：DeepSeek、通义千问兼容 OpenAI SDK 接口
- **后端服务**：FastAPI、Uvicorn
- **前端界面**：React、Vite
- **前端可视化**：ECharts、echarts-for-react、lucide-react
- **数据库**：PostgreSQL
- **数据处理**：pandas、numpy、scipy
- **可视化**：matplotlib

## 目录结构

```text
.
├── requirements.txt
├── MCP+LangGraph构建专属 ChatBI 数据分析智能助手.md
├── 2.ChatBI数据分析助手问题.md
├── 整体架构.png
├── langGraph图.jpg
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
        │   ├── execute_graph.py
        │   ├── chat_api.py
        │   ├── my_llm.py
        │   ├── my_state.py
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
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/execute_graph.py` | 命令行交互式运行入口 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/chat_api.py` | FastAPI 接口服务入口 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/my_llm.py` | 大模型配置 |
| `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/my_state.py` | LangGraph 状态定义 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/ywfl_mcp.py` | 业务分流 MCP 服务 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/statistic_db_mcp_tools.py` | 数据库查询 MCP 服务 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/python_chart_mcp.py` | Python 代码执行与绘图 MCP 服务 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/machine_learning_mcp.py` | 评论分析、相关性分析、销量预测 MCP 服务 |
| `langGraph_agent/smart_data_analysis_assistant/mcp_server/multi_mcp_client.py` | 多 MCP Server 客户端测试示例 |

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
```

> 注意：`my_llm.py` 会读取大模型密钥；如果本地运行时读取不到环境变量，可以把同样的 `.env` 复制到 `langGraph_agent/smart_data_analysis_assistant/chatbi_graph/`，或在启动前手动导出环境变量。

> GitHub 上传注意：真实 `.env`、PostgreSQL 数据目录 `pgdata/`、日志 `logs/`、上传清洗数据 `import_jobs/`、导出报告 `exports/`、前端依赖 `node_modules/`、构建产物 `dist/`、课程 PDF/Word/Excel 数据和生成图片已在 `.gitignore` 中排除，避免泄露密钥、提交本地运行数据或公开私有学习资料。

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

前端位于 `chatbi-react-ui/`，采用 Notion 风格工作区 UI，包含：

- `数据问答`：普通聊天式业务查询与分析。
- `业务空间`：按上传文件隔离业务上下文，每个上传表生成自己的分析报告，避免和默认样例业务混用。
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
| `GET /bi/workspaces` | 返回上传文件形成的业务空间列表 |
| `GET /bi/workspaces/{workspace_id}/report` | 返回某个上传表的独立分析报告 |
| `GET /bi/workspaces/{workspace_id}/export-report` | 导出某个上传表的独立报告 Markdown |
| `GET /bi/import-clean` | 返回导入、自动清洗、字段映射和导出流程 |
| `GET /bi/import-clean/jobs` | 返回最近导入清洗任务 |
| `POST /bi/import-clean/upload` | 上传 CSV/XLSX/XLS 文件并自动清洗，返回清洗报告和预览 |
| `GET /bi/import-clean/jobs/{job_id}` | 查询单个导入清洗任务详情 |
| `GET /bi/import-clean/jobs/{job_id}/download` | 下载清洗后的 CSV 文件 |
| `POST /bi/import-clean/jobs/{job_id}/commit` | 将清洗后的数据确认写入 PostgreSQL 新表 |
| `GET /bi/export/report` | 导出结构化分析报告 Markdown |
| `GET /bi/export/metrics` | 导出指标体系 CSV |
| `GET /bi/export/dashboard` | 导出看板核心数据 CSV |
| `GET /bi/rag` | 返回可选 RAG 知识库定位、场景和建议技术栈 |

导入清洗接口会在 `langGraph_agent/smart_data_analysis_assistant/import_jobs/` 下保存任务元数据和清洗后的 CSV 文件；确认入库时会新建 `import_` 前缀的数据表，避免覆盖原业务表。

Excel 导入时，日期字段会自动转换为可 JSON 序列化的时间字符串，避免 `Timestamp is not JSON serializable` 这类错误。

上传文件默认会形成一个独立业务空间。默认 BI 看板和默认分析报告仍基于项目样例电商库；上传表的报告需要在 `业务空间` 或 `导入导出` 模块中查看，系统会基于该表字段自动识别业务类型、主指标、维度和时间趋势。

业务空间报告会先执行一个轻量的 AI 前期判断步骤：根据文件名、行列规模、字段名、字段角色画像和业务关键词识别业务类型、主指标、核心维度，并选择合适的分析方案。该预判阶段采用 `schema-only` 策略，只传输文件名、行列数、字段名和字段角色，不传输数据明细，以提升判断速度并减少 token 消耗。

为了支撑 `schema-only` 预判，导入清洗会先做字段标准化、空白值处理、类型识别、日期转换、数值转换、去重和字段角色提取。字段角色包括 `metric`、`dimension`、`time`、`identifier`，后续报告再基于清洗后的聚合数据生成图表和详细结论。

业务空间报告会尽量串联现有业务模块：`指标体系`、`BI 看板口径`、`业务监控与异常`、`用户/客户增长分析`、`变现与成本分析`、`SQL 分析模板`、`导入清洗质量` 和 `报告导出`。如果上传表缺少某类字段，例如成本字段或时间字段，对应模块会给出补字段建议，而不是混用默认样例业务数据。

业务空间报告新增 Tableau 式诊断层：每份报告会根据业务类型选择专属方法论，例如 `销售漏斗`、`客户分层`、`区域效率`、`产品结构`、`ROI`、`留存`、`复购`、`指标树拆解` 和 `趋势异常`。报告不只输出描述统计，还会补充 `归因诊断`、`异常原因假设`、`对比基准`、`轻量显著性/可信度判断` 和 `策略建议优先级`，方便企业经营例会直接讨论。

业务空间报告会按数据特征自动选择图表：维度贡献适合 `柱形图`，结构占比适合 `饼状图`，时间字段适合 `折线图`，两个数值字段适合 `散点图`。前端使用 ECharts 渲染这些图表，并在每张图上展示 `该图回答什么业务问题`、`为什么使用这个图` 和 `如何解读`，减少模板化图表堆叠。

请求示例：

```json
{
  "user_id": "session_1",
  "message": "查询商品洗碗布的月销量数据，并绘制一张柱状图",
  "history": []
}
```

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

- Python 代码执行当前仍在本地进程中执行，生产环境建议放入 Docker 沙箱并限制权限、网络和资源。
- SQL 执行工具需要增加更严格的只读校验，避免执行 DML/DDL 语句。
- 会话历史目前主要由请求侧传入或内存维护，生产环境建议落库并做摘要压缩。
- 图表结果当前返回本地路径，生产环境建议上传对象存储并返回 URL。
- 部分文件中存在 Linux 服务器绝对路径示例，本地运行时可能需要调整 `sys.path` 或工作目录。

## 后续优化方向

- 引入 SQL 静态检查与字段白名单，降低幻觉字段风险。
- 引入 Schema RAG，在大库多表场景下只召回相关表结构。
- 增加 Prompt 配置化和版本管理。
- 增加任务状态流式输出或 WebSocket 推送。
- 增加缓存层，复用高频查询结果。
- 增加测试集和 Eval 流程，稳定评估 Text-to-SQL、图表生成和总结质量。

## 参考资料

- `MCP+LangGraph构建专属 ChatBI 数据分析智能助手.md`
- `2.ChatBI数据分析助手问题.md`
- `整体架构.png`
- `langGraph图.jpg`
