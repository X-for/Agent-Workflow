import subprocess
import sys
import os
import time

def main():
    print("正在启动 Agent Workflow 全栈服务...")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "agent-frontend")
    
    # 1. 启动 Python 后端
    print("-> 启动 FastAPI 后端 (端口 8001)...")
    backend_cmd = [sys.executable, "main.py"]
    backend_process = subprocess.Popen(backend_cmd, cwd=root_dir)
    
    # 给后端一小会儿时间启动
    time.sleep(2)
    
    # 2. 启动 Vue 前端
    print("-> 启动 Vue 前端...")
    # 注意：Windows 下 npm 脚本通常需要 shell=True
    is_windows = sys.platform.startswith("win")
    frontend_cmd = "npm run dev" if is_windows else ["npm", "run", "dev"]
    frontend_process = subprocess.Popen(
        frontend_cmd, 
        cwd=frontend_dir, 
        shell=is_windows
    )
    
    print("\n所有服务均已启动！按 Ctrl+C 即可一键关闭前后端。")
    
    try:
        # 阻塞主进程，等待子进程
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n接收到退出信号，正在关闭服务...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()