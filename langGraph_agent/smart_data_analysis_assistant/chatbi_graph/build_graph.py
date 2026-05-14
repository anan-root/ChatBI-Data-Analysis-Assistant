import sys
import os
# 添加当前项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from contextlib import asynccontextmanager
from typing import Literal
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from my_llm import llm
from my_state import BIState
from tools_node import generate_query_system_prompt, query_check_system, call_get_schema, select_deep_data_analysis_system_prompt,get_schema_tool,get_schema_node
from langchain_core.messages import SystemMessage, HumanMessage,ToolMessage
from langgraph.checkpoint.memory import MemorySaver
import matplotlib.image as mpimg
from matplotlib import pyplot as plt
from io import BytesIO
import os
from dotenv import load_dotenv
from time import perf_counter
try:
    from langchain_core.tools import tool
except ImportError:
    tool = None

try:
    from services.workspace_sql_scope import (
        build_workspace_sql_policy_text,
        build_workspace_sql_scope,
        format_workspace_table_schema,
        validate_workspace_sql_scope,
    )
except ImportError:
    from .services.workspace_sql_scope import (
        build_workspace_sql_policy_text,
        build_workspace_sql_scope,
        format_workspace_table_schema,
        validate_workspace_sql_scope,
    )
# 加载环境变量
load_dotenv()
#加载MCP服务器址的地：121.34.54.32
server_url=os.getenv("server_url")

def log_step(message: str):
    print(f"[graph {perf_counter():.3f}] {message}", flush=True)

#数据库查询MCP
mcp_server_config = {
    "search_db_mcp":{
    "url": f"http://{server_url}:9004/sse",
    "transport": "sse",
    "timeout": 20000,  # 增加超时时间
    "sse_read_timeout": 20000
},
#机器学习MCP
"machine_learning_mcp":{
    "url": f"http://{server_url}:9003/mcp",
    "transport": "streamable_http",
    "timeout": 20000,  # 机器学习时间需要久一些
    "sse_read_timeout": 20000
},
#生成python代码，执行python程序的MCP
"python_chart_mcp":{
    "url": f"http://{server_url}:9002/mcp",
    "transport": "streamable_http",
    "timeout": 20000,  # 机器学习时间需要久一些
    "sse_read_timeout": 20000
},
#业务分流MCP
"ywfl_mcp":{
    "url": f"http://{server_url}:9005/mcp",
    "transport": "streamable_http",
    "timeout": 20000.0,  # 机器学习时间需要久一些
    "sse_read_timeout": 20000.0
},
"workspace_mcp":{
    "url": f"http://{server_url}:9006/mcp",
    "transport": "streamable_http",
    "timeout": 20000.0,
    "sse_read_timeout": 20000.0
},
}
from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
class PythonState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages] #消息追加的模式增加消息

def get_message_text(message) -> str:
    """兼容不同 MCP adapter 版本返回的消息内容格式"""
    artifact = getattr(message, "artifact", None)
    if isinstance(artifact, dict):
        structured_content = artifact.get("structured_content")
        if isinstance(structured_content, dict) and "result" in structured_content:
            return str(structured_content["result"]).strip()

    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_list = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item:
                    text_list.append(str(item["text"]))
                elif "content" in item:
                    text_list.append(str(item["content"]))
            else:
                text_list.append(str(item))
        return "".join(text_list).strip()
    return str(content).strip()


def build_scoped_database_tools(list_tables_tool, db_sql_tool, workspace_context=None):
    if not workspace_context or tool is None:
        return list_tables_tool, db_sql_tool, ""
    scope = build_workspace_sql_scope(workspace_context)
    policy_text = build_workspace_sql_policy_text(workspace_context)

    @tool("list_tables_tool")
    def scoped_list_tables_tool() -> str:
        """返回当前业务空间允许查询的数据表结构和字段画像。"""
        return format_workspace_table_schema(scope)

    @tool("db_sql_tool")
    def scoped_db_sql_tool(query: str) -> str:
        """仅在当前业务空间授权表范围内执行只读 SQL 查询。"""
        validation = validate_workspace_sql_scope(query, scope)
        if not validation.allowed:
            return f"错误: 工作空间 SQL 范围检查未通过。{validation.reason}"
        return db_sql_tool.invoke({"query": validation.query})

    return scoped_list_tables_tool, scoped_db_sql_tool, policy_text

#业务分流路由条件，
def should_continue_ywfl(state: BIState) -> Literal[END,"call_python_coder", "call_list_tables"]:
    """条件路由的，动态边"""
    messages = state["messages"]
    last_message = messages[-1]
    print("ywfl_last_message:",last_message)
    route_result = get_message_text(last_message)
    print("业务分流结果:", route_result)
    # print("ywfl_last_message.tool_calls:",last_message.tool_calls)
    #最后一个message不是functionCall或者是Functioncall但是没有SQL都走到END节点
    if route_result=="纯python编码": #如果有工具调用则需要根据，业务分流的结果决策向哪里走
        return "call_python_coder"
    elif route_result=="业务数据查询分析":
        return "call_list_tables"
    else: #如果是正常回复，则结束当前流程->END节点(正常回复)
        return END

