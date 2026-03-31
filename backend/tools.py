from langchain_core.tools import tool

# 独立功能：定义一个搜索工具
@tool
def mock_web_search(query: str) -> str:
    """当你需要了解最新的知识或互联网信息时，调用此工具。"""
    print(f"\n[系统执行] 正在搜索互联网: {query}")
    # 这里未来可以接入真实的搜索 API (如 Tavily 或 SerpAPI)
    return f"关于 {query} 的搜索结果：这是一项非常前沿的技术。"