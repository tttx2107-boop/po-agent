"""
知识沉淀服务
从想法复盘、GitHub项目等来源自动提取和积累知识
"""
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from collections import defaultdict

from src.models.knowledge import (
    KnowledgeEntry, KnowledgeType, KnowledgeSource, 
    KnowledgeCollection, ExtractionRule, DEFAULT_EXTRACTION_RULES,
    INDUSTRY_DOMAINS
)
from src.models.idea import Idea, Review


class KnowledgeService:
    """知识沉淀服务"""
    
    def __init__(self, data_path: str = "data/knowledge.json"):
        self.data_path = Path(data_path)
        self.collection = KnowledgeCollection()
        self.rules = DEFAULT_EXTRACTION_RULES.copy()
        self._load()
    
    def _load(self) -> None:
        """加载知识库"""
        if self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.collection = KnowledgeCollection.from_dict(data)
            except Exception as e:
                print(f"加载知识库失败: {e}")
    
    def _save(self) -> bool:
        """保存知识库"""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.collection.updated_at = datetime.now().isoformat()
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.collection.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    
    # ==================== 基础操作 ====================
    
    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """添加知识条目"""
        entry.id = entry.id or self._generate_id()
        entry.created_at = datetime.now().isoformat()
        entry.updated_at = entry.created_at
        
        self.collection.entries.append(entry)
        self._save()
        return entry
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        import hashlib
        timestamp = str(datetime.now().timestamp())
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """获取知识条目"""
        for entry in self.collection.entries:
            if entry.id == entry_id:
                return entry
        return None
    
    def delete(self, entry_id: str) -> bool:
        """删除知识条目"""
        for i, entry in enumerate(self.collection.entries):
            if entry.id == entry_id:
                self.collection.entries.pop(i)
                self._save()
                return True
        return False
    
    def update(self, entry_id: str, updates: Dict[str, Any]) -> Optional[KnowledgeEntry]:
        """更新知识条目"""
        entry = self.get(entry_id)
        if not entry:
            return None
        
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        entry.updated_at = datetime.now().isoformat()
        self._save()
        return entry
    
    # ==================== 查询接口 ====================
    
    def search(self, query: str, category: Optional[str] = None, 
               limit: int = 10) -> List[KnowledgeEntry]:
        """搜索知识"""
        query = query.lower()
        results = []
        
        for entry in self.collection.entries:
            # 分类过滤
            if category == "general" and not entry.is_general_knowledge():
                continue
            if category == "industry" and not entry.is_industry_knowledge():
                continue
            if category and category not in ["general", "industry"]:
                if entry.industry != category:
                    continue
            
            # 文本匹配
            score = 0
            if query in entry.content.lower():
                score += 3
            if query in entry.title.lower():
                score += 2
            if any(query in tag.lower() for tag in entry.tags):
                score += 2
            if any(query in tag.lower() for tag in entry.domain_tags):
                score += 1
            
            if score > 0:
                results.append((entry, score))
        
        # 按分数排序
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]
    
    def list_by_type(self, knowledge_type: str, limit: int = 50) -> List[KnowledgeEntry]:
        """按类型列出"""
        return [
            e for e in self.collection.entries 
            if e.type == knowledge_type
        ][:limit]
    
    def list_by_industry(self, industry: str, limit: int = 50) -> List[KnowledgeEntry]:
        """按行业列出"""
        return [
            e for e in self.collection.entries 
            if e.industry == industry
        ][:limit]
    
    def list_general(self, limit: int = 50) -> List[KnowledgeEntry]:
        """列出通用知识"""
        return [
            e for e in self.collection.entries 
            if e.is_general_knowledge()
        ][:limit]
    
    def list_industry(self, industry: Optional[str] = None, limit: int = 50) -> List[KnowledgeEntry]:
        """列出行业知识"""
        results = self.collection.entries
        if industry:
            results = [e for e in results if e.industry == industry]
        results = [e for e in results if e.is_industry_knowledge()]
        return results[:limit]
    
    # ==================== 知识提取 ====================
    
    def extract_from_review(self, idea: Idea, review: Review) -> List[KnowledgeEntry]:
        """从复盘记录提取知识"""
        extracted = []
        
        # 合并复盘内容
        content_parts = []
        if review.lessons:
            content_parts.append(f"经验教训: {review.lessons}")
        if review.next_actions:
            content_parts.append(f"后续行动: {review.next_actions}")
        if review.data:
            content_parts.append(f"数据: {json.dumps(review.data, ensure_ascii=False)}")
        
        full_content = "\n".join(content_parts)
        if not full_content:
            return extracted
        
        # 检测知识类型
        detected_type = self._detect_knowledge_type(full_content)
        detected_industry = self._detect_industry(idea.tags + review.data.get("tags", []))
        
        # 创建知识条目
        entry = KnowledgeEntry(
            id=self._generate_id(),
            content=self._summarize_content(full_content),
            title=self._extract_title(idea.content, full_content),
            type=detected_type,
            category="general" if not detected_industry else "industry",
            industry=detected_industry,
            source_type=KnowledgeSource.IDEA_REVIEW.value,
            source_id=idea.id,
            source_content=idea.content[:200],
            tags=idea.tags.copy(),
            domain_tags=[detected_industry] if detected_industry else [],
            extraction_confidence=self._calculate_confidence(full_content, detected_type),
            related_ideas=[idea.id]
        )
        
        extracted.append(entry)
        
        # 如果是成功案例，额外提取模式
        if review.result == "success" and review.lessons:
            pattern_entry = self._extract_pattern(review.lessons, idea, detected_industry)
            if pattern_entry:
                extracted.append(pattern_entry)
        
        return extracted
    
    def extract_from_github(self, repo_data: Dict[str, Any]) -> List[KnowledgeEntry]:
        """从GitHub项目提取知识"""
        extracted = []
        
        # 提取核心概念
        description = repo_data.get("description", "")
        topics = repo_data.get("topics", [])
        
        if description or topics:
            entry = KnowledgeEntry(
                id=self._generate_id(),
                content=description or " ".join(topics),
                title=repo_data.get("name", ""),
                type=KnowledgeType.INSPIRATION.value,
                category="general",
                source_type=KnowledgeSource.GITHUB_PROJECT.value,
                source_id=repo_data.get("full_name", ""),
                source_content=f"Stars: {repo_data.get('stars', 0)} | Forks: {repo_data.get('forks', 0)}",
                tags=topics[:5] if isinstance(topics, list) else [],
                domain_tags=self._detect_domain_tags(topics),
                extraction_confidence=0.7 if repo_data.get("stars", 0) > 1000 else 0.5
            )
            extracted.append(entry)
        
        # 如果是AI/Agent相关，提取设计模式
        ai_keywords = ["agent", "llm", "ai", "gpt", "tool", "reasoning"]
        if any(kw in str(topics).lower() for kw in ai_keywords):
            pattern_entry = KnowledgeEntry(
                id=self._generate_id(),
                content=f"AI Agent设计模式参考: {description}",
                title=f"来自 {repo_data.get('full_name')} 的架构灵感",
                type=KnowledgeType.PATTERN.value,
                category="general",
                source_type=KnowledgeSource.GITHUB_PROJECT.value,
                source_id=repo_data.get("full_name", ""),
                tags=["AI", "Agent", "架构"],
                extraction_confidence=0.8
            )
            extracted.append(pattern_entry)
        
        return extracted
    
    def _detect_knowledge_type(self, content: str) -> str:
        """检测知识类型"""
        content_lower = content.lower()
        
        scores = {
            KnowledgeType.PATTERN.value: 0,
            KnowledgeType.LESSON.value: 0,
            KnowledgeType.METHOD.value: 0,
            KnowledgeType.CONCEPT.value: 0
        }
        
        # 模式检测
        pattern_keywords = {
            KnowledgeType.PATTERN.value: ["成功", "有效", "可行", "验证", "证实"],
            KnowledgeType.LESSON.value: ["失败", "问题", "风险", "错误", "踩坑", "教训"],
            KnowledgeType.METHOD.value: ["方法", "策略", "流程", "步骤", "方案"],
            KnowledgeType.CONCEPT.value: ["概念", "原理", "本质", "定义", "理解"]
        }
        
        for ktype, keywords in pattern_keywords.items():
            scores[ktype] = sum(1 for kw in keywords if kw in content_lower)
        
        # 返回最高分类型
        if max(scores.values()) == 0:
            return KnowledgeType.CONCEPT.value
        return max(scores, key=scores.get)
    
    def _detect_industry(self, tags: List[str]) -> str:
        """检测行业"""
        tags_lower = [t.lower() for t in tags]
        
        for domain_id, domain in INDUSTRY_DOMAINS.items():
            if any(tag in tags_lower for tag in domain["tags"]):
                return domain_id
        
        return ""
    
    def _detect_domain_tags(self, topics: List[str]) -> List[str]:
        """从话题检测领域标签"""
        detected = []
        topics_lower = [t.lower() for t in topics]
        
        for domain_id, domain in INDUSTRY_DOMAINS.items():
            if any(tag in topics_lower for tag in domain["tags"]):
                detected.append(domain["name"])
        
        return detected
    
    def _summarize_content(self, content: str, max_len: int = 200) -> str:
        """摘要内容"""
        # 移除多余空白
        content = re.sub(r"\s+", " ", content).strip()
        
        # 移除"经验教训:"等前缀
        prefixes = ["经验教训:", "后续行动:", "数据:", "结果:"]
        for prefix in prefixes:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
        
        if len(content) <= max_len:
            return content
        
        # 在句号处截断
        truncated = content[:max_len]
        last_period = max(truncated.rfind("。"), truncated.rfind("."))
        if last_period > max_len * 0.5:
            return truncated[:last_period + 1]
        
        return truncated + "..."
    
    def _extract_title(self, idea_content: str, review_content: str) -> str:
        """提取标题"""
        # 取想法的前30个字符作为标题
        title = idea_content[:50].strip()
        if len(idea_content) > 50:
            title += "..."
        return title
    
    def _calculate_confidence(self, content: str, knowledge_type: str) -> float:
        """计算提取置信度"""
        base_confidence = 0.5
        
        # 内容长度加成
        if len(content) > 100:
            base_confidence += 0.1
        if len(content) > 300:
            base_confidence += 0.1
        
        # 类型关键词加成
        type_keywords = {
            KnowledgeType.PATTERN.value: ["成功", "验证", "可行"],
            KnowledgeType.LESSON.value: ["失败", "错误", "问题"],
            KnowledgeType.METHOD.value: ["方法", "步骤", "流程"],
            KnowledgeType.CONCEPT.value: ["概念", "原理"]
        }
        
        for kw in type_keywords.get(knowledge_type, []):
            if kw in content:
                base_confidence += 0.1
        
        return min(0.95, base_confidence)
    
    def _extract_pattern(self, lessons: str, idea: Idea, industry: str) -> Optional[KnowledgeEntry]:
        """提取执行模式"""
        if len(lessons) < 20:
            return None
        
        return KnowledgeEntry(
            id=self._generate_id(),
            content=lessons[:200],
            title=f"执行模式: {idea.content[:30]}...",
            type=KnowledgeType.PATTERN.value,
            category="industry" if industry else "general",
            industry=industry,
            source_type=KnowledgeSource.IDEA_REVIEW.value,
            source_id=idea.id,
            tags=["执行模式", "经验"] + idea.tags[:2],
            extraction_confidence=0.6
        )
    
    # ==================== 知识沉淀 ====================
    
    def accumulate(self, idea: Idea, reviews: List[Review]) -> List[KnowledgeEntry]:
        """沉淀想法中的知识"""
        all_extracted = []
        
        for review in reviews:
            extracted = self.extract_from_review(idea, review)
            all_extracted.extend(extracted)
        
        # 去重并添加
        existing_contents = {e.content[:50] for e in self.collection.entries}
        for entry in all_extracted:
            if entry.content[:50] not in existing_contents:
                self.add(entry)
        
        return all_extracted
    
    def accumulate_from_github(self, repos: List[Dict[str, Any]]) -> List[KnowledgeEntry]:
        """从GitHub项目沉淀知识"""
        all_extracted = []
        
        for repo in repos:
            extracted = self.extract_from_github(repo)
            all_extracted.extend(extracted)
        
        # 去重并添加
        existing_sources = {e.source_id for e in self.collection.entries}
        added = []
        for entry in all_extracted:
            if entry.source_id not in existing_sources:
                self.add(entry)
                added.append(entry)
        
        return added
    
    # ==================== 使用追踪 ====================
    
    def record_usage(self, entry_id: str, usefulness: float = 0.5) -> bool:
        """记录知识使用"""
        entry = self.get(entry_id)
        if not entry:
            return False
        
        entry.record_usage()
        entry.update_usefulness(usefulness)
        self._save()
        return True
    
    def get_popular(self, limit: int = 10) -> List[KnowledgeEntry]:
        """获取热门知识"""
        sorted_entries = sorted(
            self.collection.entries,
            key=lambda x: (x.usage_count, x.usefulness_score),
            reverse=True
        )
        return sorted_entries[:limit]
    
    def get_inspirations(self, industry: Optional[str] = None, limit: int = 10) -> List[KnowledgeEntry]:
        """获取灵感来源"""
        results = self.collection.entries
        if industry:
            results = [e for e in results if e.industry == industry]
        results = [e for e in results if e.type == KnowledgeType.INSPIRATION.value]
        return sorted(results, key=lambda x: x.extraction_confidence, reverse=True)[:limit]
    
    # ==================== 统计分析 ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        entries = self.collection.entries
        
        # 按类型统计
        by_type = defaultdict(int)
        for e in entries:
            by_type[e.type] += 1
        
        # 按行业统计
        by_industry = defaultdict(int)
        for e in entries:
            if e.industry:
                by_industry[e.industry] += 1
        
        # 使用统计
        total_usage = sum(e.usage_count for e in entries)
        avg_usefulness = sum(e.usefulness_score for e in entries) / len(entries) if entries else 0
        
        return {
            "total_entries": len(entries),
            "general_knowledge": len([e for e in entries if e.is_general_knowledge()]),
            "industry_knowledge": len([e for e in entries if e.is_industry_knowledge()]),
            "by_type": dict(by_type),
            "by_industry": dict(by_industry),
            "total_usage": total_usage,
            "avg_usefulness": round(avg_usefulness, 2),
            "top_entries": [
                {"id": e.id, "title": e.title[:30], "usage": e.usage_count}
                for e in self.get_popular(5)
            ]
        }
    
    def format_report(self) -> str:
        """生成知识库报告"""
        stats = self.get_statistics()
        
        lines = [
            "📚 **知识库概览**",
            "=" * 40,
            f"",
            f"📊 总量: **{stats['total_entries']}** 条",
            f"   ├─ 通用知识: {stats['general_knowledge']} 条",
            f"   └─ 行业知识: {stats['industry_knowledge']} 条",
            f"",
            f"📈 使用统计:",
            f"   ├─ 总使用次数: {stats['total_usage']}",
            f"   └─ 平均实用性: {stats['avg_usefulness']}",
            f"",
            f"🏷️ 知识类型分布:",
        ]
        
        for ktype, count in stats["by_type"].items():
            type_name = {
                "pattern": "执行模式",
                "lesson": "经验教训", 
                "concept": "核心概念",
                "method": "方法论",
                "inspiration": "灵感来源"
            }.get(ktype, ktype)
            lines.append(f"   ├─ {type_name}: {count}")
        
        if stats["by_industry"]:
            lines.append(f"")
            lines.append(f"🏢 行业分布:")
            for ind, count in stats["by_industry"].items():
                domain = INDUSTRY_DOMAINS.get(ind, {})
                icon = domain.get("icon", "📌")
                name = domain.get("name", ind)
                lines.append(f"   ├─ {icon} {name}: {count}")
        
        if stats["top_entries"]:
            lines.append(f"")
            lines.append(f"🔥 热门知识:")
            for entry in stats["top_entries"]:
                lines.append(f"   • {entry['title']} (使用{entry['usage']}次)")
        
        lines.append(f"")
        lines.append(f"⏰ 更新时间: {self.collection.updated_at[:19]}")
        
        return "\n".join(lines)


# 便捷函数
_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识服务单例"""
    global _service
    if _service is None:
        _service = KnowledgeService()
    return _service
