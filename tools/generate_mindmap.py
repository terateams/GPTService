import json
import os
import uuid
from graphviz import Digraph
from common import create_mindma_data_by_openai, build_mind_map
from main import MindmapItem


async def generate_mindmap():
    try:
        airesp = await create_mindma_data_by_openai("根据微积分基础整理一个学习计划思维导图")
        # 创建并构建思维导图
        data = json.loads(airesp)
        item = MindmapItem.model_validate(data)

        graph = Digraph(comment=item.title, engine="Sfdp")
        graph.attr(splines='curved', overlap='false', sep='2',mode="major", margin='0.4')  # 设置图的大小为A4纸尺寸

        build_mind_map(graph, item.title, None, structure=item.structure)

        fileuuid = str(uuid.uuid4())
        output_path = os.path.join("/tmp", fileuuid)
        graph.render(output_path, format='png', cleanup=True)
        graph.view()

    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    content = """{
    "title": "对数基础知识",
    "structure": {
        "对数基础知识": ["📚 定义", "🔍 属性", "🔢 计算规则", "📈 应用"],
        "📚 定义": ["🎯 对数的概念", "🔑 对数的底数", "✅ 对数函数"],
        "🔍 属性": ["🌀 唯一性", "☀️ 正值性", "🌐 定义域和值域"],
        "🔢 计算规则": ["➕ 乘法的对数法则", "➖ 除法的对数法则", "✖️ 幂的对数法则", "➗ 根的对数法则", "🔄 底数变换法则"],
        "📈 应用": ["📉 指数方程", "💹 指数衰减与增长", "🌏 科学计数法", "📊 数据分析"],
        
        "🎯 对数的概念": [],
        "🔑 对数的底数": [],
        "✅ 对数函数": [],
        
        "🌀 唯一性": [],
        "☀️ 正值性": [],
        "🌐 定义域和值域": [],
        
        "➕ 乘法的对数法则": [],
        "➖ 除法的对数法则": [],
        "✖️ 幂的对数法则": [],
        "➗ 根的对数法则": [],
        "🔄 底数变换法则": [],
        
        "📉 指数方程": [],
        "💹 指数衰减与增长": [],
        "🌏 科学计数法": [],
        "📊 数据分析": []
    }
}"""
    generate_mindmap()
