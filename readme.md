# ChatBI 数据分析助手

一个基于 **LangGraph + MCP + FastAPI + React** 的企业级 ChatBI 原型项目。  
系统支持上传业务数据、自动清洗、生成业务空间、输出诊断型分析报告，并通过对话方式完成数据查询、图表分析和经营洞察。

## 项目亮点

- **自然语言问数**：通过大模型理解业务问题，并调用 SQL / Python / 分析工具完成回答。
- **自动导入清洗**：支持 CSV、XLSX、XLS 文件上传，自动处理空值、重复行、字段标准化和类型转换。
- **业务空间管理**：上传数据后自动形成独立业务空间，避免不同业务数据混用。
- **诊断型报告**：报告结构从描述统计升级为「现象 → 对比 → 异常 → 归因假设 → 行动建议」。
- **图表分析**：支持柱形图、折线图、饼图、散点图，并说明每张图回答的业务问题。
- **企业安全治理**：内置只读 SQL 网关、workspace 表/字段白名单、CORS 白名单、Python 执行隔离和审计日志。
- **可选审计落库**：SQL 审计事件默认写入 JSONL，也可同步到 PostgreSQL 审计表。
- **可选 RAG 模块**：预留企业知识库入口，后续可接入指标口径、数据字典和历史报告。

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
- 可选 RAG 知识库

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

## 验证命令

后端测试：

```bash
python -m pytest tests -q
```

前端构建：

```bash
npm --prefix chatbi-react-ui run build
```

## 安全说明

- 数据库查询默认只允许 `SELECT / WITH / EXPLAIN`。
- workspace 模式下只能访问当前业务空间的数据表和字段。
- 默认关闭任意 Python 代码执行。
- 审计日志默认写入本地 JSONL，可选同步到 PostgreSQL。
- `.env`、上传数据、日志、PostgreSQL 数据目录和构建产物已通过 `.gitignore` 排除。

## 项目定位

本项目适合作为：

- ChatBI / AI BI 原型项目
- 企业数据分析助手 Demo
- LangGraph + MCP 工具调用实践
- 数据清洗、业务报告和自然语言问数的一体化样例

## 后续规划

- 审计日志权限体系
- 租户级数据隔离
- 异步导入任务
- Docker Compose 一键部署
- 更完整的指标口径管理
- 企业 RAG 知识库接入

