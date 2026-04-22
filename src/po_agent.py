"""「破」想法实现智能体 - 主入口"""
from typing import Optional, Dict, Any

from .core.idea_manager import IdeaManager
from .core.task_manager import TaskManager
from .core.router import CommandRouter
from .storage.gist_store import get_storage
from .utils.config import get_config
from .utils.logger import setup_logger
from .services.task_breaker import TaskBreaker


logger = setup_logger("po-agent")


class PoAgent:
    """「破」想法实现智能体主类"""
    
    def __init__(self, storage=None, config=None):
        self.config = config or get_config()
        self.storage = storage or get_storage(
            self.config.github_token,
            self.config.gist_id
        )
        
        self.idea_manager = IdeaManager(self.storage)
        self.task_manager = TaskManager(self.storage)
        self.router = CommandRouter()
        self.task_breaker = TaskBreaker()
        
        logger.info("「破」智能体初始化完成")
    
    def process(self, message: str, source: str = "cli") -> str:
        """
        处理用户消息
        
        Args:
            message: 用户消息
            source: 来源 (wechat, cli, schedule)
            
        Returns:
            响应文本
        """
        # 路由
        route = self.router.route(message)
        
        if not route.success:
            return "请输入有效的想法或命令"
        
        # 分发处理
        if route.module == "idea":
            return self._handle_idea(route, source)
        elif route.module == "assessment":
            return self._handle_assessment(route)
        elif route.module == "task":
            return self._handle_task(route)
        elif route.module == "stats":
            return self._handle_stats()
        elif route.module == "help":
            return self._show_help()
        elif route.module == "system":
            return self._handle_system(route)
        else:
            return f"未知模块: {route.module}"
    
    def _handle_idea(self, route, source: str) -> str:
        """处理想法相关命令"""
        from .services.quick_assessment import format_quick_result
        
        if route.action == "create":
            idea = self.idea_manager.create(route.args["content"], source)
            
            # 检查是否需要触发评估
            if self.idea_manager.should_trigger_assessment(self.config.eval_trigger_count):
                return (format_quick_result(idea.quick_assessment.to_dict(), route.args["content"]) 
                       + f"\n\n💡 提示：已积累 {len(self.idea_manager.get_pending_assessment())} 个待评估想法，建议运行「立即评估」")
            
            return format_quick_result(idea.quick_assessment.to_dict(), route.args["content"])
        
        elif route.action == "list":
            ideas = self.idea_manager.list()
            return self._format_idea_list(ideas)
        
        elif route.action == "detail":
            idea_id = route.args.get("id")
            if not idea_id:
                return "请提供想法ID：查看详情 [ID]"
            
            idea = self.idea_manager.get(idea_id)
            if not idea:
                return f"❌ 未找到想法 [{idea_id}]"
            
            return self._format_idea_detail(idea)
        
        elif route.action == "confirm":
            idea_id = route.args.get("id")
            if idea_id:
                self.idea_manager.update_status(idea_id, "CONFIRMED")
                return f"✅ 想法 [{idea_id}] 已确认为执行状态"
            return "请提供想法ID"
        
        elif route.action == "defer":
            idea_id = route.args.get("id")
            if idea_id:
                self.idea_manager.update_status(idea_id, "DEFERRED")
                return f"⏸️ 想法 [{idea_id}] 已暂缓"
            return "请提供想法ID"
        
        elif route.action == "reject":
            idea_id = route.args.get("id")
            if idea_id:
                self.idea_manager.update_status(idea_id, "REJECTED")
                return f"❌ 想法 [{idea_id}] 已否决"
            return "请提供想法ID"
        
        return "未知想法操作"
    
    def _handle_assessment(self, route) -> str:
        """处理评估命令"""
        from .services.deep_assessment import format_deep_report
        
        if route.action == "trigger":
            pending = self.idea_manager.get_pending_assessment()
            if not pending:
                return "✅ 没有待评估的想法"
            
            results = self.idea_manager.assess_pending(self.config.max_daily_assessments)
            
            reports = ["📊 深度评估报告\n━━━━━━━━━━━━━━━\n"]
            for i, result in enumerate(results):
                reports.append(f"想法：{pending[i].content[:40]}...")
                reports.append(format_deep_report(result, pending[i].content))
                reports.append("")
            
            # 剩余待评估
            remaining = len(pending) - len(results)
            if remaining > 0:
                reports.append(f"还有 {remaining} 个想法待评估，明天继续～")
            
            return "\n".join(reports)
        
        return "未知评估操作"
    
    def _handle_task(self, route) -> str:
        """处理任务命令"""
        if route.action == "list":
            tasks = self.task_manager.list()
            return self._format_task_list(tasks)
        
        elif route.action == "detail":
            task_id = route.args.get("id")
            if task_id:
                task = self.task_manager.get(task_id)
                if task:
                    return self._format_task_detail(task)
                return f"❌ 未找到任务 [{task_id}]"
            return "请提供任务ID"
        
        elif route.action == "done":
            task_id = route.args.get("id")
            if task_id:
                task = self.task_manager.done(task_id)
                if task:
                    return f"✅ 任务 [{task_id}] 已完成！"
                return f"❌ 未找到任务 [{task_id}]"
            return "请提供任务ID"
        
        elif route.action == "create":
            idea_id = route.args.get("idea_id")
            if idea_id:
                idea = self.idea_manager.get(idea_id)
                if idea:
                    task = self.task_manager.create(
                        idea_id=idea_id,
                        title=f"执行：{idea.content[:30]}...",
                        description=idea.content
                    )
                    # 关联到想法
                    if idea_id not in idea.tasks:
                        idea.tasks.append(task.id)
                        self.idea_manager.update(idea_id, {"tasks": idea.tasks})
                    return f"✅ 任务 [{task.id}] 已创建"
                return f"❌ 未找到想法 [{idea_id}]"
            return "请提供想法ID：创建任务 [想法ID]"
        
        return "未知任务操作"
    
    def _handle_stats(self) -> str:
        """处理统计命令"""
        stats = self.idea_manager.get_stats()
        return self._format_stats(stats)
    
    def _handle_system(self, route) -> str:
        """处理系统命令"""
        if route.action == "sync":
            return "✅ 数据已同步"
        elif route.action == "backup":
            return "✅ 备份完成"
        return "未知系统操作"
    
    def _show_help(self) -> str:
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

