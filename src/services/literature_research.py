"""
文献调研服务 - Phase 14
支持多文献源、可扩展的学术文献检索与整理
"""

import json
import re
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from urllib.parse import quote_plus
import time

# ============================================================
# 数据模型
# ============================================================

@dataclass
class Paper:
    """论文实体"""
    paper_id: str
    title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    year: int = 0
    venue: str = ""  # 发表venue/期刊/会议
    citation_count: int = 0
    url: str = ""
    doi: str = ""
    
    # 来源信息
    source: str = ""  # sematicscholar, arxiv, pubmed, cnki, 自定义
    source_id: str = ""  # 原始ID
    
    # 评估信息
    relevance_score: float = 0.0  # 相关度评分 0-1
    credibility: int = 0  # 可信度 1-5
    credibility_reason: str = ""
    
    # 用户标注
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    is_starred: bool = False
    
    # 元数据
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if isinstance(self.authors, str):
            self.authors = [self.authors]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Paper":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_credibility_display(self) -> str:
        """可信度显示"""
        stars = "⭐" * self.credibility + "☆" * (5 - self.credibility)
        return f"{stars} {self.credibility_reason}" if self.credibility_reason else stars


@dataclass
class ResearchTask:
    """文献调研任务"""
    id: str
    query: str
    idea_id: str = ""  # 关联想法
    
    # 任务配置
    sources: List[str] = field(default_factory=list)  # 使用哪些文献源
    max_results_per_source: int = 20
    min_relevance: float = 0.3
    
    # 结果
    papers: List[Paper] = field(default_factory=list)
    total_found: int = 0
    
    # 状态
    status: str = "pending"  # pending, searching, completed, failed
    progress: int = 0
    error: str = ""
    
    # 时间
    created_at: str = ""
    completed_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchTask":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LiteratureSource:
    """文献源配置"""
    id: str
    name: str
    description: str
    enabled: bool = True
    api_key_required: bool = False
    api_key: str = ""  # 加密存储
    base_url: str = ""
    rate_limit: int = 10  # 每分钟请求数
    
    # 能力标识
    supports_abstract: bool = True
    supports_citations: bool = True
    supports_keywords: bool = False
    supports_fulltext: bool = False
    
    # 可信度预设
    default_credibility: int = 4
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("api_key"):
            d["api_key"] = "***"  # 脱敏
        return d


# ============================================================
# 文献源基类
# ============================================================

class BaseLiteratureSource(ABC):
    """文献源抽象基类"""
    
    def __init__(self, config: LiteratureSource):
        self.config = config
        self.name = config.name
        self.source_id = config.id
    
    @abstractmethod
    def search(self, query: str, max_results: int = 20) -> List[Paper]:
        """搜索文献，返回论文列表"""
        pass
    
    @abstractmethod
    def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """获取论文详情"""
        pass
    
    def rate_limit_wait(self):
        """速率限制等待"""
        time.sleep(60 / self.config.rate_limit)
    
    def _default_credibility(self, venue: str) -> tuple[int, str]:
        """根据venue评估可信度"""
        venue_lower = venue.lower()
        
        # 顶会/顶刊
        top_conferences = [
            "acl", "neurips", "icml", "iclr", "aaai", "ijcai",  # AI/ML
            "icse", "ase", "fse",  # 软件工程
            "ieee cvpr", "iccv", "eccv",  # 计算机视觉
            "sigcomm", "nsdi", "usenix",  # 网络系统
            "science", "nature", "cell", "pnas",  # 顶刊
        ]
        
        if any(t in venue_lower for t in top_conferences):
            return 5, "顶会/顶刊"
        
        # 高质量期刊
        good_venues = [
            "ieee", "acm", "springer", "elsevier", 
            "towards data science", "arxiv",
            "journal of", "proceedings of"
        ]
        
        if any(t in venue_lower for t in good_venues):
            return 4, "高质量期刊/出版社"
        
        # 预印本
        if "arxiv" in venue_lower or "preprint" in venue_lower:
            return 3, "预印本，需交叉验证"
        
        return 3, "普通来源"


# ============================================================
# 内置文献源实现
# ============================================================

