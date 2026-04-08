from graph import app
import sys

def main():
    print("多智能体对话系统已启动！(输入 'quit' 或 'exit' 退出)")
    
    while True:
        lines = []
        print("\n用户 (输入完毕后，在新的一行输入 'END' 并回车结束): ")
        while True:
            line = input()
            if line == 'END':
                break
            lines.append(line)
        user_input = '\n'.join(lines)
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("系统关闭。")
            break
            
        if not user_input.strip():
            continue

        print("多智能体协作处理中...")
        
        # 构造初始 State，触发流程
        initial_state = {"user_input": user_input}
        
        final_draft = "" # 用于记录最终通过审核的回答
        
        # 将原先的 final_state = app.invoke(initial_state) 替换为流式遍历
        for output in app.stream(initial_state):
            # output 是一个字典，键是当前刚执行完毕的节点名称，值是它返回的状态更新
            for node_name, state_update in output.items():
                print(f"--- [当前进度]: 智能体 '{node_name}' 已完成工作 ---")
                
                # 根据不同节点，打印关键的流转信息，方便调试和观察
                if node_name == "parser":
                    print(f"  > 提取关键词: {state_update.get('parsed_query')}")
                elif node_name == "search":
                    print(f"  > 网页检索已完成")
                elif node_name == "generator":
                    # 实时记录最新生成的草稿
                    if "draft" in state_update:
                        final_draft = state_update["draft"]
                    print(f"  > 初稿已生成，等待审核...")
                elif node_name == "reviewer":
                    is_approved = state_update.get("is_approved")
                    print(f"  > 审核通过状态: {is_approved}")
                    if not is_approved:
                        print(f"  > 审核意见: {state_update.get('feedback')}\n  > [系统提示]: 正在打回重写...")
                        
        # 整个图流转到达 END 后，输出最终被采纳的草稿
        print(f"\nAI 最终回答: {final_draft}")

if __name__ == "__main__":
    main()