from .utils import *
from ddgs import DDGS 
from langchain_core.tools import tool

@tool
@log
def web_search(query: str) -> str:
    """
    当你不知道某些最新信息、事实，或者需要了解外部互联网上的知识时，必须调用此工具进行搜索。
    输入参数应该是一个简洁明确的搜索关键词。
    """
    try:
        # 初始化搜索引擎
        ddgs = DDGS()
        # 搜索最多前 5 条结果
        results = list(ddgs.text(query, max_results=5))
        
        if not results:
            return f"未能找到关于 '{query}' 的搜索结果。"
            
        # 将结果拼接成让大模型易于阅读的格式
        formatted_results = []
        for i, res in enumerate(results):
            # DuckDuckGo 返回的通常有 title(标题), body(摘要), href(链接)
            title = res.get('title', '无标题')
            body = res.get('body', '无摘要')
            link = res.get('href', '')
            formatted_results.append(f"[{i+1}] {title}\n摘要: {body}\n来源: {link}")
            
        # 把这些拼接好的字符串返回给 Agent
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"搜索过程中发生错误: {str(e)}"
    

@tool
@log
def get_content_from_url(url: str) -> str:
    """当你需要获取某个网页的内容时，调用此工具."""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 如果请求失败会抛出异常
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # 提取网页的标题和正文（这只是一个简单的示例，实际情况可能需要更复杂的解析）
        title = soup.title.string if soup.title else "无标题"
        paragraphs = soup.find_all('p')
        content = "\n".join(p.get_text() for p in paragraphs[:5])  # 只取前5段
        
        return f"网页标题: {title}\n网页内容:\n{content}"
        
    except Exception as e:
        return f"获取网页内容时发生错误: {str(e)}"
    
