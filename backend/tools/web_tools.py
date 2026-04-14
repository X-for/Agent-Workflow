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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()  # 如果请求失败会抛出异常
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除不需要的标签（脚本、样式等）
        for script in soup(["script", "style", "nav", "footer", "iframe"]):
            script.decompose()
            
        title = soup.title.string if soup.title else "无标题"
        
        # 提取正文并稍微清理多余的空行
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # 限制长度以避免 token 过大
        if len(text) > 8000:
            text = text[:8000] + "\n\n... (内容过长，已截断)"
            
        return f"网页标题: {title}\n网页内容:\n{text}"
        
    except Exception as e:
        return f"获取网页内容时发生错误: {str(e)}"
    