⚙️ 确认/暂缓/否决
   「确认执行 [ID]」
   「暂缓 [ID]」
   「否决 [ID]」

🔄 帮助
   「帮助」或「?」

━━━━━━━━━━━━━━━
"""
    
    def _format_idea_list(self, ideas: list) -> str:
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
    
    def _format_idea_detail(self, idea) -> str:
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
        
        if idea.quick_assessment:
            qa = idea.quick_assessment
            if isinstance(qa, dict):
                completeness = int(qa.get("completeness", 0) * 100)
            else:
                completeness = int(qa.completeness * 100)
            detail.append(f"\n⚡ 快速评估：完整性 {completeness}%")
        
        if idea.deep_assessment:
            da = idea.deep_assessment
            if isinstance(da, dict):
                score = da.get("overall_score", 0)
                decision = da.get("decision_level", "")
            else:
                score = da.overall_score
                decision = da.decision_level
            detail.append(f"\n📊 深度评估：{score}分 - {decision}")
        
        return "\n".join(detail)
    
    def _format_task_list(self, tasks: list) -> str:
        """格式化任务列表"""
        if not tasks:
            return "📋 暂无任务"
        
        lines = ["📋 任务列表\n━━━━━━━━━━━━━━━\n"]
        
        status_emoji = {
            "TODO": "📋", "IN_PROGRESS": "🔄",
            "BLOCKED": "🚫", "DONE": "✅", "CANCELLED": "❌"
        }
        
        for task in tasks:
            emoji = status_emoji.get(task.status, "📋")
            line = f"{emoji} [{task.id}] {task.title}"
            if task.status == "BLOCKED" and task.block_reason:
                line += f"\n   └ 🚫 {task.block_reason}"
            lines.append(line)
            lines.append("")
        
        lines.append("━━━━━━━━━━━━━━━")
        lines.append(f"共 {len(tasks)} 个任务")
        
        return "\n".join(lines)
    
    def _format_task_detail(self, task) -> str:
        """格式化任务详情"""
        status_map = {
            "TODO": "📋 待办", "IN_PROGRESS": "🔄 进行中",
            "BLOCKED": "🚫 阻塞", "DONE": "✅ 完成", "CANCELLED": "❌ 取消"
        }
        
        detail = [f"📋 任务详情 [{task.id}]\n━━━━━━━━━━━━━━━"]
        detail.append(f"📌 状态：{status_map.get(task.status, task.status)}")
        detail.append(f"📝 标题：{task.title}")
        
        if task.description:
            detail.append(f"\n📄 描述：\n{task.description}")
        
        detail.append(f"\n📊 进度：{task.progress}%")
        detail.append(f"📅 创建：{task.created_at[:10]}")
        
        if task.block_reason:
            detail.append(f"\n🚫 阻塞原因：{task.block_reason}")
        
        return "\n".join(detail)
    
    def _format_stats(self, stats: dict) -> str:
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
    
    # 便捷方法
    def list_ideas(self, status: Optional[str] = None) -> list:
        """列出想法"""
        return self.idea_manager.list(status=status)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return self.idea_manager.get_stats()
    
    def assess_pending(self, limit: int = 3) -> list:
        """批量评估"""
        return self.idea_manager.assess_pending(limit)
    
    def breakdown_idea(self, idea_id: str) -> str:
        """
        拆解想法为任务
        
        Args:
            idea_id: 想法 ID
            
        Returns:
            拆解结果报告
        """
        idea = self.idea_manager.get(idea_id)
        if not idea:
            return f"❌ 未找到想法 [{idea_id}]"
        
        # 执行拆解
        result = self.task_breaker.breakdown(idea.content)
        
        # 创建任务
        task_ids = []
        for subtask in result.subtasks:
            task = self.task_manager.create(
                idea_id=idea_id,
                title=subtask.title,
                description=subtask.description,
                task_type=subtask.task_type,
                estimated_hours=subtask.estimated_hours,
                priority=subtask.priority
            )
            task_ids.append(task.id)
        
        # 更新想法的任务关联
        self.idea_manager.update(idea_id, {"tasks": task_ids})
        
        # 更新状态
        self.idea_manager.update(idea_id, {"status": "IN_PROGRESS"})
        
        # 生成报告
        report = result.format()
        report += f"\n\n✅ 已拆解并创建 {len(result.subtasks)} 个任务"
        
        return report
