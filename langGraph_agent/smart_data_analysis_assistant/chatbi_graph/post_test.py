"""
本文件用于向chat_api接口发送请求参数来模拟用户使用chatbi服务
"""
#%%
import os
import sys
sys.path.append("/root/wangshihang/langGraph_agent/smart_data_analysis_assistant")
sys.path.append("/root/wangshihang/langGraph_agent/smart_data_analysis_assistant/chatbi_graph")
import requests
from dotenv import load_dotenv

load_dotenv()
server_api_url=os.getenv("server_api_url")
print(server_api_url)
api_url=f"http://{server_api_url}:9008/chatbi_service" #112.98.20.44
input_message={
    "user_id":"ABC",
    "message":"面包和鱿鱼丝哪个贵", #你好 查询一下瓜子的单价 查询一下瓜子的单价 面包和鱿鱼丝哪个贵
    "history":[]
}
result=requests.post(api_url,json=input_message,timeout=20000)
print("result:",result.json())

#%%
input_message={
    "user_id":"ABC",
    "message":"查询一下瓜子的单价", #你好 查询一下瓜子的单价 查询一下瓜子的单价 面包和鱿鱼丝哪个贵
    "history":[{"role":"user","content":"面包和鱿鱼丝哪个贵"},{"role":"assistant","content":"面包贵一些"}]
}
result=requests.post(api_url,json=input_message,timeout=20000)
print("result:",result.json())

