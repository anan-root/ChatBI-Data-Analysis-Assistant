import sys
sys.path.append("/root/wangshihang/langGraph_agent/smart_data_analysis_assistant")
from mcp.server import FastMCP
from dotenv import load_dotenv
import os
from openai import AsyncOpenAI
import asyncio
#加载.env文件中的环境变量
load_dotenv()
#定义大模型调用函数，用于处理文本类模型生成功能
async def LLM_replay(messages):
    """
    prompt_template:大模型调用的提示词模板
    message:大模型调用的用户输入
    """
    llm_client =AsyncOpenAI(api_key=os.getenv("QWEN_API_KEY"), base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    result =await llm_client.chat.completions.create(
        model="qwen-plus", #推荐使用:qwen-plus-latest qwen-plus qwen-max-0125 qwen-plus-latest -0125
        messages=[{"role":"user","content":messages}],
        max_tokens=8192,
        temperature=0)
    return result.choices[0].message.content

# result=await LLM_replay(messages="你好")
# print(result)