"""
pip install psycopg2
pip install pg8000
pip install langchain_openai
"""
import os
import sys
# 添加当前项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

#%%
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langgraph.prebuilt import ToolNode
from my_llm import llm
from my_state import BIState
from langchain_core.messages import SystemMessage, HumanMessage,ToolMessage

# db = SQLDatabase.from_uri('sqlite:///../chinook.db')
QWEN_API_KEY=os.getenv("QWEN_API_KEY")
db_host =os.getenv("db_host")
password = os.getenv("password")
dbname = os.getenv("dbname")
db_port=5432
user =os.getenv("user")
if not password:
    raise RuntimeError("数据库密码未配置，请在 .env 中设置 password，禁止使用默认弱密码。")
# 创建数据库连接
try:
    db = SQLDatabase.from_uri(
        f"postgresql+psycopg2://{user}:{password}@{db_host}:{db_port}/{dbname}",
        # include_tables=['slot_info_test'],  # 指定你想包含的表名
        sample_rows_in_table_info=3  # 每张表采样3行数据
    )
    print("成功连接到数据库!")
    # 测试是否能获取表信息
    tables = db.get_usable_table_names()
    print("数据库中的表:", tables)
    # 创建工具包
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    print("SQL 工具加载完成:", [tool.name for tool in tools])
except Exception as e:
    print("连接数据库时出错:", str(e))

#%%
db = SQLDatabase.from_uri(f"postgresql://{user}:{password}@{db_host}:{db_port}/{dbname}")
print(db.dialect)
#%%
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()
# tools: [QuerySQLDatabaseTool(description="Input to this tool is a detailed and correct SQL query, output is a result from the database. If the query is not correct, an error message will be returned. If an error is returned, rewrite the query, check the query, and try again. If you encounter an issue with Unknown column 'xxxx' in 'field list', use sql_db_schema to query the correct table fields.", db=<langchain_community.utilities.sql_database.SQLDatabase object at 0x7f3ee2635a20>), InfoSQLDatabaseTool(description='Input to this tool is a comma-separated list of tables, output is the schema and sample rows for those tables. Be sure that the tables actually exist by calling sql_db_list_tables first! Example Input: table1, table2, table3', db=<langchain_community.utilities.sql_database.SQLDatabase object at 0x7f3ee2635a20>), ListSQLDatabaseTool(db=<langchain_community.utilities.sql_database.SQLDatabase object at 0x7f3ee2635a20>), QuerySQLCheckerTool(description='Use this tool to double check if your query is correct before executing it. Always use this tool before executing a query with sql_db_query!', db=<langchain_community.utilities.sql_database.SQLDatabase object at 0x7f3ee2635a20>, llm=ChatOpenAI(client=<openai.resources.chat.completions.completions.Completions object at 0x7f3ee2634220>, async_client=<openai.resources.chat.completions.completions.AsyncCompletions object at 0x7f3ee2635ab0>, root_client=<openai.OpenAI object at 0x7f3ee2634a60>, root_async_client=<openai.AsyncOpenAI object at 0x7f3ee26349d0>, model_name='qwen-plus', temperature=0.0, model_kwargs={}, openai_api_key=SecretStr('**********'), openai_api_base='https://dashscope.aliyuncs.com/compatible-mode/v1', extra_body={'chat_template_kwargs': {'enable_thinking': False}}), llm_chain=LLMChain(verbose=False, prompt=PromptTemplate(input_variables=['dialect', 'query'], input_types={}, partial_variables={}, template='\n{query}\nDouble check the {dialect} query above for common mistakes, including:\n- Using NOT IN with NULL values\n- Using UNION when UNION ALL should have been used\n- Using BETWEEN for exclusive ranges\n- Data type mismatch in predicates\n- Properly quoting identifiers\n- Using the correct number of arguments for functions\n- Casting to the correct data type\n- Using the proper columns for joins\n\nIf there are any of the above mistakes, rewrite the query. If there are no mistakes, just reproduce the original query.\n\nOutput the final SQL query only.\n\nSQL Query: '), llm=ChatOpenAI(client=<openai.resources.chat.completions.completions.Completions object at 0x7f3ee2634220>, async_client=<openai.resources.chat.completions.completions.AsyncCompletions object at 0x7f3ee2635ab0>, root_client=<openai.OpenAI object at 0x7f3ee2634a60>, root_async_client=<openai.AsyncOpenAI object at 0x7f3ee26349d0>, model_name='qwen-plus', temperature=0.0, model_kwargs={}, openai_api_key=SecretStr('**********'), openai_api_base='https://dashscope.aliyuncs.com/compatible-mode/v1', extra_body={'chat_template_kwargs': {'enable_thinking': False}}), output_parser=StrOutputParser(), llm_kwargs={}))]
#%%
# 获取表结构的工具
get_schema_tool = next(tool for tool in tools if tool.name == 'sql_db_schema') #sql_db_schema
print("get_schema_tool:",get_schema_tool)
get_schema_node = ToolNode([get_schema_tool], name="get_schema_node")


