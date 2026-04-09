import config_manager
from graph import build_graph_from_config


def main():
    # 1. 读取工作流配置 (这里硬编码读取您刚才存的 standard_qa)
    workflow_id = "test2"
    try:
        config = config_manager.load_workflow_config(workflow_id)
        print(f"成功加载配置: {config.get('description', workflow_id)}")
    except FileNotFoundError:
        print(f"错误: 找不到配置文件 {workflow_id}.json，请先保存配置。")
        return

    # 2. 将配置交给图引擎，动态编译出 LangGraph 实例
    app = build_graph_from_config(config)
    print("多智能体对话引擎已启动！(输入 'quit' 或 'exit' 退出)")

    # 3. 终端交互循环
    while True:
        user_input = input("\n用户: ")
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("系统关闭。")
            break

        if not user_input.strip():
            continue

        print("工作流执行中...")

        # 构造初始 State，注意初始化 tool_calls 防范空指针
        initial_state = {
            "user_input": user_input,
            "tool_calls": [],
            "context_data": {}  # 初始化动态数据池
        }

        final_output = ""

        run_config = {"configurable": {"thread_id": "."}}

        # 使用 stream 流式输出，观察状态机的每一次流转
        for output in app.stream(initial_state, config=run_config):
            for node_name, state_update in output.items():
                print(f"--- [进度]: 节点 '{node_name}' 已完成 ---")

                # 打印一些关键信息方便调试观察
                if node_name == "tool_executor":
                    print(f"  > 工具执行完毕")
                elif "draft" in state_update and node_name in ["generator", "summarizer"]:
                    final_output = state_update["draft"]
                    print(f"  > 已生成初稿")
                elif node_name == "reviewer":
                    print(f"  > 审核意见: {state_update.get('feedback', '无')}")

        # 循环结束，图到达 END，输出最终草稿
        print(f"\nAI 最终输出:\n{final_output}")


if __name__ == "__main__":
    main()