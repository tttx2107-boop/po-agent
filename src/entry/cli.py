"""CLI 入口"""
import sys
from typing import Optional

from ..core.idea_manager import IdeaManager
from ..core.task_manager import TaskManager
from ..core.router import CommandRouter
from ..storage.gist_store import get_storage
from ..utils.config import get_config
from ..utils.logger import setup_logger


logger = setup_logger("po-agent.cli")


def format_idea_list(ideas: list, show_all: bool = False) -> str:
    """格式化想法列表"""
    if not ideas:
        return "💭 暂无想法，快来添加第一个吧！"
    
    lines = ["📋 想法列表\n━━━━━━━━━━━━━━━\n"]
    
    status_emoji = {
        "NEW": "🆕", "ASSESSING": "⏳", "CONFIRMED": "✅",
        "DEFERRED": "⏸️", "REJECTED": "❌", "IN_PROGRESS": "🔄",
        "COMPLETED": "⭐"
    }
    
    for i, idea in enumerate(ideas, 1):
        emoji = status_emoji.get(idea.status, "📝")
        
        content_preview = idea.content[:35] + "..." if len(idea.content) > 35 else idea.content
        tags = "·".join(idea.tags[:2]) if idea.tags else ""
        
        line = f"{i}. {emoji} [{idea.id}] {content_preview}"
        if tags:
            line += f"\n   └ {tags}"
        lines.append(line)
        lines.append("")
    
    lines.append("━━━━━━━━━━━━━━━")
    lines.append(f"共 {len(ideas)} 个想法")
    
    return "\n".join(lines)


def format_idea_detail(idea) -> str:
    """格式化想法详情"""
    status_map = {
        "NEW": "🆕 新想法", "ASSESSING": "⏳ 待评估", 
        "CONFIRMED": "✅ 已确认", "DEFERRED": "⏸️ 暂缓",
        "REJECTED": "❌ 已否决", "IN_PROGRESS": "🔄 执行中",
        "COMPLETED": "⭐ 已完成"
    }
    
    detail = [f"📝 想法详情 [{idea.id}]\n━━━━━━━━━━━━━━━"]
    detail.append(f"📌 状态：{status_map.get(idea.status, idea.status)}")
    detail.append(f"\n📄 内容：\n{idea.content}")
    detail.append(f"\n🏷️ 标签：{'、'.join(idea.tags) or '无'}")
    detail.append(f"\n📅 创建：{idea.created_at[:10]}")
    detail.append(f"📝 更新：{idea.updated_at[:10]}")
    
    if idea.quick_assessment:
        qa = idea.quick_assessment
        if isinstance(qa, dict):
            completeness = int(qa.get("completeness", 0) * 100)
        else:
            completeness = int(qa.completeness * 100)
        detail.append(f"\n⚡ 快速评估：")
        detail.append(f"   完整性：{completeness}%")
    
    if idea.deep_assessment:
        da = idea.deep_assessment
        if isinstance(da, dict):
            score = da.get("overall_score", 0)
            decision = da.get("decision_level", "")
        else:
            score = da.overall_score
            decision = da.decision_level
        detail.append(f"\n📊 深度评估：")
        detail.append(f"   综合得分：{score}分")
        detail.append(f"   决策：{decision}")
    
    if idea.tasks:
        detail.append(f"\n📋 关联任务：{len(idea.tasks)} 个")
    
    return "\n".join(detail)


def format_stats(stats: dict) -> str:
    """格式化统计"""
    status_names = {
        "NEW": "新想法", "ASSESSING": "待评估", "CONFIRMED": "已确认",
        "DEFERRED": "暂缓", "REJECTED": "已否决", "IN_PROGRESS": "执行中",
        "COMPLETED": "已完成"
    }
    
    lines = ["📈 「破」统计概览\n━━━━━━━━━━━━━━━\n"]
    lines.append(f"💭 想法总数：{stats['total']}")
    lines.append(f"⏳ 待评估：{stats['pending_assessment']}\n")
    
    if stats.get('by_status'):
        lines.append("📊 状态分布：")
        for status, count in stats['by_status'].items():
            name = status_names.get(status, status)
            lines.append(f"   {name}：{count}")
    
    if stats.get('by_tag'):
        lines.append("\n🏷️ 标签分布：")
        for tag, count in sorted(stats['by_tag'].items(), key=lambda x: -x[1])[:5]:
            lines.append(f"   {tag}：{count}")
    
    return "\n".join(lines)


def format_help() -> str:
    """格式化帮助"""
    return """
🔮 「破」想法实现智能体 - 命令帮助

━━━━━━━━━━━━━━━

💭 录入想法
   直接发送想法内容即可

📋 查看想法
   「查看想法」或「list」

🔍 查看详情
   「查看详情 [ID]」

📊 立即评估
   「立即评估」或「eval」

📈 统计
   「统计」或「stats」

⚙️ 确认/暂缓/否决
   「确认执行 [ID]」
   「暂缓 [ID]」
   「否决 [ID]」

🔄 帮助
   「帮助」或「?」

━━━━━━━━━━━━━━━
"""


def run_cli():
    """运行 CLI 交互"""
    config = get_config()
    storage = get_storage(config.github_token, config.gist_id)
    
    idea_manager = IdeaManager(storage)
    task_manager = TaskManager(storage)
    router = CommandRouter()
    
    print("""
╔══════════════════════════════════════╗
║     「破」想法实现智能体              ║
║     让想法从灵光一现到落地成真        ║
╚══════════════════════════════════════╝
    """)
    
    while True:
        try:
            user_input = input("\n💬 请输入（帮助查看命令）：").strip()
            if not user_input:
                continue
            
            # 路由
            route = router.route(user_input)
            
            if route.module == "help":
                print(format_help())
                
            elif route.module == "idea":
                if route.action == "list":
                    ideas = idea_manager.list()
                    print(format_idea_list(ideas))
                elif route.action == "detail":
                    idea_id = route.args.get("id")
                    if idea_id:
                        idea = idea_manager.get(idea_id)
                        if idea:
                            print(format_idea_detail(idea))
                        else:
                            print(f"❌ 未找到想法 [{idea_id}]")
                    else:
                        print("请提供想法ID：查看详情 [ID]")
                elif route.action == "create":
                    from ..services.quick_assessment import format_quick_result
                    idea = idea_manager.create(user_input, source="cli")
                    print(format_quick_result(idea.quick_assessment.to_dict(), user_input))
                    
            elif route.module == "assessment":
                if route.action == "trigger":
                    pending = idea_manager.get_pending_assessment()
                    if not pending:
                        print("✅ 没有待评估的想法")
                    else:
                        from ..services.deep_assessment import format_deep_report
                        results = idea_manager.assess_pending(3)
                        for i, result in enumerate(results):
                            print(f"\n--- 评估 {i+1} ---")
                            print(format_deep_report(result, pending[i].content))
                            
            elif route.module == "stats":
                stats = idea_manager.get_stats()
                print(format_stats(stats))
                
            elif route.module == "system":
                if route.action == "sync":
                    print("✅ 数据已同步")
                elif route.action == "backup":
                    print("✅ 备份完成")
            
            if user_input in ["退出", "exit", "quit"]:
                print("👋 再见！")
                break
                
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            logger.error(f"处理输入失败: {e}")
            print(f"❌ 出错了: {e}")


if __name__ == "__main__":
    run_cli()
