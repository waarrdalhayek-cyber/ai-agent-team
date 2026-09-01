"""Free/local tool adapters for the commerce team."""
from __future__ import annotations
import ast
import operator
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self, data):
        text=data.strip()
        if text: self.parts.append(text)


def web_search(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Public-web search via DuckDuckGo HTML; no API key required."""
    url='https://html.duckduckgo.com/html/?'+urllib.parse.urlencode({'q':query})
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        html=r.read().decode('utf-8','ignore')
    # Lightweight extraction: retain useful result links/text without third-party deps.
    import re
    rows=[]
    for href,title in re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.I|re.S):
        parser=_TextExtractor(); parser.feed(title)
        rows.append({'title':' '.join(parser.parts),'url':href})
        if len(rows)>=limit: break
    return rows


def marketplace_search(query: str, limit: int = 5):
    return web_search(f'{query} السعودية متجر سعر شراء', limit)


def social_search(query: str, limit: int = 5):
    return web_search(f'{query} site:tiktok.com OR site:instagram.com OR site:youtube.com', limit)


def social_trends(query: str, limit: int = 5):
    return web_search(f'{query} ترند viral trending السعودية', limit)


def supplier_search(query: str, limit: int = 5):
    return web_search(f'{query} supplier wholesale manufacturer السعودية', limit)


def ad_library_search(query: str, limit: int = 5):
    return web_search(f'{query} ads advertising social media', limit)


_ALLOWED_BIN={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Pow:operator.pow}
_ALLOWED_UN={ast.UAdd:operator.pos,ast.USub:operator.neg}
def calculator(expression: str) -> float:
    """Safe arithmetic calculator; never evals arbitrary Python."""
    def walk(n):
        if isinstance(n,ast.Expression): return walk(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)): return n.value
        if isinstance(n,ast.BinOp) and type(n.op) in _ALLOWED_BIN: return _ALLOWED_BIN[type(n.op)](walk(n.left),walk(n.right))
        if isinstance(n,ast.UnaryOp) and type(n.op) in _ALLOWED_UN: return _ALLOWED_UN[type(n.op)](walk(n.operand))
        raise ValueError('Unsupported calculation')
    return float(walk(ast.parse(expression,mode='eval')))


def copywriting(brief: str) -> dict[str,str]:
    """Local deterministic brief scaffold; LLM adapter can replace it later."""
    return {'brief':brief,'status':'BRIEF_READY_FOR_LLM'}


def default_free_tools() -> dict[str, Any]:
    return {
        'web_search': web_search,
        'marketplace_search': marketplace_search,
        'social_search': social_search,
        'social_trends': social_trends,
        'supplier_search': supplier_search,
        'ad_library_search': ad_library_search,
        'calculator': calculator,
        'copywriting': copywriting,
    }
