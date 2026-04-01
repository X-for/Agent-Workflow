import subprocess
import sys
import os
import time
import signal

def kill_process_tree(p):
    """跨平台的杀进程树函数，保证不留僵尸子进程"""
    try:
        if sys.platform == 'win32':
            # Windows: 使用 taskkill 强制杀死进程树 (/T 参数)
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Linux/Mac: 向整个进程组发送 SIGTERM 信号
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
    except Exception as e:
        print(f"清理进程 {p.pid} 时出错: {e}")

def main():
    print("正在启动 Agent Workflow 全栈服务...")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "agent-frontend")
    
    # 🌟 核心：为 Linux/Mac 的子进程分配新的进程组 (Session ID)
    kwargs = {}
    if sys.platform != "win32":
        kwargs["preexec_fn"] = os.setsid
    
    # 1. 启动 Python 后端
    print("-> 启动 FastAPI 后端 (端口 8001)...")
    backend_cmd = [sys.executable, "main.py"]
    backend_process = subprocess.Popen(backend_cmd, cwd=root_dir, **kwargs)
    
    # 给后端一小会儿时间启动
    time.sleep(2)
    
    # 2. 启动 Vue 前端
    print("-> 启动 Vue 前端...")
    is_windows = sys.platform.startswith("win")
    frontend_cmd = "npm run dev" if is_windows else ["npm", "run", "dev"]
    frontend_process = subprocess.Popen(
        frontend_cmd, 
        cwd=frontend_dir, 
        shell=is_windows,
        **kwargs
    )
    
    print("\n所有服务均已启动！按 Ctrl+C 即可一键彻底关闭前后端。")
    
    try:
        # 阻塞主进程，等待子进程
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n[系统提示] 接收到退出信号，正在彻底清理服务及所有后台子进程...")
        
        # 调用我们的终极清理函数
        kill_process_tree(backend_process)
        kill_process_tree(frontend_process)
        
        print("清理完成，再见！")
        sys.exit(0)

if __name__ == "__main__":
    main()