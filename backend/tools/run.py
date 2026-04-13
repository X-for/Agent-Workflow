import os 
from Graph import GraphEngine
from tools import web_search, get_content_from_url

tool_registry = {
    "web_search": web_search,
    "get_content_from_url": get_content_from_url
}

# 2. 从 JSON 文件直接加载整个图网络
if __name__ == "__main__":
    workflow_config_path = os.path.join(os.environ.get("BASE_DIR"), os.environ.get("WORKFLOW_DIR", "workflow_config.json"))
    test = os.path.join(workflow_config_path, "test.json")
    engine = GraphEngine(test, tool_registry)
    
    # 3. 运行！
    final_global_state = engine.run(
        start_node_id="searcher_agent",
        start_port_id="user_query",
        initial_data="帮我查一下什么是多智能体工作流，并总结一下"
    )
    
    # 【新增代码】：去全局状态里提取最终的果实！
    print("\n" + "="*50)
    print("🏆 工作流最终输出的总结报告：")
    print("="*50)
    # 通过 节点名:端口名 提取包裹
    final_result = final_global_state.get("summarizer_agent:final_summary", "未找到结果")
    print(final_result)