#%%
# 测试工具调用
# print(get_schema_tool.invoke('slot_info_test'))
#%%

def call_get_schema(state: BIState):
    """ 第三个节点"""
    prompt="""你能根据
    
    """
    # 注意：LangChain强制要求所有模型都接受 `tool_choice="any"`
    # 以及 `tool_choice=<工具名称字符串>` 这两种参数
    # print("进入Call_get_schema节点")
    # new_state_message_list = []
    # for message in state['messages'][::-1]:
    #     #将本轮会话取出来
    #     #如果不是human消息则追加消息
    #     if not isinstance(message, HumanMessage):
    #         new_state_message_list.append(message)
    #     else: #如果是human消息追加后退出
    #         new_state_message_list.append(message)
    #         break
    # new_state_message_list1 = new_state_message_list[::-1]
    # print("call_get_schema message[state]:",new_state_message_list1)
    llm_with_tools = llm.bind_tools([get_schema_tool], tool_choice="any")
    response = llm_with_tools.invoke(state["messages"]) #state["messages"]new_state_message_list1
    return {"messages": [response]}

#一个或多个 然后查看查询结果并返回答案。
get_schema_node = ToolNode([get_schema_tool], name="get_schema")
generate_query_system_prompt = """
你是一个设计用于与Postgresql数据库交互的智能体，你的任务是调用db_sql_tool工具根据任务编写SQL查询语句，然后再调用db_sql_tool工具执行SQL查询获取到精确查询结果。
给定一个输入问题，你能通过创建所有语法正确的{dialect}查询来尽可能多的获取与之相关的数据库中的所有数据，然后执行该查询得到精确查询结果
除非用户明确指定他们希望获取的示例数量(返回指定数量个结果)或仅对某个对象进行查询(仅返回该对象的结果)，否则始终将查询限制为最多{top_k}个结果。
永远不要查询特定表的所有列，只询问与问题相关的列。
不要对数据库执行任何DML语句（INSERT、UPDATE、DELETE、DROP等）。
如果用户只是询问价格、数量、总和、平均值等简单业务查询，请只调用一次db_sql_tool获取结果，然后立即用自然语言回答，不要继续调用其它工具。
只有当用户明确要求绘图、预测、评论分析、相关性分析或复杂统计建模时，才调用Python或机器学习类工具。
若生成图表，请务必将图表路径在回复中输出
""".format(
    dialect=db.dialect,
    top_k=30, #查询30行记录，这个根据业务来设置
)

query_check_system = """您是一位SQL检查大师。
你善于检查SQL查询语句中的常见错误，包括：
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins
如果发现上述任何错误，请重写查询。若无错误，请原封不动的返回查询语句。
检查完成后，您将调用适当的工具来执行查询。
不要对数据库执行任何DML语句（INSERT、UPDATE、DELETE、DROP等）。"""

select_deep_data_analysis_system_prompt="""
你是一个数据分析智能体，你能将用户的输入进行拆解，利用提供的数据，调用合适的响应工具完成回复:
(0)若基于已有数据能解决用户问题，请直接回答用户问题
(1)若希望绘制图表请调用'run_python_script_tool'工具实现编写python代码并执行绘图
(2)若希望对指定商品名进行用户满意度与星级评分相关性分析请调用'reviews_stars_correlation_test_tool'工具
(3)若希望挖掘商品的用户满意度与评价，请调用'analysis_product_reviews_tool'工具
(4)若希望预测销量，请调用'sales_predict_tool'工具
"""

