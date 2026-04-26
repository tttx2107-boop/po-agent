#!/usr/bin/env python3
"""
微信公众号文章爬虫
通过手机UA绕过微信PC端反爬机制
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("请先安装 requests: pip install requests")
    sys.exit(1)


MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 Safari/604.1"
)


class WeChatArticleParser(HTMLParser):
    """解析微信公众号文章HTML"""
    
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.author = ""
        self.content = []
        self.in_article = False
        self.current_tag = None
        self.current_text = []
        self.meta_tags = {}
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # 提取 meta 信息
        if tag == "meta":
            prop = attrs_dict.get("property", "")
            name = attrs_dict.get("name", "")
            content = attrs_dict.get("content", "")
            
            if prop == "og:title":
                self.title = content
            elif prop == "og:description":
                self.description = content
            elif name == "author":
                self.author = content
                
        # 进入文章正文区域
        if tag == "article" or attrs_dict.get("id") == "js_content":
            self.in_article = True
            self.current_tag = tag
            
    def handle_endtag(self, tag):
        if self.in_article and tag == self.current_tag:
            # 如果遇到 script 或 style，丢弃当前内容
            if self.current_text:
                text = "".join(self.current_text).strip()
                if text:
                    self.content.append(text)
                self.current_text = []
            self.in_article = False
            self.current_tag = None
            
    def handle_data(self, data):
        if self.in_article:
            self.current_text.append(data)
    
    def get_content_text(self):
        """获取正文文本"""
        paragraphs = []
        for p in self.content:
            text = p.strip()
            if text and len(text) > 10:  # 过滤短文本
                paragraphs.append(text)
        return "\n\n".join(paragraphs)


def scrape_wechat_article(url: str) -> dict:
    """
    爬取微信公众号文章
    
    Args:
        url: 微信文章链接
        
    Returns:
        dict: 包含 title, description, author, content
    """
    # 验证URL
    parsed = urlparse(url)
    if parsed.netloc != "mp.weixin.qq.com":
        raise ValueError("仅支持 mp.weixin.qq.com 域名链接")
    
    headers = {
        "User-Agent": MOBILE_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    response.encoding = "utf-8"
    
    parser = WeChatArticleParser()
    parser.feed(response.text)
    
    result = {
        "title": parser.title or "未获取到标题",
        "description": parser.description or "",
        "author": parser.author or "",
        "content": parser.get_content_text() or "",
        "url": url,
        "word_count": len(parser.get_content_text())
    }
    
    return result


def output_result(result: dict, format: str = "json", output_file: str = None):
    """输出结果"""
    if format == "json":
        content = json.dumps(result, ensure_ascii=False, indent=2)
    elif format == "text":
        content = f"""{result['title']}
作者: {result['author']}
描述: {result['description']}

正文:
{result['content']}
"""
    elif format == "markdown":
        content = f"""# {result['title']}

> 作者: {result['author']}  
> 描述: {result['description']}

---

{result['content']}
"""
    else:
        content = json.dumps(result, ensure_ascii=False, indent=2)
    
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"已保存到: {output_file}")
    else:
        print(content)


def main():
    parser = argparse.ArgumentParser(description="微信公众号文章爬虫")
    parser.add_argument("url", help="微信文章链接")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-f", "--format", choices=["json", "text", "markdown"], 
                       default="json", help="输出格式")
    
    args = parser.parse_args()
    
    try:
        result = scrape_wechat_article(args.url)
        output_result(result, args.format, args.output)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
