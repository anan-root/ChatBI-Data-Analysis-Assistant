"""
本文件用于对项目进行API封装部署
"""
import os
import sys
import shutil
import tempfile
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append("/root/wangshihang/langGraph_agent/smart_data_analysis_assistant")
sys.path.append("/root/wangshihang/langGraph_agent/smart_data_analysis_assistant/chatbi_graph")
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
import asyncio
from build_graph import get_message_text, make_graph
import time
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
import hashlib
import time
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, StreamingResponse
from fastapi import File, Form, UploadFile, WebSocket, WebSocketDisconnect
from concurrent.futures import ThreadPoolExecutor
import asyncio
import os
import sys
import datetime
from collections import defaultdict
import json
from fastapi import WebSocket, WebSocketDisconnect, Query
from async_timeout import timeout  # 确保安装了 async-timeout 库
from chat_context import UserInput, build_workspace_system_message
from bi_api import (
    build_ai_eval_data,
    build_anomaly_data,
    build_audit_log_data,
    build_dashboard_data,
    build_workspace_chat_context,
    build_import_clean_data,
    build_metric_definitions,
    build_monetization_data,
    build_report_data,
    build_rag_data,
    build_sql_analysis_data,
    build_user_growth_data,
    build_workspace_report,
    commit_import_job,
    commit_import_jobs,
    get_import_job,
    get_import_job_file,
    init_audit_log_storage,
    init_metadata_storage,
    list_business_workspaces,
    list_import_jobs,
    migrate_metadata_storage,
    migrate_audit_logs_to_postgres,
    process_import_file,
    write_dashboard_csv_file,
    write_metrics_csv_file,
    write_report_markdown_file,
    write_workspace_report_markdown_file,
)
from core.security import parse_cors_origins
from core.audit import audit_admin_token
from services.agent_trace import (
    build_evidence,
    build_trace,
    infer_intent_from_route,
    new_trace_id,
    step_from_ai_message,
    step_from_tool_message,
)
from services.knowledge_base import search_knowledge

