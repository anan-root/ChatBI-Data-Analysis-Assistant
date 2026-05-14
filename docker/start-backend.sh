#!/usr/bin/env sh
set -eu

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup INT TERM EXIT

cd /app/langGraph_agent/smart_data_analysis_assistant/mcp_server
python -u ywfl_mcp.py &
python -u python_chart_mcp.py &
python -u machine_learning_mcp.py &
python -u statistic_db_mcp_tools.py &
python -u workspace_mcp.py &

cd /app/langGraph_agent/smart_data_analysis_assistant/chatbi_graph
python -m uvicorn chat_api:app --host 0.0.0.0 --port 9008 &
api_pid="$!"

wait "$api_pid"