#路由逻辑->下游可能的节点
def should_continue(state: BIState) -> Literal[END,"call_select_deep_data_analysis"]:
    """条件路由的，动态边"""
    messages = state["messages"]
    last_message = messages[-1]
    print("should_continue last_message1:",last_message)
    print("should_continue last_message.tool_calls:",last_message.tool_calls)
    #最后一个message不是functionCall或者是Functioncall但是没有SQL都走到END节点
    if not last_message.tool_calls:
        return END
    else:
        if "query" not in last_message.tool_calls[0]["args"]:
            print("触发了MCP但是没有成功返回SQL")
            return END
        return "call_select_deep_data_analysis"

#select_deep_data_analysis节点是否需要进一步调用工具完成数据分析
# def should_analysis_continue(state: BIState) -> Literal[END, "deep_data_analysis_tool"]:
#     """条件路由的，动态边"""
#     messages = state["messages"]
#     last_message = messages[-1]
#     print("should_analysis_continue last_message:",last_message)
#     # print("should_analysis_continue last_message.tool_calls:",last_message.tool_calls)
#     # 还有数据分析、机器学习类的工具调用，因此需要继续走LangGraph的数据分析流程
#     if not last_message.content: #content='' tool_cals:[{args:{}}]
#         return "deep_data_analysis_tool"
#     else: #最后一个message不是functionCall说明run sql已经得到答案了
#         return END



