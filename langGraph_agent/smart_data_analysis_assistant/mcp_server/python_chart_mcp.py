"""
python绘图的mcp
工具1:实现运行一段python script脚本，根据生成的不同结果输出不同的内容(1.文本输出 2.图形输出)
工具2:translate_to_python_plot_script:根据绘图需求，将提供数据转成python matplotlib库写的绘图代码,如果当前数据不足以生成绘图代码请勿调用
"""
import sys
import os
import tempfile
import matplotlib.pyplot as plt
from pathlib import Path
import uuid
import shutil
sys.path.append("/root/wangshihang/langGraph_agent/smart_data_analysis_assistant")
import json
from langchain_community.utilities import SQLDatabase
from mcp.server import FastMCP
from public_function import LLM_replay
from dotenv import load_dotenv
load_dotenv()
#%%
QWEN_API_KEY=os.getenv("QWEN_API_KEY")
#%%
mcp = FastMCP(name='python_chart_mcp', instructions='Python绘图工具MCP',host="0.0.0.0",  port=9002)
#%%
def format_output(content):
    """将输出内容格式化为JSON字符串"""
    #...其它操作
    return json.dumps(content, ensure_ascii=False)
def prepare_output_data(variables, env):
    """
    准备可序列化的输出数据
    参数:
        variables: 需要处理的变量名集合
        env: 包含变量的执行环境
    返回:
        包含变量名和可序列化值的字典
    """
    result = {}
    for var in variables:
        value = env[var]
        try:
            # 测试值是否可JSON序列化
            json.dumps(value)
            result[var] = value
        except (TypeError, ValueError):
            # 对不可序列化的值进行字符串化处理
            result[var] = f"[不可序列化对象] {str(value)}"
    return result
#%%
# 配置图片存储目录（可根据需要修改）
# 使用绝对路径确保找到目录
IMAGE_STORAGE_DIR = Path(__file__).parent.parent / "chatbi_graph" / "output"
IMAGE_STORAGE_DIR.mkdir(exist_ok=True)  # 确保目录存在
#运行python代码的mcp tool
#这里我们假设只会有一张图,多张图的话自己改造一下代码即可，通过一个image_list搜集所有生成的图像,然后交给前端分别做渲染呈现
"""
这段代码实现运行一段python script脚本，根据生成的不同结果输出不同的内容
1 做计算,写python代码做值的运算
2 绘图,绘制统计图
3 执行pythoh代码
"""
@mcp.tool()
async def run_python_script_tool(script_content: str):
    """
    执行用户提供的Python代码，并返回执行结果或生成的图片路径
    :param script_content: 需要执行的Python代码字符串
    :return: 代码运行的最终结果或生成的图片路径信息描述
    """
    # 获取执行环境中的全局变量
    execution_env = globals().copy()
    execution_env.update({
        'plt': plt,
        '__name__': '__main__'
    })
    try:
        # 阶段一：表达式求值尝试
        try:
            evaluated_result = eval(script_content, execution_env)
            print("xxx:",evaluated_result)
            # 检查是否有活动的matplotlib图形
            if plt.get_fignums():
                image_path = save_matplotlib_figures()
                plt.close('all')
                if image_path:
                    return format_output(f"根据您的要求,生成的统计图路径:{image_path}")
            return format_output(str(evaluated_result)) #输出表达式运行结果
        except SyntaxError:
            pass  # 不是简单表达式，继续执行代码块

        # 阶段二：记录执行前的环境状态
        pre_execution_vars = set(execution_env.keys())
        # 执行代码块
        try:
            exec(script_content, execution_env)
        except Exception as error:
            plt.close('all')
            return format_output(f"执行过程中发生错误: {str(error)}")
        # 检查是否有活动的matplotlib图形,如果有图形则返回图形所在的路径（生产环境下返回类似oss url链接,一个道理）
        if plt.get_fignums():
            image_path = save_matplotlib_figures()
            plt.close('all')
            # output["images"] = generated_images
            return format_output(f"根据您的要求,生成的统计图路径:{image_path}")

        # 阶段三：分析执行后的环境变化;执行完的结果保存在变量中
        post_execution_vars = set(execution_env.keys())
        created_vars = post_execution_vars - pre_execution_vars
        # 处理执行结果
        output = {}
        if created_vars:
            output["variables"] = prepare_output_data(created_vars, execution_env)

        if not output:
            return format_output("代码执行完成，未产生新的变量或图片") #print(1)
        return format_output(output)
    except Exception as e:
        plt.close('all')
        return format_output(f"系统错误: {str(e)}")

#生产环境下这个函数中还需要实现将图像上传到对应的云空间，拿到对应的图像的url link,后续拿着这个link交给前端做呈现渲染
def save_matplotlib_figures():
    """保存当前所有的matplotlib图形到文件"""
    for i in plt.get_fignums():
        fig = plt.figure(i)
        # 生成唯一文件名
        image_name = f"figure_{uuid.uuid4().hex}.png"
        image_path = IMAGE_STORAGE_DIR / image_name
        # 保存图片
        fig.savefig(image_path, format='png', bbox_inches='tight')
        image_path=str(image_path.absolute()) #上传OSS拿到image url
    return image_path #image_url
def prepare_output_data(variables, env):
    """准备可序列化的输出数据"""
    output = {}
    for var in variables:
        try:
            output[var] = str(env[var])
        except Exception as e:
            output[var] = f"<无法序列化的对象: {type(env[var]).__name__}>"
    return output
def format_output(data):
    """格式化输出结果"""
    if isinstance(data, str):
        return "程序执行得到结果:\n"+data #返回string格式
    else:
        data=str(data)
        return "程序执行得到结果:\n"+data #返回string格式
