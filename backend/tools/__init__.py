# 把所有子模块里的 tool 导入到这一层暴露出去
from .web_tools import *
from .file_tools import *
from .code_tools import *
from .analyze_tools import *
import functools



category_map = {
    "web_tools": {"label": "网络交互", "icon": "🌐"},
    "file_tools": {"label": "文件操作", "icon": "📁"},
    "code_tools": {"label": "代码执行", "icon": "💻"},
    "analyze_tools": {"label": "数据分析", "icon": "📊"}
}
