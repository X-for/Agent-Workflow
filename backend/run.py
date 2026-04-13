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
    
    print("多智能体工作流系统启动")
    print("输入 'quit' 或 'exit' 退出程序\n")
    
    while True:
        # 获取用户输入
        user_input = input("请输入您的查询: ").strip()
        
        # 检查退出条件
        if user_input.lower() in ['quit', 'exit', '退出']:
            print("再见！")
            break
        
        if not user_input:
            print("输入不能为空，请重新输入。\n")
            continue
        
        try:
            # 运行工作流
            print(f"\n正在处理: {user_input}")
            final_global_state = engine.run(
                start_node_id="start_node",
                start_port_id="out_query",
                initial_data=user_input
            )
            
            # 提取并显示结果
            print("\n" + "="*50)
            print("工作流最终输出的总结报告：")
            print("="*50)
            # 通过 节点名:端口名 提取包裹
            final_result = final_global_state.get("end_node:text_output", "未找到结果")
            print(final_result)
            print("\n" + "-"*50 + "\n")
            
        except Exception as e:
            print(f"执行过程中出现错误: {str(e)}\n")