#%%
#(1) 绘制图形返回值测试
x="""
import os
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')  # 在导入pyplot之前设置后端
import numpy as np
# 修正后的数据
months = np.arange(1, 13)  # 12个月
product_A_sales = [1, 2, 3, 4, 5, 5, 6, 2, 4, 8, 10, 9]
# 补充了一个值以满足12个月的需求
# 绘制柱状图\n
plt.figure(figsize=(10, 6))
plt.bar(months, product_A_sales, color='blue', label='Product A Sales')
plt.show()
print("11111")
plt.xlabel('Month')
plt.ylabel('Sales')
plt.title('Monthly Sales of Product A')
plt.xticks(months)
plt.legend()
# plt.grid(True)
# 保存到当前目录下的 "output" 文件夹
output_dir = "/root/wangshihang/langGraph_agent/smart_data_analysis_assistant/chatbi_graph/output"
print(output_dir)
os.makedirs(output_dir, exist_ok=True)  # 确保文件夹存在
save_path = os.path.join(output_dir, "product_A_sales.png")  # 文件路径
plt.savefig(save_path, dpi=300, bbox_inches='tight')  # 保存为PNG
"""
# async def main():
#     result=await run_python_script_tool(x)
#     print("result:",result)
# asyncio.run(main())
#%%
# (2)计算表达式测试
# async def main():
#     y = "6666*8888"
#     result = await run_python_script_tool(y)
#     print("result:", result)
# asyncio.run(main())


#%%
# (3)计算可执行程序的返回值测试
z="""def bubble_sort(arr):
    n = len(arr)
    # 遍历所有数组元素
    for i in range(n):
        # 最后i个元素已经是排好序的
        swapped = False  # 优化：如果某一轮没有交换，说明已经有序
        for j in range(0, n-i-1):
            # 如果当前元素大于下一个元素，则交换
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]  # Python的交换语法
                swapped = True
        
        # 如果没有发生交换，提前结束排序
        if not swapped:
            break    
    return arr

if __name__ == "__main__":
    # 测试数据
    test_data = [64, 34, 25, 12, 22, 11, 90]
    print("排序前:", test_data)
    # 调用冒泡排序
    sorted_data = bubble_sort(test_data.copy())  # 使用copy避免修改原数据
    print("排序后:", sorted_data)
"""
# result=await run_python_script(z)
# print("result:",result)

# async def main():
#     result=await run_python_script_tool(z)
#     print("result:",result)
# asyncio.run(main())
#%%
#实现绘制图标的MCP tool
#这里说明一下:为什么要和上面的工具同时具备绘图的功能。
# 原因在于有一些需求是：A.直接绘图。那么AI的逻辑处理是->寻找能生成图片的工具 而非 (1)写python代码 (2)代码执行绘图程序
#B.查询XXX的数据，然后写一段python代码，然后绘图 那么AI的逻辑->(1)写python绘图的代码 (2)代码执行绘图程序 可以用我们上面定义的run_python_script工具了
#所以拥有一个让用户需求->python绘图代码的工具，能有效防止AI反应不过来的情况
@mcp.tool()
async def translate_to_python_plot_script(graph_demand:str,data_desc:str) -> str:
    """
    根据绘图需求，将提供数据转成python matplotlib库写的绘图代码,如果当前数据不足以生成绘图代码请勿调用
    :param graph_demand:绘图的需求，如：绘制一张折线图,出具一张饼图
    :param data_desc:可以支持实现绘制统计图的数据描述
    :return:一段可以执行的python绘图代码
    """
    prompt=f"""你是一个python绘图代码生成大师,你善于根据当前用户提供的数据，依据用户的绘图需求生成可执行的python绘图代码，必须通过matplotlib库实现。
    注意：(1)若没有提供合适的数据完成绘图代码生成，请返回:我无法生成绘图代码 (2) 请勿生成需求要求外的代码，请勿生成非绘图代码。(3) 你的任务仅仅是生成可执行python代码，请勿做任何分析或解释。
    举例1:
    输入:
    用户需求:请根据销量数据生成一张销量折线图
    数据:12个月的销量数据[30,50,70,50,80,55,30,50,70,50,80,55]
    输出:import matplotlib.pyplot as plt
import numpy as np
sales_data = [30, 50, 70, 50, 80, 55, 30, 50, 70, 50, 80, 55]
months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
plt.figure(figsize=(10, 6))  # 设置图表大小
plt.plot(months, sales_data, marker='o', color='#4CAF50', linewidth=2, markersize=8)
plt.title('2023年每月销量趋势', fontsize=16, pad=20)
plt.xlabel('月份', fontsize=12)
plt.ylabel('销量(件)', fontsize=12)
plt.ylim(0, max(sales_data) + 10)
for x, y in zip(months, sales_data):
    plt.text(x, y+2, str(y), ha='center', va='bottom', fontsize=10)
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show() 
    举例2:
    输入:
    用户需求:请根据订单数据绘制一张每个产品的销售分布饼图
    数据:需要查询订单表的数据
    输出:我无法生成绘图代码
    
    
    输入:
    用户需求:{graph_demand}
    数据:{data_desc}
    输出:"""
    code_result=await LLM_replay(messages=prompt)
    if '无法生成' in code_result:
        return "数据不够，需要从数据库中查询获取更多数据"
    return code_result.strip()
# async def main():
#     code_result=await translate_to_python_plot_script(graph_demand="绘制一张饼图",data_desc="纸巾12月销量数据为:[4,5,8,3,7,0,20,55,7,89,22,13]")
#     print(code_result)
# asyncio.run(main())
#%%
if __name__ == "__main__":
    # 以标准 streamable-http方式运行 MCP 服务器
    mcp.run(transport='streamable-http')
#nohup python python_chart_mcp.py &
#uv run python_chart_mcp.py &
#%%
