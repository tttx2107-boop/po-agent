#!/usr/bin/env python3
"""
知识沉淀测试脚本
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.knowledge import KnowledgeEntry, KnowledgeType, INDUSTRY_DOMAINS
from src.models.idea import Idea, Review, DeepAssessment
from src.services.knowledge_service import KnowledgeService, get_knowledge_service
from src.services.knowledge_miner import KnowledgeMiner, create_miner


def test_knowledge_service():
    """测试知识服务"""
    print("=" * 50)
    print("测试知识服务")
    print("=" * 50)
    
    # 创建服务
    service = KnowledgeService(data_path="data/test_knowledge.json")
    
    # 添加测试条目
    entries = [
        KnowledgeEntry(
            id="test1",
            content="模块化设计可以提高代码复用性",
            title="模块化设计原则",
            type=KnowledgeType.PATTERN.value,
            category="general",
            tags=["设计", "代码"],
            extraction_confidence=0.8
        ),
        KnowledgeEntry(
            id="test2",
            content="消防系统需要定期检测维护",
            title="消防系统维护要点",
            type=KnowledgeType.METHOD.value,
            category="industry",
            industry="fire_safety",
            tags=["消防", "维护"],
            extraction_confidence=0.9
        ),
        KnowledgeEntry(
            id="test3",
            content="Agent架构中Memory模块的重要性",
            title="Agent Memory设计",
            type=KnowledgeType.CONCEPT.value,
            category="industry",
            industry="ai",
            tags=["AI", "Agent", "Memory"],
            extraction_confidence=0.85
        )
    ]
    
    for entry in entries:
        service.add(entry)
    
    print(f"\n✅ 添加了 {len(entries)} 条知识")
    
    # 测试查询
    print("\n📊 统计信息:")
    stats = service.get_statistics()
    print(f"   总条目: {stats['total_entries']}")
    print(f"   通用知识: {stats['general_knowledge']}")
    print(f"   行业知识: {stats['industry_knowledge']}")
    print(f"   按类型: {stats['by_type']}")
    print(f"   按行业: {stats['by_industry']}")
    
    # 测试搜索
    print("\n🔍 搜索'消防':")
    results = service.search("消防")
    for r in results:
        print(f"   - {r.title} ({r.type})")
    
    # 测试分类查询
    print("\n📂 通用知识:")
    general = service.list_general()
    for g in general:
        print(f"   - {g.title}")
    
    print("\n📂 行业知识:")
    industry = service.list_industry()
    for i in industry:
        print(f"   - {i.title} ({INDUSTRY_DOMAINS.get(i.industry, {}).get('name', i.industry)})")
    
    # 测试使用记录
    if results:
        entry_id = results[0].id
        service.record_usage(entry_id, usefulness=0.8)
        print(f"\n✅ 记录了知识 {entry_id} 的使用")
    
    # 格式化报告
    print("\n" + service.format_report())
    
    # 清理测试数据
    Path("data/test_knowledge.json").unlink(missing_ok=True)
    
    return True


def test_extract_from_review():
    """测试从复盘提取知识"""
    print("\n" + "=" * 50)
    print("测试从复盘提取知识")
    print("=" * 50)
    
    service = KnowledgeService(data_path="data/test_extract.json")
    
    # 创建测试想法
    idea = Idea(
        id="idea_test",
        content="开发一个智能问答系统，结合知识图谱提升回答质量",
        tags=["AI", "知识图谱", "问答系统"]
    )
    
    # 创建复盘
    review = Review(
        date="2026-04-26",
        result="success",
        lessons="知识图谱的引入显著提升了问答的准确性。RAG模式比纯微调更有效。",
        next_actions="可以尝试将图谱与向量检索结合",
        data={"tags": ["AI", "RAG"]}
    )
    
    # 提取
    extracted = service.extract_from_review(idea, review)
    
    print(f"\n✅ 从复盘提取了 {len(extracted)} 条知识:")
    for entry in extracted:
        print(f"   - 类型: {entry.type}")
        print(f"   - 内容: {entry.content[:60]}...")
        print(f"   - 置信度: {entry.extraction_confidence}")
        print()
    
    # 清理
    Path("data/test_extract.json").unlink(missing_ok=True)
    
    return len(extracted) > 0


def test_miner():
    """测试挖掘器"""
    print("\n" + "=" * 50)
    print("测试知识挖掘器")
    print("=" * 50)
    
    miner = create_miner()
    
    # 创建测试想法
    idea = Idea(
        id="idea_miner_test",
        content="研究基于LLM的自主Agent框架",
        tags=["AI", "Agent", "LLM"]
    )
    
    # 添加复盘
    idea.reviews.append(Review(
        date="2026-04-26",
        result="success",
        lessons="Agent需要明确的工具定义和执行策略。使用ReAct模式效果良好。",
        next_actions="可以尝试添加规划器模块"
    ))
    
    # 挖掘
    extracted = miner.mine_from_idea(idea)
    
    print(f"\n✅ 挖掘了 {len(extracted)} 条知识:")
    for entry in extracted:
        print(f"   [{entry.type}] {entry.title}")
    
    # 获取推荐
    print("\n💡 推荐知识:")
    recommendations = miner.get_recommendations(current_idea=idea, limit=3)
    for rec in recommendations:
        print(f"   - {rec.title}")
    
    return len(extracted) > 0


def main():
    print("🚀 开始知识沉淀功能测试\n")
    
    all_passed = True
    
    all_passed &= test_knowledge_service()
    all_passed &= test_extract_from_review()
    all_passed &= test_miner()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败")
    print("=" * 50)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
