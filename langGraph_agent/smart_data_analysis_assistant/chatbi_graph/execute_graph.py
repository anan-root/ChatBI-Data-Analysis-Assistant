#%%
import os
import sys
# 添加当前项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
import asyncio
from build_graph import make_graph
from langchain_core.messages import AIMessage


#设置同一个是thread_id的对话
thread_config={"configurable":{"thread_id":"session_1"}}
whole_history=[] #存储纯文本会话消息
#或查业务数据库
async def run_graph():
    """执行该 工作流"""
    async with make_graph() as graph:
        while True:
            print("用户输入:")
            user_input = input("用户：")
            whole_history.append({"role": "user", "content": user_input})
            if user_input.lower() in ['q', 'exit', 'quit']:
                print('对话结束，拜拜！')
                break
            else:
                print("本轮输入消息:",whole_history)
                event_message_list=whole_history
                async for event in graph.astream({"messages":event_message_list},
                                                 stream_mode="values"): #保持同一个用户的对话的连续记忆 ,config=thread_config ,config=thread_config
                    #Emit all values in the state after each step, including interrupts.When used with functional API, values are emitted once at the end of the workflow.
                    event["messages"][-1].pretty_print()
                    #如果当前事件不是工具类消息是回复则更新历史记录,
                    if event["messages"][-1].content and isinstance(event["messages"][-1],AIMessage) and not event["messages"][-1].tool_calls:
                        print("kkkkk:",event["messages"][-1].content)
                        whole_history.append({"role": "assistant", "content": event["messages"][-1].content})
                    event_message_list.append(event["messages"][-1])

if __name__ == '__main__':
    asyncio.run(run_graph())

#查询健身手套价格是多少
#查询运动类商品有多少
#查询用户王一珂的在线平均时长为多久 她的在线平均时长为多久
#运动用品平均价格与食品平均价格哪个高
#抽纸近12个月的总销量和洗手液的总销量哪个更高
#分析一下王一珂的用户画像，通过其购买的物品、职业和个人描述的数据来分析
#王一珂和梦彤的消费习惯有什么不同
#查询一下保鲜袋历史12个月的销量，基于此预测一下未来的销量
#我想写一段冒泡排序 写一段python代码，实现冒泡排序
#王一珂的在线平均时长为多久
#查询商品洗碗布的月销量数据，实现绘制一张以月为维度的销量柱状图
#查询商品洗碗布的月销量数据，绘制一张以月为维度的销量柱状图
#查询银耳的用户评论和星级数据，并分析评论好坏与星级两者的相关性，是否是星级越高用户越满意

#多轮对话测试案例:
#查询用户王一珂的用户id/她的在线平均时长为多久/分析一下她的用户画像，从其购买的物品、职业、个人描述来分析
#抽纸单价是多少？/查询一下它过去12个月的销量/请帮我再预测一下它下个月的销量/根据其12个月的销量与预测的一个月的销量共计13个月绘制一张销量折线图