#%%
@asynccontextmanager  # 作用：用于快速创建异步上下文管理器。它使得异步资源的获取和释放可以像同步代码一样通过 async with 语法优雅地管理。
async def make_graph(workspace_context=None):
    """定义，并且编译工作流"""
    client = MultiServerMCPClient(mcp_server_config) #接收一个MCP服务器组对象
    log_step("初始化 MCP 客户端")
    tools=[] #所有工具
    #并行同时启动4个会话session,session的作用是持久化会话,保持MCP server和client之间的不断
    async with client.session("python_chart_mcp") as python_chart_session, client.session("ywfl_mcp") as ywfl_session, \
        client.session("machine_learning_mcp") as machine_learning_session, client.session("search_db_mcp") as search_db_session, \
        client.session("workspace_mcp") as workspace_session:
        python_chart_server_tools = await load_mcp_tools(python_chart_session) #加载所有MCP，并显示所有的工具 list_tools()
        ywfl_server_tools = await load_mcp_tools(ywfl_session)  #
        machine_learning_server_tools = await load_mcp_tools(machine_learning_session)  #
        search_db_server_tools = await load_mcp_tools(search_db_session)  #
        workspace_server_tools = await load_mcp_tools(workspace_session)
        tools.extend(ywfl_server_tools)
        tools.extend(machine_learning_server_tools)
        tools.extend(python_chart_server_tools)
        tools.extend(search_db_server_tools)
        tools.extend(workspace_server_tools)
        log_step("MCP 工具加载完成: " + ", ".join(tool.name for tool in tools))
        # 解析tool获取工具变量
        for one_tool in tools:
            if one_tool.name=="list_tables_tool":
                list_tables_tool=one_tool
            elif one_tool.name=="db_sql_tool":
                db_sql_tool=one_tool
            elif one_tool.name == "ywfl_tool":
                ywfl_tool=one_tool
            elif one_tool.name == "run_python_script_tool":
                run_python_script_tool=one_tool
            elif one_tool.name =="reviews_stars_correlation_test_tool":
                reviews_stars_correlation_test_tool=one_tool
            elif one_tool.name =="analysis_product_reviews_tool":
                analysis_product_reviews_tool=one_tool
            elif one_tool.name =="sales_predict_tool":
                sales_predict_tool=one_tool
            elif one_tool.name=="translate_to_python_plot_script": #写python代码绘图的工具
                translate_to_python_plot_script_tool=one_tool
            elif one_tool.name=="list_workspaces_tool":
                list_workspaces_tool=one_tool
            elif one_tool.name=="get_workspace_schema_tool":
                get_workspace_schema_tool=one_tool
            elif one_tool.name=="get_workspace_analysis_context_tool":
                get_workspace_analysis_context_tool=one_tool
            elif one_tool.name=="get_workspace_report_summary_tool":
                get_workspace_report_summary_tool=one_tool
            else:
                log_step(f"遇到了其它tools:{one_tool.name}")

        def call_identify_intention(state: BIState):
            """业务分流节点"""
            #每一轮的history应当是HumanMessage与最终执行完整个LangGraph流程得到了AI Message回复+本轮消息
            call_identify_system_message=[SystemMessage(content="""你是一个对话智能助手,你具有语言技能和工具调用技能。
            若用户希望做数据分析、查询业务数据、机器学习建模、做计算、绘制统计图表、写代码等工作，你需要调用`ywfl_tool`工具来实现下游任务分流，
            若用户做纯咨询则使用对话技能完成自由对话""")]
            log_step("进入业务分流节点")
            # 不强制ywfl_tool的调用，允许模型在获得解决方案时自然响应，如正常回复。只对写代码和数据分析响应工具调用
            llm_with_tools = llm.bind_tools([ywfl_tool])
            #ToolNode 通过图形状态和消息列表进行操作。它期望消息列表中的最后一条消息为 AIMessage 类型，并具有 tool_calls 参数
            ywfl_result = llm_with_tools.invoke(call_identify_system_message+state['messages']) #返回的是一个AI_MESSAGE对象，有可能是工具调用(判断下游业务转向)，有可能不走工具调用(自由回复)
            log_step(f"业务分流模型返回: tool_calls={bool(ywfl_result.tool_calls)}")
            return  {"messages":[ywfl_result]}
        identify_intention_tool_node = ToolNode([ywfl_tool], name="identify_intention_tool_node")
        def call_python_coder(state: BIState):
            """PYTHON直接写程序+自动执行节点"""
            log_step("进入 Python 编码节点")
            llm_with_tools = llm.bind_tools([run_python_script_tool])
            python_coder_result = llm_with_tools.invoke(state['messages'],parallel_tool_calls=True) #state['messages'][-2:] whole_message_list
            log_step(f"Python 编码模型返回: tool_calls={bool(python_coder_result.tool_calls)}")
            return {'messages': [python_coder_result]}
        #执行python程序的工具节点(绘图+编码执行结果)
        python_run_tool_node = ToolNode([run_python_script_tool], name="python_run_tool_node")
        list_tables_tool, db_sql_tool, workspace_sql_policy = build_scoped_database_tools(
            list_tables_tool,
            db_sql_tool,
            workspace_context,
        )
        def call_list_tables(state: BIState):
            """获取数据库信息节点"""
            log_step("进入获取数据表结构节点")
            tool_call = {
                "name": "list_tables_tool", #关系型数据库的内置方法
                "args": {},
                "id": "tool1",
                "type": "tool_call",
            }
            tool_call_message = AIMessage(content="", tool_calls=[tool_call])
            return {"messages": [tool_call_message]}

         # 第二个节点
        list_tables_tool = ToolNode([list_tables_tool], name="list_tables_tool")

        #数据分析和机器学习、绘图的一个runnable编译完了的子图
        data_analysis_prompt = generate_query_system_prompt
        if workspace_sql_policy:
            data_analysis_prompt = f"{generate_query_system_prompt}\n{workspace_sql_policy}"
        data_analysis_agent = create_react_agent(model=llm,
                                                 tools=[db_sql_tool,
                                                        run_python_script_tool,
                                                        list_workspaces_tool,
                                                        get_workspace_schema_tool,
                                                        get_workspace_analysis_context_tool,
                                                        get_workspace_report_summary_tool,
                                                        reviews_stars_correlation_test_tool,
                                                        translate_to_python_plot_script_tool,
                                                        analysis_product_reviews_tool,
                                                        sales_predict_tool], 
                                                 prompt=data_analysis_prompt,name="data_analysis_agent",debug=True)
        workflow = StateGraph(BIState)
        workflow.add_node(call_python_coder)
        workflow.add_node(python_run_tool_node)
        workflow.add_node(call_identify_intention)
        workflow.add_node(identify_intention_tool_node)
        workflow.add_node(call_list_tables)
        workflow.add_node(list_tables_tool)
        workflow.add_node(data_analysis_agent) #generate_sql
        workflow.add_edge(START, "call_identify_intention")
        workflow.add_edge("call_identify_intention", "identify_intention_tool_node")
        workflow.add_conditional_edges("identify_intention_tool_node", should_continue_ywfl) #    {"tools": "tools", END: END},
        workflow.add_edge("call_python_coder", "python_run_tool_node")
        workflow.add_edge("python_run_tool_node",END) #执行python程序
        workflow.add_edge("call_list_tables", "list_tables_tool")
        workflow.add_edge("list_tables_tool", "data_analysis_agent")
        workflow.add_edge('data_analysis_agent', END) #generate_sql 工具调用了代表生成了sql，没有工具调用代表出了问题走到END结束节点;如果没有继续走就从should_continue中走到END
        #构建带有MemorySaver的图结构
        # memory=MemorySaver()
        log_step("正在创建 LangGraph 图")
        try:
            graph = workflow.compile() # checkpointer=memory
        except Exception as e:
            print("创建图出现错误:",e)
        # 绘制 LangGraph 流程图会访问 mermaid.ink，接口请求时默认跳过，避免离线/网络慢导致阻塞。
        if os.getenv("DRAW_LANGGRAPH", "").lower() in {"1", "true", "yes"}:
            try:
                graph_png = graph.get_graph().draw_mermaid_png()
                img = mpimg.imread(BytesIO(graph_png), format='PNG')
                plt.imshow(img)
                plt.axis('off')
                plt.show()
                with open("./build_graph.png", "wb") as f:
                    f.write(graph_png)
            except Exception as e:
                print("绘制LangGraph图失败，已跳过:", e)
        yield graph


