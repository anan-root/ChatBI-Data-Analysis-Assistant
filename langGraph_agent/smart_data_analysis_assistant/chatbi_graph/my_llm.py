#%%
from langchain_openai import ChatOpenAI
from pathlib import Path
from dotenv import load_dotenv
import os
# 获取当前脚本所在目录
script_dir = Path(__file__).resolve().parent
# 加载 .env 文件：优先读取 chatbi_graph/.env，兼容读取 smart_data_analysis_assistant/.env
load_dotenv(script_dir.parent / ".env")
load_dotenv(script_dir / ".env", override=True)


#DEEPSEEK llm - 使用最新的DeepSeek模型
llm = ChatOpenAI(
    temperature=0,
    model='deepseek-chat',
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com")

# 通义千问LLM
# llm = ChatOpenAI(
#     temperature=0,
#     model="qwen-plus-latest", #qwen-plus
#     openai_api_key=os.getenv("QWEN_API_KEY"),
#     openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
#     extra_body={"chat_template_kwargs": {"enable_thinking": False},"parallel_tool_calls":True},
#     parallel_tool_calls=True
# )
#,"parallel_tool_calls":True
