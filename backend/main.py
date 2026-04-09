import os
import sys
import glob
import json
import config_manager
from graph import build_graph_from_config
from dotenv import load_dotenv
load_dotenv()


# ==========================================
# 1. CLI 终端 UI 辅助工具 (ANSI 色彩控制)
# ==========================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


# ==========================================
# 2. 长效记忆流系统 (Long-Term Memory) - 支持多会话
# ==========================================
def get_memory_path(workflow_id: str, session_id: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, os.environ.get("CHAT_DIR", "chats"), f"{workflow_id}_{session_id}_memory.json")


def load_context_memory(workflow_id: str, session_id: str) -> dict:
    path = get_memory_path(workflow_id, session_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_context_memory(workflow_id: str, session_id: str, context_data: dict):
    path = get_memory_path(workflow_id, session_id)
    try:
        # 新增这一行：在写入文件前，确保它所在的父级目录一定存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print_warn(f"无法保存记忆: {e}")


def print_banner():
    banner = f"""
{Colors.HEADER}{Colors.BOLD}==================================================
      🤖 动态多智能体工作流引擎 (Agent Workflow)      
=================================================={Colors.RESET}
"""
    print(banner)


def print_sys(msg): print(f"{Colors.BLUE}✦ {msg}{Colors.RESET}")


def print_success(msg): print(f"{Colors.GREEN}✔ {msg}{Colors.RESET}")


def print_warn(msg): print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_error(msg): print(f"{Colors.RED}✖ {msg}{Colors.RESET}")


def print_ai(msg): print(f"\n{Colors.CYAN}{Colors.BOLD}🤖 [AI 兜底输出]:{Colors.RESET}\n{msg}\n")


# ==========================================
# 2. 新建工作流向导 (Wizard)
# ==========================================
def create_workflow_wizard() -> str:
    print(f"\n{Colors.CYAN}{Colors.BOLD}=== 🪄 创建新智能体架构向导 ==={Colors.RESET}")

    wf_id = input(f"{Colors.GREEN}👉 1. 请输入工作流 ID (英文/下划线，作为文件名，如 my_agent): {Colors.RESET}").strip()
    if not wf_id:
        print_warn("创建已取消。")
        return None

    desc = input(f"{Colors.GREEN}👉 2. 请输入架构的一句话描述: {Colors.RESET}").strip()

    print_sys("3. 请选择要生成的初始架构模板:")
    print(f"  [{Colors.YELLOW}1{Colors.RESET}] 单一全能智能体 (标准 ReAct 循环)")
    print(f"  [{Colors.YELLOW}2{Colors.RESET}] 多分支并行架构 (一分多 -> 独立查阅 -> 汇总)")
    print(f"  [{Colors.YELLOW}3{Colors.RESET}] 纯净空白模板 (供手动编写)")

    choice = input(f"{Colors.GREEN}👉 请选择模板 (1/2/3): {Colors.RESET}").strip()

    template = {
        "workflow_id": wf_id,
        "description": desc,
        "entry_point": "agent",
        "nodes": [],
        "edges": [],
        "conditional_edges": []
    }

    if choice == "1":
        template["nodes"] = [
            {"name": "agent", "model": "deepseek-chat", "temperature": 0.3,
             "system_prompt": "你是一个强大的 AI 助手。请根据用户问题调用工具或直接回答。", "api": "DEEPSEEK_API_KEY",
             "output_key": "draft", "tools": ["web_search", "list_files_in_directory", "read_document"]}
        ]
        template["conditional_edges"] = [
            {"from": "agent", "router": "check_tool_calls",
             "mapping": {"execute_tools": "agent_tools", "next_step": "END"}}
        ]
        template["edges"] = [{"from": "agent_tools", "to": "agent"}]

    elif choice == "2":
        template["entry_point"] = "parser"
        template["nodes"] = [
            {"name": "parser", "model": "deepseek-chat", "temperature": 0.1, "system_prompt": "分析用户任务并下发指令。",
             "api": "DEEPSEEK_API_KEY", "output_key": "parsed_query", "tools": []},
            {"name": "web_searcher", "model": "deepseek-chat", "temperature": 0.3, "system_prompt": "负责网络检索。",
             "api": "DEEPSEEK_API_KEY", "output_key": "web_results", "tools": ["web_search"]},
            {"name": "local_searcher", "model": "deepseek-chat", "temperature": 0.1, "system_prompt": "负责本地检索。",
             "api": "DEEPSEEK_API_KEY", "output_key": "local_results",
             "tools": ["list_files_in_directory", "read_document"]},
            {"name": "summarizer", "model": "deepseek-chat", "temperature": 0.4,
             "system_prompt": "综合所有搜索结果给出最终回答。", "api": "DEEPSEEK_API_KEY", "output_key": "draft",
             "tools": []}
        ]
        template["edges"] = [
            {"from": "parser", "to": "web_searcher"},
            {"from": "parser", "to": "local_searcher"},
            {"from": "web_searcher_tools", "to": "web_searcher"},
            {"from": "local_searcher_tools", "to": "local_searcher"}
        ]
        template["conditional_edges"] = [
            {"from": "web_searcher", "router": "tool_or_fan_in_router",
             "router_args": {"required_keys": ["web_results", "local_results"]},
             "mapping": {"execute_tools": "web_searcher_tools", "ready": "summarizer", "wait": "END"}},
            {"from": "local_searcher", "router": "tool_or_fan_in_router",
             "router_args": {"required_keys": ["web_results", "local_results"]},
             "mapping": {"execute_tools": "local_searcher_tools", "ready": "summarizer", "wait": "END"}}
        ]

    # 保存 JSON 文件
    base_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_dir = os.path.join(base_dir, "workflow")
    os.makedirs(workflow_dir, exist_ok=True)
    file_path = os.path.join(workflow_dir, f"{wf_id}.json")

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print_success(f"工作流架构已生成并保存至: {file_path}")
    print_sys("该架构将被自动加载运行。您随时可以在代码编辑器中修改其提示词或拓扑结构。\n")
    return wf_id


# ==========================================
# 3. 动态加载工作流菜单
# ==========================================
def select_workflow() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_dir = os.path.join(base_dir, "workflow")
    os.makedirs(workflow_dir, exist_ok=True)

    files = glob.glob(os.path.join(workflow_dir, "*.json"))
    workflows = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                wf_id = data.get("workflow_id", os.path.basename(f).replace('.json', ''))
                desc = data.get("description", "无描述信息")
                workflows.append({"id": wf_id, "desc": desc, "file": os.path.basename(f)})
        except Exception:
            pass

    print_sys("请选择要加载的多智能体工作流:")
    print(f"  {Colors.YELLOW}[0]{Colors.RESET} {Colors.BOLD}➕ 创建新架构 (Wizard){Colors.RESET}")
    for idx, wf in enumerate(workflows):
        print(f"  {Colors.GREEN}[{idx + 1}]{Colors.RESET} {Colors.BOLD}{wf['id']}{Colors.RESET} - {wf['desc']}")

    while True:
        try:
            choice = input(f"\n👉 请输入序号 (0-{len(workflows)}): ").strip()
            if choice.lower() in ['q', 'quit', 'exit']:
                sys.exit(0)
            idx = int(choice)

            if idx == 0:
                new_id = create_workflow_wizard()
                if new_id:
                    return new_id
                else:
                    continue

            elif 1 <= idx <= len(workflows):
                return workflows[idx - 1]['id']
            else:
                print_warn("序号超出范围，请重新输入。")
        except ValueError:
            print_warn("请输入有效的数字序号。")
        except KeyboardInterrupt:
            print()
            sys.exit(0)


# ==========================================
# 4. 主程序交互循环
# ==========================================
def main():
    print_banner()
    workflow_id = select_workflow()

    try:
        config = config_manager.load_workflow_config(workflow_id)
        print_success(f"成功加载配置: {config.get('description', workflow_id)}\n")
    except Exception as e:
        print_error(f"加载配置文件失败: {e}")
        return

    print_sys("正在编译多智能体图网络...")
    try:
        app = build_graph_from_config(config)
        print_success("引擎启动完毕！(输入 'q', 'quit' 或 'exit' 退出)\n")
    except Exception as e:
        print_error(f"图编译失败，请检查配置与代码: {e}")
        return

    import glob

    # 扫描当前工作流的所有历史记忆文件
    memory_files = glob.glob(f"{workflow_id}_*_memory.json")
    sessions = [f.replace(f"{workflow_id}_", "").replace("_memory.json", "") for f in memory_files]

    print(f"\n✦ 请选择历史对话，或创建新对话:")
    print(f"  \033[93m[0] ➕ 创建新对话\033[0m")
    for i, s_id in enumerate(sessions):
        print(f"  \033[92m[{i + 1}]\033[0m 📁 {s_id}")

    # 循环直到用户做出正确选择
    while True:
        s_choice = input(f"\n👉 请输入序号 (0-{len(sessions)}): ").strip()
        if s_choice == "0":
            session_id = input("请输入新对话名称 (直接回车默认 'default'): ").strip() or "default"
            break
        elif s_choice.isdigit() and 1 <= int(s_choice) <= len(sessions):
            session_id = sessions[int(s_choice) - 1]
            break
        else:
            print("输入无效，请重新选择。")

    # 加载记忆
    global_context = load_context_memory(workflow_id, session_id)
    if global_context:
        print(f"\n✔ 已恢复旧对话记忆: [{session_id}] (包含 {len(global_context)} 条记录)")
    else:
        print(f"\n✔ 已创建新对话沙盒: [{session_id}]")

    print_sys(f"当前已进入独立会话沙盒: [{session_id}]")
    # 【修改传参】：将 session_id 传给记忆读取函数
    global_context = load_context_memory(workflow_id, session_id)
    if global_context:
        print_success(f"已恢复上一次的上下文记忆 (包含 {len(global_context)} 条历史资料区块)")

    while True:
        try:
            user_input = input(
                f"\n{Colors.GREEN}{Colors.BOLD}🧑 [用户] (输入 '/m' 开启多行粘贴，'q' 退出): {Colors.RESET}")
            if user_input.strip() == '/clear':
                global_context.clear()
                # 【修改传参】
                save_context_memory(workflow_id, session_id, global_context)
                print_success(f"已彻底清空会话 [{session_id}] 的长期记忆！")
                continue
            if user_input.strip() == "/m":
                print(
                    f"{Colors.YELLOW}⬇️ [多行模式] 请粘贴或输入内容 (按 Ctrl+D 或在新行单独输入 'EOF' 提交): {Colors.RESET}")
                lines = []
                while True:
                    try:
                        line = input()
                        if line.strip() == "EOF":
                            break
                        lines.append(line)
                    except EOFError:  # 捕获 Ctrl+D (Mac/Linux) 或 Ctrl+Z (Windows)
                        break
                user_input = "\n".join(lines).strip()
                print(f"{Colors.BLUE}✦ 多行内容已提交 ({len(lines)} 行){Colors.RESET}")
            else:
                user_input = user_input.strip()
            if not user_input:
                continue
            if user_input.lower() in ['quit', 'exit', 'q']:
                print_sys("系统安全退出，再见！")
                break

            print_sys("任务已下发，工作流开始流转...")

            initial_state = {
                "user_input": user_input,
                "tool_calls": {},
                "context_data": global_context.copy()
            }

            # 【修改】：让 LangGraph 的线程 ID 和您的会话 ID 绑定，实现真正的物理隔离
            run_config = {"configurable": {"thread_id": session_id}}
            final_output = "【未获取到最终输出，图可能在中间节点中断】"
            print_ai_header = False

            for event in app.stream(initial_state, config=run_config, stream_mode=["updates", "messages"]):
                event_type, event_data = event

                if event_type == "messages":
                    chunk, metadata = event_data
                    node_name = metadata.get("langgraph_node", "")

                    if node_name in ["generator", "summarizer", "agent"]:
                        if not print_ai_header:
                            print(
                                f"\n{Colors.CYAN}{Colors.BOLD}🤖 [{node_name} 正在实时思考并输出]:{Colors.RESET}\n{Colors.CYAN}",
                                end="")
                            print_ai_header = True

                        if hasattr(chunk, "content") and isinstance(chunk.content, str) and chunk.content:
                            sys.stdout.write(chunk.content)
                            sys.stdout.flush()

                elif event_type == "updates":
                    for node_name, state_update in event_data.items():
                        if "context_data" in state_update:
                            global_context.update(state_update["context_data"])
                        if node_name.endswith("_tools"):
                            print(f"  {Colors.YELLOW}⚙️  [{node_name}] 工具执行完毕{Colors.RESET}")
                        elif node_name == "reviewer":
                            feedback = state_update.get('feedback', '无')
                            print(f"  {Colors.RED}🔍 [{node_name}] 审核意见: {feedback}{Colors.RESET}")
                        elif node_name in ["generator", "summarizer", "agent"]:
                            print(f"{Colors.RESET}\n  {Colors.GREEN}✔ [{node_name}] 报告流式生成完毕{Colors.RESET}")
                            if "draft" in state_update:
                                final_output = state_update["draft"]
                        else:
                            print(f"  {Colors.BLUE}🧠 [{node_name}] 思考/分发完成{Colors.RESET}")
            save_context_memory(workflow_id, session_id, global_context)
            if not print_ai_header:
                print_ai(final_output)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⚠ 收到中断信号。若要彻底退出请输入 'q'。{Colors.RESET}\n")
            continue
        except Exception as e:
            print_error(f"工作流执行期间发生异常: {str(e)}")
            print_warn("请检查您的环境变量或 JSON 路由拓扑是否正确配置。")


if __name__ == "__main__":
    main()
