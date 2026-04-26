#!/usr/bin/env python3
"""
GitHub项目监测Cron任务
发现高价值AI/Agent项目，用于智能体能力提升
"""
import sys
import json
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.github_monitor import create_monitor, GitHubMonitorConfig


def run_github_monitor():
    """运行GitHub监测任务"""
    print("🔍 启动GitHub项目监测...")
    
    # 创建监测器（使用默认配置）
    monitor = create_monitor()
    
    print(f"📋 监测模式: {monitor.config.mode}")
    print(f"🔑 关键词: {', '.join(monitor.config.keywords[:3])}...")
    print(f"💻 监测语言: {', '.join(monitor.config.trending_languages)}")
    
    # 发现新项目
    print("\n⏳ 正在搜索项目...")
    results = monitor.discover_new_repos()
    
    # 生成报告
    report = monitor.get_discovery_report(results)
    print("\n" + report)
    
    # 检查高分项目（用于通知）
    high_score_repos = []
    for repos_list in results.values():
        for repo in repos_list:
            if repo.quality_score >= monitor.config.min_notify_score:
                high_score_repos.append(repo)
    
    # 保存报告
    report_path = Path("data/github_reports")
    report_path.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    report_file = report_path / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    # 生成摘要JSON（用于API读取）
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_discovered": sum(len(r) for r in results.values()),
        "trending_count": len(results.get("trending", [])),
        "keyword_count": len(results.get("keywords", [])),
        "high_score_projects": [
            {
                "full_name": r.full_name,
                "stars": r.stars,
                "quality_score": r.quality_score,
                "relevance_score": r.relevance_score,
                "suggestion": r.integration_suggestion,
                "url": r.url
            }
            for r in high_score_repos[:10]
        ]
    }
    
    summary_file = report_path / "latest.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 打印通知信息
    if high_score_repos and monitor.config.notify_on_discovery:
        print("\n" + "=" * 50)
        print("🚀 高价值项目发现!")
        print("=" * 50)
        for repo in high_score_repos[:3]:
            print(f"\n⭐ {repo.full_name}")
            print(f"   {repo.integration_suggestion}")
            print(f"   🔗 {repo.url}")
    
    print(f"\n✅ 监测完成! 报告已保存至: {report_file}")
    
    return report, summary


if __name__ == "__main__":
    run_github_monitor()
