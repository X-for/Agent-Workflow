import config_manager
from graph import build_graph_from_config

def main():
    workflow_id = "test2"
    try:
        config = config_manager.load_workflow_config(workflow_id)
        print(f"成功加载配置: {config.get('description', workflow_id)}")
    except FileNotFoundError:
        print(f"错误: 找不到配置文件 {workflow_id}.json，请先保存配置。")
        return

    app = build_graph_from_config(config)
    print("多智能体对话引擎已启动！(输入 'quit' 或 'exit' 退出)")

    while True:
        user_input = input("\n用户: ")
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("系统关闭。")
            break

        if not user_input.strip():
            continue

        print("工作流执行中...")

        # 核心修改：tool_calls 必须初始化为空字典
        initial_state = {
            "user_input": user_input,
            "tool_calls": {},
            "context_data": {}
        }

        final_output = ""
        run_config = {"configurable": {"thread_id": "."}}

        for output in app.stream(initial_state, config=run_config):
            for node_name, state_update in output.items():
                print(f"--- [进度]: 节点 '{node_name}' 已完成 ---")

                if node_name.endswith("_tools"):
                    print(f"  > 工具执行完毕")
                elif "draft" in state_update and node_name in ["generator", "summarizer"]:
                    final_output = state_update["draft"]
                    print(f"  > 已生成报告")
                elif node_name == "reviewer":
                    print(f"  > 审核意见: {state_update.get('feedback', '无')}")

        print(f"\nAI 最终输出:\n{final_output}")

if __name__ == "__main__":
    main()