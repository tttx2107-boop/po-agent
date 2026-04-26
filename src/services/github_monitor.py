"""
GitHub项目监测服务
自动发现、评估和追踪GitHub上的有价值项目
"""
import json
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from src.models.github_project import GitHubRepo, GitHubMonitorConfig


class GitHubMonitor:
    """GitHub项目监测器"""
    
    def __init__(self, data_path: str = "data/github_repos.json", config: Optional[GitHubMonitorConfig] = None):
        self.data_path = Path(data_path)
        self.config = config or GitHubMonitorConfig()
        self.repos: Dict[str, GitHubRepo] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """加载已存储的仓库数据"""
        if self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for repo_data in data.get("repos", []):
                        repo = GitHubRepo(**repo_data)
                        self.repos[repo.full_name] = repo
            except Exception as e:
                print(f"加载GitHub数据失败: {e}")
    
    def _save_data(self) -> None:
        """保存仓库数据"""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated_at": datetime.now().isoformat(),
            "repos": [repo.to_dict() for repo in self.repos.values()]
        }
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _make_request(self, url: str, headers: Optional[Dict] = None) -> Optional[Dict]:
        """发起HTTP请求"""
        import urllib.request
        import urllib.parse
        
        default_headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if headers:
            default_headers.update(headers)
        
        try:
            req = urllib.request.Request(url, headers=default_headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            print(f"请求失败: {url} - {e}")
            return None
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[List]:
        """GET请求GitHub API"""
        from urllib.parse import urlencode, quote_plus
        
        base_url = "https://api.github.com"
        url = f"{base_url}{endpoint}"
        if params:
            # URL编码所有值
            encoded_params = []
            for k, v in params.items():
                if isinstance(v, list):
                    v = "+".join(v)
                encoded_params.append(f"{k}={quote_plus(str(v))}")
            query = "&".join(encoded_params)
            url = f"{url}?{query}"
        
        result = self._make_request(url)
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        return result if isinstance(result, list) else None
    
    def search_trending(self, language: str = "", since: str = "daily") -> List[GitHubRepo]:
        """获取GitHub Trending"""
        # 使用非API方式获取Trending页面
        url = f"https://api.github.com/search/repositories"
        params = {
            "q": f"created:>{self._get_date_range(since)}",
            "sort": "stars",
            "order": "desc",
            "per_page": 30
        }
        if language:
            params["q"] += f" language:{language}"
        
        repos = []
        items = self._get("/search/repositories", params)
        if items:
            for item in items[:30]:
                repo = GitHubRepo.from_github_api(item)
                repos.append(repo)
        return repos
    
    def _get_date_range(self, since: str) -> str:
        """获取日期范围"""
        days_map = {"daily": 1, "weekly": 7, "monthly": 30}
        days = days_map.get(since, 1)
        date = datetime.now() - timedelta(days=days)
        return date.strftime("%Y-%m-%d")
    
    def search_by_keywords(self, keywords: List[str], per_page: int = 30) -> List[GitHubRepo]:
        """通过关键词搜索仓库"""
        repos = []
        for keyword in keywords:
            # 搜索查询
            query = f"{keyword} in:name,description,readme"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page
            }
            items = self._get("/search/repositories", params)
            if items:
                for item in items:
                    repo = GitHubRepo.from_github_api(item)
                    repos.append(repo)
        return repos
    
    def get_repository(self, owner: str, repo: str) -> Optional[GitHubRepo]:
        """获取单个仓库详情"""
        data = self._get(f"/repos/{owner}/{repo}")
        if data:
            return GitHubRepo.from_github_api(data)
        return None
    
    def get_readme(self, owner: str, repo: str) -> str:
        """获取仓库README"""
        data = self._get(f"/repos/{owner}/{repo}/readme")
        if data and "content" in data:
            import base64
            content = data["content"]
            # 移除可能的padding
            content = content.replace("\n", "")
            try:
                return base64.b64decode(content).decode("utf-8")
            except:
                return ""
        return ""
    
    def assess_repo(self, repo: GitHubRepo) -> Tuple[float, str]:
        """评估仓库质量和价值"""
        score = 0.0
        notes = []
        
        # 1. Stars评分 (0-40分)
        if repo.stars >= 10000:
            score += 40
            notes.append("⭐ 顶级流行项目")
        elif repo.stars >= 1000:
            score += 30 + (repo.stars / 1000) * 2
        elif repo.stars >= 100:
            score += 15 + (repo.stars / 100) * 5
        else:
            score += repo.stars * 0.1
        
        # 2. Forks评分 (0-20分)
        if repo.forks >= 1000:
            score += 20
        elif repo.forks >= 100:
            score += 10 + (repo.forks / 100) * 2
        else:
            score += repo.forks * 0.05
        
        # 3. 活跃度评分 (0-20分)
        if repo.is_recently_updated(7):
            score += 20
            notes.append("📅 近期活跃")
        elif repo.is_recently_updated(30):
            score += 10
        elif repo.pushed_at:
            try:
                from datetime import timezone
                pushed_dt = datetime.fromisoformat(repo.pushed_at.replace("Z", "+00:00"))
                now_dt = datetime.now(timezone.utc)
                days_old = (now_dt - pushed_dt.replace(tzinfo=timezone.utc)).days
                score += max(0, 10 - days_old * 0.1)
            except:
                pass
        
        # 4. 许可评分 (0-10分)
        if repo.license:
            good_licenses = ["MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause"]
            if any(good in repo.license for good in good_licenses):
                score += 10
                notes.append("📄 开源友好许可")
            else:
                score += 5
        
        # 5. 文档评分 (0-10分)
        if repo.description and len(repo.description) > 50:
            score += 5
        if repo.topics:
            score += min(5, len(repo.topics) * 0.5)
        
        # 扣分项
        if repo.language in ["HTML", "CSS"] and repo.stars < 100:
            score *= 0.7
            notes.append("⚠️ 低价值内容")
        
        # 限制分数
        score = min(10.0, score)
        
        # 生成建议
        suggestion = self._generate_suggestion(repo, score, notes)
        
        return round(score, 1), suggestion
    
    def _generate_suggestion(self, repo: GitHubRepo, score: float, notes: List[str]) -> str:
        """生成集成建议"""
        suggestions = []
        
        if score >= 8.0:
            suggestions.append("💡 强烈推荐集成")
        elif score >= 6.0:
            suggestions.append("💡 可考虑参考")
        
        # 基于语言和话题的建议
        ai_keywords = ["ai", "llm", "gpt", "nlp", "transformer", "neural", "ml", "deep-learning"]
        agent_keywords = ["agent", "autonomous", "tool-use", "planning", "reasoning"]
        
        has_ai = any(kw in repo.topics or kw in (repo.description or "").lower() for kw in ai_keywords)
        has_agent = any(kw in repo.topics or kw in (repo.description or "").lower() for kw in agent_keywords)
        
        if has_ai:
            suggestions.append("🤖 AI相关项目")
        if has_agent:
            suggestions.append("🧠 Agent架构参考")
        
        # 建议内容
        if score >= 7.0:
            suggestions.append(f"📖 可学习其设计模式")
        if repo.forks > 50:
            suggestions.append(f"🔧 社区活跃，易于定制")
        
        return " | ".join(suggestions) if suggestions else "📌 普通项目"
    
    def filter_by_quality(self, repos: List[GitHubRepo]) -> List[GitHubRepo]:
        """按质量过滤"""
        filtered = []
        for repo in repos:
            # 跳过已标记为REJECTED的项目
            if repo.assessment == "REJECTED":
                continue
            
            # 应用最低标准
            if repo.stars < self.config.min_stars:
                continue
            if repo.forks < self.config.min_forks:
                continue
            
            # 排除特定话题
            if any(topic in repo.topics for topic in self.config.exclude_topics):
                continue
            
            # 评估
            score, suggestion = self.assess_repo(repo)
            repo.quality_score = score
            repo.relevance_score = self._calculate_relevance(repo)
            repo.integration_suggestion = suggestion
            
            filtered.append(repo)
        
        return filtered
    
    def _calculate_relevance(self, repo: GitHubRepo) -> float:
        """计算与「破」项目的相关性"""
        relevance_keywords = [
            "agent", "autonomous", "ai", "llm", "gpt", "tool", "planning",
            "reasoning", "memory", "knowledge", "graph", "rag", "vector",
            "automation", "workflow", "task", "idea", "creative", "research"
        ]
        
        text = " ".join([
            repo.name.lower(),
            (repo.description or "").lower(),
            " ".join(repo.topics)
        ])
        
        matches = sum(1 for kw in relevance_keywords if kw in text)
        return min(10.0, matches * 1.5)
    
    def discover_new_repos(self) -> Dict[str, List[GitHubRepo]]:
        """发现新仓库"""
        results = {"trending": [], "keywords": []}
        
        # 1. 获取Trending
        if self.config.mode in ["trending", "both"]:
            for lang in self.config.trending_languages or ["Python", "TypeScript"]:
                repos = self.search_trending(lang, self.config.trending_since)
                filtered = self.filter_by_quality(repos)
                results["trending"].extend(filtered)
        
        # 2. 关键词搜索
        if self.config.mode in ["keywords", "both"]:
            repos = self.search_by_keywords(self.config.keywords, self.config.keywords_per_page)
            filtered = self.filter_by_quality(repos)
            results["keywords"].extend(filtered)
        
        # 3. 去重并更新状态
        new_repos = []
        for repos_list in results.values():
            for repo in repos_list:
                if repo.full_name not in self.repos:
                    self.repos[repo.full_name] = repo
                    new_repos.append(repo)
        
        # 保存
        if new_repos:
            self._save_data()
        
        return results
    
    def get_discovery_report(self, results: Dict[str, List[GitHubRepo]]) -> str:
        """生成发现报告"""
        lines = ["📊 **GitHub 项目监测报告**", "=" * 40, ""]
        
        total_new = sum(len(r) for r in results.values())
        lines.append(f"🆕 本次发现: **{total_new}** 个新项目\n")
        
        # 按分数排序
        all_repos = []
        for repos_list in results.values():
            all_repos.extend(repos_list)
        all_repos.sort(key=lambda x: x.quality_score, reverse=True)
        
        if all_repos:
            lines.append("**🔥 高分项目 (Top 5):**\n")
            for i, repo in enumerate(all_repos[:5], 1):
                lines.append(f"{i}. **{repo.full_name}** ⭐{repo.get_stars_display()}")
                lines.append(f"   {repo.description[:80]}..." if repo.description else "   (无描述)")
                lines.append(f"   📊 质量: {repo.quality_score} | 相关性: {repo.relevance_score}")
                lines.append(f"   💡 {repo.integration_suggestion}")
                lines.append("")
        
        # 分类统计
        if results["trending"]:
            lines.append(f"**📈 Trending**: {len(results['trending'])} 个项目")
        if results["keywords"]:
            lines.append(f"**🔍 关键词匹配**: {len(results['keywords'])} 个项目")
        
        lines.append("")
        lines.append(f"⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def get_summary(self) -> str:
        """获取监测摘要"""
        total = len(self.repos)
        by_status = {}
        for repo in self.repos.values():
            by_status[repo.assessment] = by_status.get(repo.assessment, 0) + 1
        
        lines = ["📊 **GitHub监测概览**", "-" * 30]
        lines.append(f"📦 总追踪项目: **{total}**")
        
        status_icons = {
            "PENDING": "⏳",
            "REVIEWED": "👀", 
            "INTERESTING": "⭐",
            "INTEGRATED": "✅",
            "REJECTED": "❌"
        }
        
        for status, count in sorted(by_status.items()):
            icon = status_icons.get(status, "📌")
            lines.append(f"{icon} {status}: {count}")
        
        return "\n".join(lines)
    
    def get_repo_details(self, owner: str, repo: str) -> Optional[str]:
        """获取仓库详情报告"""
        if f"{owner}/{repo}" not in self.repos:
            data = self.get_repository(owner, repo)
            if not data:
                return None
        
        stored = self.repos.get(f"{owner}/{repo}")
        if stored:
            score, _ = self.assess_repo(stored)
            stored.quality_score = score
        else:
            stored = GitHubRepo.from_github_api(data)
        
        readme = self.get_readme(owner, repo)[:2000]
        
        lines = [
            f"## 📦 {stored.full_name}",
            f"**描述**: {stored.description or '无'}",
            f"",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| ⭐ Stars | {stored.stars:,} |",
            f"| 🍴 Forks | {stored.forks:,} |",
            f"| 👁️ Watchers | {stored.watchers:,} |",
            f"| 🐛 Issues | {stored.open_issues} |",
            f"| 💻 语言 | {stored.language or '未知'} |",
            f"| 📄 许可 | {stored.license or '未指定'} |",
            f"| 📅 最近更新 | {stored.pushed_at[:10] if stored.pushed_at else '未知'} |",
            f"",
            f"**话题**: {', '.join(stored.topics) if stored.topics else '无'}",
            f"",
            f"**质量评分**: {stored.quality_score}/10",
            f"**相关性评分**: {stored.relevance_score}/10",
            f"",
            f"**集成建议**: {stored.integration_suggestion}",
            f"",
            f"**README预览**:",
            f"```",
            f"{readme[:500]}..." if len(readme) > 500 else f"```\n{readme}\n```",
            f"```",
            f"",
            f"[🔗 GitHub链接]({stored.url})"
        ]
        
        return "\n".join(lines)


# 默认配置
DEFAULT_CONFIG = GitHubMonitorConfig(
    mode="both",
    keywords=[
        "AI agent", "autonomous agent", "LLM tool use", 
        "AI assistant", "GPT agent", "LangChain alternative",
        "reasoning engine", "agent framework"
    ],
    keywords_per_page=20,
    trending_languages=["Python", "TypeScript", "JavaScript"],
    trending_since="daily",
    min_stars=50,
    min_forks=5,
    exclude_topics=["tutorial", "example", "demo"],
    preferred_licenses=["MIT", "Apache-2.0", "BSD-3-Clause"],
    star_weight=0.4,
    fork_weight=0.2,
    recency_weight=0.2,
    relevance_weight=0.2,
    notify_on_discovery=True,
    min_notify_score=7.0
)


def create_monitor(config: Optional[Dict] = None) -> GitHubMonitor:
    """创建监测器"""
    if config:
        cfg = GitHubMonitorConfig(**config)
    else:
        cfg = DEFAULT_CONFIG
    return GitHubMonitor(config=cfg)
