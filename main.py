"""「破」想法实现智能体 - 主入口"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from config import GITHUB_TOKEN, GITHUB_USER, GIST_ID, EVAL_TRIGGER_COUNT
from storage import get_storage
from quick_assessment import QuickAssessment, format_quick_result
from deep_assessment import DeepAssessment, format_deep_report


class PoAgent:
    """「破」想法实现智能体主类"""
    
    def __init__(self):
        self.storage = get_storage(GITHUB_TOKEN, GIST_ID)
        self.quick_assessor = QuickAssessment()
        self.deep_assessor = DeepAssessment()
        self.ideas: List[Dict[str, Any]] = []
        self._load_ideas()
    
    def _load_ideas(self):
        """加载想法数据"""
        self.ideas = self.storage.read()
        print(f"已加载 {len(self.ideas)} 条想法")
    
    def _save_ideas(self) -> bool:
        """保存想法数据"""
        success = self.storage.write(self.ideas)
        if success:
            print(f"已保存 {len(self.ideas)} 条想法到存储")
        return success
    
    def add_idea(self, content: str, source: str = "cli") -> Dict[str, Any]:
        """添加新想法"""
        assessment = self.quick_assessor.assess(content)
        
        idea = {
            "id": str(uuid.uuid4())[:8],
            "content": content,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "source": source,
            "tags": assessment["domain_tags"],
            "status": "NEW",
            "quick_assessment": assessment,
            "deep_assessment": None,
            "tasks": [],
            "progress": 0,
            "reviews": []
        }
        
        self.ideas.append(idea)
        self._save_ideas()
        
        # 检查是否需要触发深度评估
        self._check_eval_trigger()
        
        return idea
    
    def _check_eval_trigger(self):
        """检查是否触发深度评估"""
        pending = [i for i in self.ideas if i["status"] == "NEW"]
        if len(pending) >= EVAL_TRIGGER_COUNT:
            print(f"\n⏰ 已积累 {len(pending)} 个待评估想法，建议运行「立即评估」")
    
    def list_ideas(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出想法"""
        if status:
            return [i for i in self.ideas if i.get("status") == status]
        return self.ideas
    
    def get_idea(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """获取想法详情"""
        for idea in self.ideas:
            if idea["id"] == idea_id:
                return idea
        return None
    
    def assess_idea(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """深度评估单个想法"""
        idea = self.get_idea(idea_id)
        if not idea:
            return None
        
        assessment = self.deep_assessor.assess(idea)
        idea["deep_assessment"] = assessment
        idea["updated_at"] = datetime.now().isoformat()
        
        # 更新状态
        if assessment["decision"]["action"] in ["优先执行"]:
            idea["status"] = "CONFIRMED"
        elif assessment["decision"]["action"] in ["可考虑执行"]:
            idea["status"] = "CONFIRMED"
        elif assessment["decision"]["action"] in ["持续关注"]:
            idea["status"] = "DEFERRED"
        else:
            idea["status"] = "REJECTED"
        
        self._save_ideas()
        return assessment
    
    def assess_pending(self, limit: int = 3) -> List[Dict[str, Any]]:
        """评估所有待评估想法"""
        pending = [i for i in self.ideas if i["status"] in ["NEW", "ASSESSING"]]
        results = []
        
        for idea in pending[:limit]:
            result = self.assess_idea(idea["id"])
            if result:
                results.append((idea, result))
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        total = len(self.ideas)
        by_status = {}
        by_tag = {}
        
        for idea in self.ideas:
            # 按状态统计
            status = idea.get("status", "UNKNOWN")
            by_status[status] = by_status.get(status, 0) + 1
            
            # 按标签统计
            for tag in idea.get("tags", []):
                by_tag[tag] = by_tag.get(tag, 0) + 1
        
        return {
            "total": total,
            "by_status": by_status,
            "by_tag": by_tag,
            "pending_assessment": len([i for i in self.ideas if i["status"] == "NEW"])
        }
    
    def process(self, user_input: str) -> str:
        """
        处理用户输入
        
        支持的命令：
        - 直接发送想法 → 录入并快速评估
        - 查看想法 / list → 列表
        - 查看详情 [ID] / detail [ID] → 详情
        - 立即评估 / eval → 深度评估
        - 统计 / stats → 统计
        - 帮助 / help → 帮助
        """
        user_input = user_input.strip()
        
        # 命令处理
        if user_input in ["帮助", "help"]:
            return self._help()
        
        if user_input in ["查看想法", "list"]:
            return self._list_ideas()
        
        if user_input.startswith("查看详情 ") or user_input.startswith("detail "):
            parts = user_input.split(" ", 1)
            if len(parts) == 2:
                return self._show_detail(parts[1])
            return "请提供想法ID：查看详情 [ID]"
        
        if user_input in ["立即评估", "eval"]:
            return self._do_eval()
        
        if user_input in ["统计", "stats"]:
            return self._stats()
        
        # 直接发送的想法
        idea = self.add_idea(user_input, source="cli")
        return format_quick_result(idea["quick_assessment"], user_input)
    
    def _help(self) -> str:
        """显示帮助"""
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

━━━━━━━━━━━━━━━
"""
    
    def _list_ideas(self) -> str:
        """列出想法"""
        if not self.ideas:
            return "💭 暂无想法，快来添加第一个吧！"
        
        lines = ["📋 想法列表\n━━━━━━━━━━━━━━━\n"]
        for i, idea in enumerate(self.ideas, 1):
            status_emoji = {
                "NEW": "🆕", "ASSESSING": "⏳", "CONFIRMED": "✅",
                "DEFERRED": "⏸️", "REJECTED": "❌", "IN_PROGRESS": "🔄",
                "COMPLETED": "⭐"
            }
            emoji = status_emoji.get(idea.get("status", "NEW"), "📝")
            
            content_preview = idea["content"][:30] + "..." if len(idea["content"]) > 30 else idea["content"]
            tags = "·".join(idea.get("tags", [])[:2]) or ""
            
            lines.append(f"{i}. {emoji} [{idea['id']}] {content_preview}")
            if tags:
                lines.append(f"   └ {tags}")
            lines.append("")
        
        lines.append("━━━━━━━━━━━━━━━")
        lines.append(f"共 {len(self.ideas)} 个想法")
        return "\n".join(lines)
    
    def _show_detail(self, idea_id: str) -> str:
        """显示想法详情"""
        idea = self.get_idea(idea_id)
        if not idea:
            return f"❌ 未找到想法 [{idea_id}]"
        
        status_emoji = {
            "NEW": "🆕 新想法", "ASSESSING": "⏳ 待评估", "CONFIRMED": "✅ 已确认",
            "DEFERRED": "⏸️ 暂缓", "REJECTED": "❌ 已否决", "IN_PROGRESS": "🔄 执行中",
            "COMPLETED": "⭐ 已完成"
        }
        
        detail = f"""📝 想法详情 [{idea['id']}]

━━━━━━━━━━━━━━━

📌 状态：{status_emoji.get(idea.get('status', 'NEW'), '📝')}

📄 内容：
{idea['content']}

🏷️ 标签：{'、'.join(idea.get('tags', [])) or '无'}

📅 创建：{idea['created_at'][:10]}
"""
        
        if idea.get("quick_assessment"):
            qa = idea["quick_assessment"]
            detail += f"\n⚡ 快速评估：\n"
            detail += f"   完整性：{int(qa['completeness']*100)}%\n"
            detail += f"   备注：{qa['keywords_note']}\n"
        
        if idea.get("deep_assessment"):
            detail += f"\n📊 深度评估：\n"
            detail += f"   综合得分：{idea['deep_assessment']['overall_score']}分\n"
            detail += f"   决策：{idea['deep_assessment']['decision']['level']}\n"
        
        return detail
    
    def _do_eval(self) -> str:
        """执行深度评估"""
        results = self.assess_pending(limit=3)
        
        if not results:
            return "✅ 没有待评估的想法"
        
        reports = ["📊 深度评估报告\n━━━━━━━━━━━━━━━\n"]
        for idea, assessment in results:
            reports.append(f"想法：{idea['content'][:40]}...")
            reports.append(format_deep_report(assessment, idea["content"]))
            reports.append("")
        
        return "\n".join(reports)
    
    def _stats(self) -> str:
        """显示统计"""
        stats = self.get_stats()
        
        status_names = {
            "NEW": "新想法", "ASSESSING": "待评估", "CONFIRMED": "已确认",
            "DEFERRED": "暂缓", "REJECTED": "已否决", "IN_PROGRESS": "执行中",
            "COMPLETED": "已完成"
        }
        
        lines = ["📈 「破」统计概览\n━━━━━━━━━━━━━━━\n"]
        lines.append(f"💭 想法总数：{stats['total']}")
        lines.append(f"⏳ 待评估：{stats['pending_assessment']}\n")
        
        if stats['by_status']:
            lines.append("📊 状态分布：")
            for status, count in stats['by_status'].items():
                name = status_names.get(status, status)
                lines.append(f"   {name}：{count}")
        
        if stats['by_tag']:
            lines.append("\n🏷️ 标签分布：")
            for tag, count in sorted(stats['by_tag'].items(), key=lambda x: -x[1]):
                lines.append(f"   {tag}：{count}")
        
        return "\n".join(lines)


def main():
    """CLI 入口"""
    agent = PoAgent()
    
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
            
            response = agent.process(user_input)
            print(f"\n{response}")
            
            if user_input in ["退出", "exit", "quit"]:
                print("👋 再见！")
                break
                
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break


if __name__ == "__main__":
    main()