app = FastAPI()
allowed_origins = parse_cors_origins(os.getenv("CHATBI_CORS_ORIGINS"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
class ImportCommitInput(BaseModel):
    table_name: str | None = None


class BatchCommitInput(BaseModel):
    job_ids: list[str]


class MetadataMigrationInput(BaseModel):
    limit: int | None = None


@app.post("/bi/audit/init")
async def bi_audit_init(x_chatbi_admin_token: str | None = Header(default=None)):
    expected_token = audit_admin_token()
    if expected_token and x_chatbi_admin_token != expected_token:
        raise HTTPException(status_code=403, detail="审计日志需要管理员令牌。")
    try:
        return init_audit_log_storage()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"初始化审计表失败：{exc}") from exc


@app.post("/bi/audit/migrate")
async def bi_audit_migrate(payload: MetadataMigrationInput, x_chatbi_admin_token: str | None = Header(default=None)):
    expected_token = audit_admin_token()
    if expected_token and x_chatbi_admin_token != expected_token:
        raise HTTPException(status_code=403, detail="审计日志需要管理员令牌。")
    try:
        return migrate_audit_logs_to_postgres(payload.limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"迁移审计日志失败：{exc}") from exc


@app.get("/bi/audit")
async def bi_audit(
    limit: int = Query(200, ge=1, le=1000),
    event_type: str | None = None,
    workspace_id: str | None = None,
    allowed: bool | None = None,
    source: str | None = None,
    x_chatbi_admin_token: str | None = Header(default=None),
):
    expected_token = audit_admin_token()
    if expected_token and x_chatbi_admin_token != expected_token:
        raise HTTPException(status_code=403, detail="审计日志需要管理员令牌。")
    return build_audit_log_data(
        limit=limit,
        event_type=event_type,
        workspace_id=workspace_id,
        allowed=allowed,
        source=source,
    )


@app.get("/bi/dashboard")
async def bi_dashboard():
    return build_dashboard_data()


@app.get("/bi/metrics")
async def bi_metrics():
    return {"metrics": build_metric_definitions()}


@app.get("/bi/anomalies")
async def bi_anomalies():
    return build_anomaly_data()


@app.get("/bi/report")
async def bi_report():
    return build_report_data()


@app.get("/bi/workspaces")
async def bi_workspaces():
    return list_business_workspaces()


@app.get("/bi/workspaces/{workspace_id}/report")
async def bi_workspace_report(workspace_id: str):
    try:
        return build_workspace_report(workspace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/bi/workspaces/{workspace_id}/export-report")
async def bi_workspace_export_report(workspace_id: str):
    try:
        output_file = write_workspace_report_markdown_file(workspace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(output_file, filename=output_file.name, media_type="text/markdown")


@app.get("/bi/sql-analysis")
async def bi_sql_analysis():
    return build_sql_analysis_data()


@app.get("/bi/import-clean")
async def bi_import_clean():
    return build_import_clean_data()


@app.get("/bi/import-clean/jobs")
async def bi_import_jobs():
    return list_import_jobs()


@app.post("/bi/metadata/init")
async def bi_metadata_init():
    try:
        return init_metadata_storage()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"初始化元数据表失败：{exc}") from exc


@app.post("/bi/metadata/migrate")
async def bi_metadata_migrate(payload: MetadataMigrationInput):
    try:
        return migrate_metadata_storage(payload.limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"迁移元数据失败：{exc}") from exc


@app.post("/bi/import-clean/upload")
async def bi_import_upload(file: UploadFile = File(...)):
    filename = file.filename or "uploaded.csv"
    suffix = os.path.splitext(filename)[1].lower()
    if suffix not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="仅支持 CSV、XLSX、XLS 文件。")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    try:
        return process_import_file(temp_path, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导入清洗失败：{exc}") from exc
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@app.post("/bi/import-clean/upload-batch")
async def bi_import_upload_batch(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="请选择至少一个文件。")
    results = []
    for file in files:
        filename = file.filename or "uploaded.csv"
        suffix = os.path.splitext(filename)[1].lower()
        if suffix not in [".csv", ".xlsx", ".xls"]:
            results.append({"filename": filename, "ok": False, "detail": "仅支持 CSV、XLSX、XLS 文件。"})
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name

        try:
            results.append({"filename": filename, "ok": True, "job": process_import_file(temp_path, filename)})
        except ValueError as exc:
            results.append({"filename": filename, "ok": False, "detail": str(exc)})
        except Exception as exc:
            results.append({"filename": filename, "ok": False, "detail": f"导入清洗失败：{exc}"})
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
    return {
        "total": len(files),
        "success": sum(1 for item in results if item.get("ok")),
        "failed": sum(1 for item in results if not item.get("ok")),
        "results": results,
    }


@app.get("/bi/import-clean/jobs/{job_id}")
async def bi_import_job(job_id: str):
    try:
        return get_import_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/bi/import-clean/jobs/{job_id}/download")
async def bi_import_download(job_id: str):
    try:
        metadata, cleaned_file = get_import_job_file(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    download_name = f"cleaned_{os.path.splitext(metadata['originalFilename'])[0]}.csv"
    return FileResponse(cleaned_file, filename=download_name, media_type="text/csv")


@app.post("/bi/import-clean/jobs/{job_id}/commit")
async def bi_import_commit(job_id: str, payload: ImportCommitInput):
    try:
        return commit_import_job(job_id, payload.table_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"确认入库失败：{exc}") from exc


@app.post("/bi/import-clean/jobs/batch-commit")
async def bi_import_batch_commit(payload: BatchCommitInput):
    if not payload.job_ids:
        raise HTTPException(status_code=400, detail="请选择至少一个导入任务。")
    return commit_import_jobs(payload.job_ids)


@app.get("/bi/export/report")
async def bi_export_report():
    output_file = write_report_markdown_file()
    return FileResponse(output_file, filename=output_file.name, media_type="text/markdown")


@app.get("/bi/export/metrics")
async def bi_export_metrics():
    output_file = write_metrics_csv_file()
    return FileResponse(output_file, filename=output_file.name, media_type="text/csv")


@app.get("/bi/export/dashboard")
async def bi_export_dashboard():
    output_file = write_dashboard_csv_file()
    return FileResponse(output_file, filename=output_file.name, media_type="text/csv")


@app.get("/bi/user-growth")
async def bi_user_growth():
    return build_user_growth_data()


@app.get("/bi/monetization")
async def bi_monetization():
    return build_monetization_data()


@app.get("/bi/rag")
async def bi_rag():
    return build_rag_data()


@app.get("/bi/ai-eval")
async def bi_ai_eval():
    return build_ai_eval_data()


@app.post("/chatbi_service")
async def chatbi_server(user_input: UserInput):
    print("user_input:",user_input)
    user_id=user_input.user_id
    user_message=user_input.message
    history=list(user_input.history or [])
    trace_id = new_trace_id()
    trace_steps = []
    intent = "unknown"
    workspace_context = None
    if user_input.workspace_id:
        try:
            workspace_context = build_workspace_chat_context(user_input.workspace_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    knowledge_references = search_knowledge(user_message, workspace_context)
    if workspace_context:
        workspace_context = {**workspace_context, "knowledgeReferences": knowledge_references}
    history.append({"role": "user", "content": user_message})
    print(f"用户Id:{user_id},本轮输入:{user_message},历史记录:{history}")
    graph_messages = history
    if workspace_context:
        graph_messages = [build_workspace_system_message(workspace_context), *history]
    # thread_config = {"configurable": {"thread_id": user_id}}

    async with make_graph(workspace_context=workspace_context) as graph:
        print("创建图成功")
        fallback_result = None
        async for event in graph.astream({"messages":graph_messages},
                                         config={"recursion_limit": 8},
                                         stream_mode="values"):  # 保持同一个用户的对话的连续记忆 , config=thread_config
            print("event:",event)
            # Emit all values in the state after each step, including interrupts.When used with functional API, values are emitted once at the end of the workflow.
            messages = event.get('messages')
            event["messages"][-1].pretty_print()
            print("messages:xxxxxxxxxxx",messages)
            if messages:
                if isinstance(messages, list):
                    message = messages[-1]  # 如果消息是列表，则取最后一个
                if message.__class__.__name__ == 'AIMessage':
                    trace_steps.extend(step_from_ai_message(message))
                    if message.content and not message.tool_calls: #是AIMessage且不是工具调用类消息(是正常回复类的消息)
                        result = message.content  # 需要回传消息
                        print("本轮回复:",result)
                        trace = build_trace(trace_id, intent, workspace_context, trace_steps)
                        evidence = build_evidence(workspace_context, trace_steps, knowledge_references)
                        return {"message": result, "trace": trace, "evidence": evidence}
                elif message.__class__.__name__ == 'ToolMessage':
                    tool_result = get_message_text(message)
                    if tool_result in ["纯python编码", "业务数据查询分析"]:
                        intent = infer_intent_from_route(tool_result)
                        trace_steps.append(
                            {
                                "stage": "intent",
                                "node": "identify_intention_tool_node",
                                "toolName": getattr(message, "name", "") or "ywfl_tool",
                                "status": "ok",
                                "summary": f"意图识别结果：{tool_result}",
                                "sql": "",
                                "reason": "",
                            }
                        )
                    else:
                        trace_steps.append(step_from_tool_message(message, get_message_text))
                    if tool_result and tool_result not in ["纯python编码", "业务数据查询分析"]:
                        fallback_result = tool_result
                else:
                    print("中间处理消息:",message)
        if fallback_result:
            print("本轮工具回复:", fallback_result)
            trace = build_trace(trace_id, intent, workspace_context, trace_steps)
            evidence = build_evidence(workspace_context, trace_steps, knowledge_references)
            return {"message": fallback_result, "trace": trace, "evidence": evidence}
        fallback_message = "本轮流程已结束，但没有生成可返回的结果。请换一种问法重试。"
        trace = build_trace(trace_id, intent, workspace_context, trace_steps)
        evidence = build_evidence(workspace_context, trace_steps, knowledge_references)
        return {"message": fallback_message, "trace": trace, "evidence": evidence}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9008)

# nohup uvicorn chat_api:app --host 0.0.0.0 --port 9008 --workers 1 &