class SemanticScholarSource(BaseLiteratureSource):
    """Semantic Scholar 文献源 - 覆盖全学科，免费API"""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    FIELDS = "title,abstract,authors,year,venue,citationCount,externalId,url,doi"
    
    def __init__(self, config: LiteratureSource):
        super().__init__(config)
        self.headers = {}
        if config.api_key:
            self.headers["x-api-key"] = config.api_key
    
    def search(self, query: str, max_results: int = 20) -> List[Paper]:
        """搜索 Semantic Scholar"""
        papers = []
        try:
            # 计算分页
            limit = min(max_results, 100)  # API单次最多100
            
            url = f"{self.BASE_URL}/paper/search"
            params = {
                "query": query,
                "limit": limit,
                "fields": self.FIELDS,
                "sort": "citationCount"  # 按引用数排序
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("data", []):
                paper = self._parse_paper(item)
                papers.append(paper)
            
            # 如果需要更多结果，递归获取
            if max_results > limit and len(data.get("data", [])) == limit:
                offset = limit
                while offset < max_results:
                    params["offset"] = offset
                    response = requests.get(url, params=params, headers=self.headers, timeout=30)
                    data = response.json()
                    for item in data.get("data", []):
                        papers.append(self._parse_paper(item))
                    if len(data.get("data", [])) < limit:
                        break
                    offset += limit
                    
        except Exception as e:
            print(f"SemanticScholar search error: {e}")
        
        return papers[:max_results]
    
    def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """获取论文详情"""
        try:
            url = f"{self.BASE_URL}/paper/{paper_id}"
            params = {"fields": self.FIELDS}
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return self._parse_paper(response.json())
        except Exception as e:
            print(f"Get paper details error: {e}")
            return None
    
    def _parse_paper(self, item: Dict) -> Paper:
        """解析论文数据"""
        authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
        
        credibility, reason = self._default_credibility(item.get("venue", ""))
        
        return Paper(
            paper_id=item.get("paperId", ""),
            title=item.get("title", "Untitled"),
            abstract=item.get("abstract", ""),
            authors=authors,
            year=item.get("year", 0) or 0,
            venue=item.get("venue", ""),
            citation_count=item.get("citationCount", 0) or 0,
            url=item.get("url", ""),
            doi=item.get("doi", ""),
            source="semanticscholar",
            source_id=item.get("externalId", ""),
            credibility=credibility,
            credibility_reason=reason
        )


class ArxivSource(BaseLiteratureSource):
    """arXiv 文献源 - 物理/计算机/AI预印本"""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    def search(self, query: str, max_results: int = 20) -> List[Paper]:
        """搜索 arXiv"""
        papers = []
        try:
            # arXiv搜索语法转换
            arxiv_query = query.replace(" ", " AND ")
            
            url = self.BASE_URL
            params = {
                "search_query": f"all:{arxiv_query}",
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析 Atom XML
            papers = self._parse_atom(response.text)
            
        except Exception as e:
            print(f"ArXiv search error: {e}")
        
        return papers
    
    def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """arXiv ID 直接获取详情"""
        try:
            url = self.BASE_URL
            params = {"id_list": paper_id}
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            papers = self._parse_atom(response.text)
            return papers[0] if papers else None
        except Exception as e:
            print(f"Get arXiv paper error: {e}")
            return None
    
    def _parse_atom(self, xml_text: str) -> List[Paper]:
        """解析 Atom 格式响应"""
        papers = []
        
        # 提取entry块
        entries = re.findall(r'<entry>(.*?)</entry>', xml_text, re.DOTALL)
        
        for entry in entries:
            try:
                title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                title = title.group(1).strip().replace('\n', ' ') if title else "Untitled"
                
                summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                abstract = summary.group(1).strip().replace('\n', ' ') if summary else ""
                
                authors = re.findall(r'<author>.*?<name>(.*?)</name>.*?</author>', entry, re.DOTALL)
                
                published = re.search(r'<published>(.*?)</published>', entry)
                year = 0
                if published:
                    try:
                        year = int(published.group(1)[:4])
                    except:
                        pass
                
                arxiv_id = re.search(r'<id>(.*?)</id>', entry)
                arxiv_id = arxiv_id.group(1).split('/')[-1] if arxiv_id else ""
                
                url = re.search(r'<link title="pdf" href="(.*?)"', entry)
                pdf_url = url.group(1) if url else ""
                
                category = re.search(r'<category term="(.*?)"', entry)
                venue = category.group(1) if category else "arXiv"
                
                papers.append(Paper(
                    paper_id=arxiv_id,
                    title=title,
                    abstract=abstract[:1000] if abstract else "",  # 截取摘要
                    authors=authors,
                    year=year,
                    venue=f"arXiv:{venue}",
                    citation_count=0,
                    url=pdf_url,
                    source="arxiv",
                    source_id=arxiv_id,
                    credibility=3,
                    credibility_reason="预印本，需交叉验证"
                ))
            except Exception as e:
                continue
        
        return papers


class PubMedSource(BaseLiteratureSource):
    """PubMed 文献源 - 生物医学/安全相关"""
    
    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    def __init__(self, config: LiteratureSource):
        super().__init__(config)
        self.email = config.api_key or "research@po-agent.local"  # PubMed建议提供邮箱
    
    def search(self, query: str, max_results: int = 20) -> List[Paper]:
        """搜索 PubMed"""
        papers = []
        try:
            # Step 1: 搜索获取ID列表
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
                "email": self.email
            }
            
            response = requests.get(self.ESEARCH_URL, params=search_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            id_list = data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return []
            
            # Step 2: 获取摘要
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "rettype": "abstract",
                "retmode": "xml"
            }
            
            response = requests.get(self.EFETCH_URL, params=fetch_params, timeout=30)
            papers = self._parse_pubmed_xml(response.text)
            
        except Exception as e:
            print(f"PubMed search error: {e}")
        
        return papers[:max_results]
    
    def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """获取 PubMed 论文详情"""
        try:
            params = {
                "db": "pubmed",
                "id": paper_id,
                "rettype": "abstract",
                "retmode": "xml"
            }
            response = requests.get(self.EFETCH_URL, params=params, timeout=30)
            papers = self._parse_pubmed_xml(response.text)
            return papers[0] if papers else None
        except Exception as e:
            print(f"Get PubMed paper error: {e}")
            return None
    
    def _parse_pubmed_xml(self, xml_text: str) -> List[Paper]:
        """解析 PubMed XML"""
        papers = []
        
        articles = re.findall(r'<PubmedArticle>(.*?)</PubmedArticle>', xml_text, re.DOTALL)
        
        for article in articles:
            try:
                medline_citation = re.search(r'<MedlineCitation>(.*?)</MedlineCitation>', article, re.DOTALL)
                if not medline_citation:
                    continue
                
                citation = medline_citation.group(1)
                
                pmid = re.search(r'<PMID[^>]*>(.*?)</PMID>', citation)
                pmid = pmid.group(1).strip() if pmid else ""
                
                title_match = re.search(r'<ArticleTitle>(.*?)</ArticleTitle>', citation, re.DOTALL)
                title = title_match.group(1).strip().replace('\n', ' ') if title_match else "Untitled"
                
                # 摘要
                abstract_match = re.search(r'<AbstractText>(.*?)</AbstractText>', citation, re.DOTALL)
                abstract = abstract_match.group(1).strip().replace('\n', ' ') if abstract_match else ""
                
                # 作者
                authors = re.findall(r'<Author.*?<LastName>(.*?)</LastName>.*?<ForeName>(.*?)</ForeName>', 
                                   citation, re.DOTALL)
                author_names = [f"{last} {first}" for last, first in authors]
                
                # 年份
                pub_date = re.search(r'<PubDate>.*?<Year>(\d{4})</Year>', citation)
                year = int(pub_date.group(1)) if pub_date else 0
                
                # 期刊
                journal = re.search(r'<Journal>.*?<Title>(.*?)</Title>', citation, re.DOTALL)
                venue = journal.group(1) if journal else ""
                
                # DOI
                article_id = re.search(r'<ArticleId IdType="doi">(.*?)</ArticleId>', article)
                doi = article_id.group(1).strip() if article_id else ""
                
                papers.append(Paper(
                    paper_id=pmid,
                    title=title,
                    abstract=abstract[:1000] if abstract else "",
                    authors=author_names,
                    year=year,
                    venue=venue,
                    citation_count=0,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    doi=doi,
                    source="pubmed",
                    source_id=pmid,
                    credibility=5,  # PubMed是同行评审期刊
                    credibility_reason="同行评审期刊"
                ))
            except Exception as e:
                continue
        
        return papers


class CustomAPISource(BaseLiteratureSource):
    """自定义 API 文献源 - 用户可配置"""
    
    def __init__(self, config: LiteratureSource):
        super().__init__(config)
        self.endpoint_search = f"{config.base_url}/search" if config.base_url else ""
        self.endpoint_detail = f"{config.base_url}/paper" if config.base_url else ""
    
    def search(self, query: str, max_results: int = 20) -> List[Paper]:
        """调用自定义API搜索"""
        if not self.endpoint_search:
            return []
        
        try:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            params = {"query": query, "limit": max_results}
            response = requests.get(self.endpoint_search, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 假设返回格式: {"papers": [...]}
            papers_data = data.get("papers", data.get("results", data.get("data", [])))
            
            return [self._parse_paper(item) for item in papers_data]
        except Exception as e:
            print(f"Custom API search error: {e}")
            return []
    
    def get_paper_details(self, paper_id: str) -> Optional[Paper]:
        """获取自定义API论文详情"""
        if not self.endpoint_detail:
            return None
        
        try:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            url = f"{self.endpoint_detail}/{paper_id}"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return self._parse_paper(response.json())
        except Exception as e:
            print(f"Get custom paper error: {e}")
            return None
    
    def _parse_paper(self, item: Dict) -> Paper:
        """解析自定义API响应"""
        return Paper(
            paper_id=item.get("id", item.get("paperId", "")),
            title=item.get("title", "Untitled"),
            abstract=item.get("abstract", ""),
            authors=item.get("authors", []) if isinstance(item.get("authors"), list) else [item.get("authors", "")],
            year=item.get("year", 0) or 0,
            venue=item.get("venue", item.get("journal", "")),
            citation_count=item.get("citationCount", item.get("citations", 0)) or 0,
            url=item.get("url", item.get("link", "")),
            doi=item.get("doi", ""),
            source=self.source_id,
            source_id=item.get("id", ""),
            credibility=item.get("credibility", self.config.default_credibility),
            credibility_reason=item.get("credibility_reason", "")
        )


# ============================================================
# 文献源注册表
# ============================================================

class LiteratureSourceRegistry:
    """文献源注册表 - 管理所有可用文献源"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._sources: Dict[str, BaseLiteratureSource] = {}
        self._configs: Dict[str, LiteratureSource] = {}
        
        # 注册内置源
        self._register_builtin_sources()
    
    def _register_builtin_sources(self):
        """注册内置文献源"""
        builtin_configs = [
            LiteratureSource(
                id="semanticscholar",
                name="Semantic Scholar",
                description="覆盖全学科的免费学术搜索API",
                base_url="https://api.semanticscholar.org/graph/v1",
                supports_abstract=True,
                supports_citations=True,
                default_credibility=4
            ),
            LiteratureSource(
                id="arxiv",
                name="arXiv",
                description="物理/计算机/AI预印本服务器",
                base_url="http://export.arxiv.org/api/query",
                supports_abstract=True,
                supports_citations=False,
                default_credibility=3
            ),
            LiteratureSource(
                id="pubmed",
                name="PubMed",
                description="生物医学文献数据库",
                base_url="https://eutils.ncbi.nlm.nih.gov",
                supports_abstract=True,
                supports_citations=False,
                default_credibility=5
            ),
        ]
        
        for config in builtin_configs:
            self._configs[config.id] = config
            self._sources[config.id] = self._create_source(config)
    
    def _create_source(self, config: LiteratureSource) -> BaseLiteratureSource:
        """根据配置创建文献源实例"""
        source_classes = {
            "semanticscholar": SemanticScholarSource,
            "arxiv": ArxivSource,
            "pubmed": PubMedSource,
        }
        
        source_class = source_classes.get(config.id, CustomAPISource)
        return source_class(config)
    
    def register_source(self, config: LiteratureSource) -> bool:
        """注册新的文献源"""
        try:
            self._configs[config.id] = config
            self._sources[config.id] = self._create_source(config)
            return True
        except Exception as e:
            print(f"Register source error: {e}")
            return False
    
    def unregister_source(self, source_id: str) -> bool:
        """取消注册文献源"""
        if source_id in self._sources:
            del self._sources[source_id]
            if source_id in self._configs:
                del self._configs[source_id]
            return True
        return False
    
    def get_source(self, source_id: str) -> Optional[BaseLiteratureSource]:
        """获取文献源实例"""
        return self._sources.get(source_id)
    
    def get_config(self, source_id: str) -> Optional[LiteratureSource]:
        """获取文献源配置"""
        return self._configs.get(source_id)
    
    def list_sources(self) -> List[LiteratureSource]:
        """列出所有文献源"""
        return list(self._configs.values())
    
    def list_enabled_sources(self) -> List[str]:
        """列出所有启用的文献源ID"""
        return [s.id for s in self._configs.values() if s.enabled]
    
    def update_source_config(self, config: LiteratureSource) -> bool:
        """更新文献源配置"""
        if config.id in self._configs:
            self._configs[config.id] = config
            self._sources[config.id] = self._create_source(config)
            return True
        return False
    
    def export_configs(self) -> List[Dict]:
        """导出配置（用于持久化）"""
        return [c.to_dict() for c in self._configs.values()]
    
    def import_configs(self, configs: List[Dict]) -> int:
        """导入配置"""
        count = 0
        for config_dict in configs:
            try:
                config = LiteratureSource(**config_dict)
                self.register_source(config)
                count += 1
            except Exception as e:
                print(f"Import config error: {e}")
        return count


# ============================================================
# 文献调研服务
# ============================================================

class LiteratureResearchService:
    """文献调研服务 - 整合多文献源进行学术调研"""
    
    def __init__(self):
        self.registry = LiteratureSourceRegistry()
        self._tasks: Dict[str, ResearchTask] = {}  # 内存存储，生产应持久化
    
    def create_task(
        self,
        query: str,
        idea_id: str = "",
        sources: Optional[List[str]] = None,
        max_results_per_source: int = 20,
        min_relevance: float = 0.3
    ) -> ResearchTask:
        """创建文献调研任务"""
        import uuid
        task_id = f"research_{uuid.uuid4().hex[:8]}"
        
        if sources is None:
            sources = self.registry.list_enabled_sources()
        
        task = ResearchTask(
            id=task_id,
            query=query,
            idea_id=idea_id,
            sources=sources,
            max_results_per_source=max_results_per_source,
            min_relevance=min_relevance,
            status="pending"
        )
        
        self._tasks[task_id] = task
        return task
    
    async def execute_task(self, task_id: str) -> ResearchTask:
        """执行调研任务"""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        task.status = "searching"
        all_papers = []
        
        for i, source_id in enumerate(task.sources):
            source = self.registry.get_source(source_id)
            if not source or not source.config.enabled:
                continue
            
            try:
                source_papers = source.search(task.query, task.max_results_per_source)
                
                # 计算相关度（简化版：基于标题和摘要匹配）
                for paper in source_papers:
                    paper.relevance_score = self._calculate_relevance(paper, task.query)
                
                all_papers.extend(source_papers)
                task.progress = int((i + 1) / len(task.sources) * 100)
                
                # 速率限制
                source.rate_limit_wait()
                
            except Exception as e:
                print(f"Search error for {source_id}: {e}")
        
        # 去重（基于DOI或标题相似度）
        unique_papers = self._deduplicate_papers(all_papers)
        
        # 过滤低相关度
        task.papers = [p for p in unique_papers if p.relevance_score >= task.min_relevance]
        
        # 按相关度排序
        task.papers.sort(key=lambda p: p.relevance_score, reverse=True)
        
        task.total_found = len(all_papers)
        task.status = "completed"
        task.completed_at = datetime.now().isoformat()
        task.progress = 100
        
        return task
    
    def _calculate_relevance(self, paper: Paper, query: str) -> float:
        """计算论文与查询的相关度"""
        query_terms = query.lower().split()
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower()
        
        score = 0.0
        
        # 标题匹配
        for term in query_terms:
            if term in title_lower:
                score += 0.3
        
        # 摘要匹配
        for term in query_terms:
            if term in abstract_lower:
                score += 0.1
        
        # 归一化
        max_possible = len(query_terms) * 0.4
        score = min(score / max_possible, 1.0) if max_possible > 0 else 0.5
        
        # 引用数加权（引用越多可能越相关）
        if paper.citation_count > 100:
            score = min(score + 0.1, 1.0)
        elif paper.citation_count > 10:
            score = min(score + 0.05, 1.0)
        
        return score
    
    def _deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        """论文去重"""
        seen_ids = set()
        seen_titles = {}  # title -> paper
        unique = []
        
        for paper in papers:
            # 首先按source_id去重
            if paper.source_id and paper.source_id in seen_ids:
                continue
            seen_ids.add(paper.source_id)
            
            # 然后按标题相似度去重
            title_normalized = paper.title.lower().strip()[:50]
            if title_normalized in seen_titles:
                # 保留可信度更高的
                existing = seen_titles[title_normalized]
                if paper.credibility > existing.credibility:
                    unique.remove(existing)
                    seen_titles[title_normalized] = paper
                    unique.append(paper)
            else:
                seen_titles[title_normalized] = paper
                unique.append(paper)
        
        return unique
    
    def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def list_tasks(self, idea_id: Optional[str] = None) -> List[ResearchTask]:
        """列出任务"""
        tasks = list(self._tasks.values())
        if idea_id:
            tasks = [t for t in tasks if t.idea_id == idea_id]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def update_paper(self, task_id: str, paper_id: str, updates: Dict) -> Optional[Paper]:
        """更新论文标注"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        for paper in task.papers:
            if paper.paper_id == paper_id:
                for key, value in updates.items():
                    if hasattr(paper, key):
                        setattr(paper, key, value)
                return paper
        return None
    
    def export_papers(self, task_id: str, format: str = "json") -> str:
        """导出论文列表"""
        task = self._tasks.get(task_id)
        if not task:
            return ""
        
        if format == "json":
            return json.dumps([p.to_dict() for p in task.papers], ensure_ascii=False, indent=2)
        
        elif format == "bibtex":
            return self._export_bibtex(task.papers)
        
        elif format == "markdown":
            return self._export_markdown(task.papers)
        
        return ""
    
    def _export_bibtex(self, papers: List[Paper]) -> str:
        """导出 BibTeX 格式"""
        bibtex = []
        for paper in papers:
            key = paper.paper_id[:8] if paper.paper_id else paper.title[:8]
            authors = " and ".join(paper.authors[:3]) + (" et al." if len(paper.authors) > 3 else "")
            
            entry = f"""@article{{{key},
  title = {{{paper.title}}},
  author = {{{authors}}},
  year = {{{paper.year}}},
  journal = {{{paper.venue}}},
  url = {{{paper.url}}},
  doi = {{{paper.doi}}}
}}"""
            bibtex.append(entry)
        
        return "\n\n".join(bibtex)
    
    def _export_markdown(self, papers: List[Paper]) -> str:
        """导出 Markdown 格式"""
        md = ["# 文献列表\n"]
        for i, paper in enumerate(papers, 1):
            md.append(f"## [{paper.title}]({paper.url})\n")
            md.append(f"- **作者**: {', '.join(paper.authors[:3])}{' et al.' if len(paper.authors) > 3 else ''}")
            md.append(f"- **年份**: {paper.year}")
            md.append(f"- **来源**: {paper.venue}")
            md.append(f"- **可信度**: {paper.get_credibility_display()}")
            md.append(f"- **相关度**: {paper.relevance_score:.2f}")
            if paper.abstract:
                md.append(f"- **摘要**: {paper.abstract[:200]}...")
            md.append("")
        
        return "\n".join(md)


# ============================================================
# 全局实例
# ============================================================

_literature_service: Optional[LiteratureResearchService] = None

def get_literature_service() -> LiteratureResearchService:
    """获取文献调研服务单例"""
    global _literature_service
    if _literature_service is None:
        _literature_service = LiteratureResearchService()
    return _literature_service
