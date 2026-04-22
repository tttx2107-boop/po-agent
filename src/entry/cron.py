"""定时任务入口"""
import sys
import argparse
from typing import Optional

from ..core.idea_manager import IdeaManager
from ..core.task_manager import TaskManager
from ..services.deep_assessment import format_deep_report
from ..utils.config import get_config
from ..utils.logger import setup_logger


logger = setup_logger("po-agent.cron")


def run_weekly_assessment(storage, notifier: Optional[callable] = None) -> dict:
    """
    运行每周评估任务
    
    Args:
        storage: 存储实例
        notifier: 通知回调函数
        
    Returns:
        执行结果
    """
    logger.info("开始每周评估任务")
    
    idea_manager = IdeaManager(storage)
    
    # 检查是否有待评估想法
    pending = idea_manager.get_pending_assessment()
    
    if not pending:
        logger.info("没有待评估的想法")
        return {"success": True, "assessed": 0}
    
    # 获取配置
    config = get_config()
    limit = config.max_daily_assessments
    
    # 执行评估
    results = idea_manager.assess_pending(limit)
    
    logger.info(f"评估完成，共评估 {len(results)} 个想法")
    
    # 生成报告
    reports = []
    for i, result in enumerate(results):
        idea = pending[i]
        report = format_deep_report(result, idea.content)
        reports.append(report)
        
        # 发送通知
        if notifier:
            notifier(f"📊 评估报告 - {idea.content[:30]}...\n\n{report}")
    
    return {
        "success": True,
        "assessed": len(results),
        "pending_left": len(pending) - len(results),
        "reports": reports
    }


def run_reminder(storage, notifier: Optional[callable] = None) -> dict:
    """
    运行提醒任务
    
    检查并发送提醒：
    - 阻塞超过3天的任务
    - 逾期任务
    - 待评估想法
    """
    logger.info("开始提醒任务")
    
    idea_manager = IdeaManager(storage)
    task_manager = TaskManager(storage)
    
    messages = []
    
    # 检查待评估想法
    pending_ideas = idea_manager.get_pending_assessment()
    if pending_ideas:
        msg = f"📋 您有 {len(pending_ideas)} 个想法待评估"
        messages.append(msg)
    
    # 检查阻塞任务
    blocked_tasks = task_manager.get_blocked()
    if blocked_tasks:
        msg = f"🚫 您有 {len(blocked_tasks)} 个任务被阻塞：\n"
        for task in blocked_tasks[:3]:
            msg += f"  - {task.title}\n"
            if task.block_reason:
                msg += f"    原因：{task.block_reason}\n"
        messages.append(msg)
    
    # 检查逾期任务
    overdue_tasks = task_manager.get_overdue()
    if overdue_tasks:
        msg = f"⚠️ 您有 {len(overdue_tasks)} 个任务逾期：\n"
        for task in overdue_tasks[:3]:
            msg += f"  - {task.title}\n"
        messages.append(msg)
    
    # 发送通知
    if messages and notifier:
        full_msg = "📊 「破」提醒\n\n" + "\n\n".join(messages)
        notifier(full_msg)
    
    return {
        "success": True,
        "messages": messages
    }


def run_backup(storage) -> dict:
    """运行备份任务"""
    logger.info("开始备份任务")
    
    try:
        # Gist 存储已自动备份
        # 可以添加其他备份逻辑
        logger.info("备份完成")
        return {"success": True}
    except Exception as e:
        logger.error(f"备份失败: {e}")
        return {"success": False, "error": str(e)}


def main():
    """定时任务入口"""
    parser = argparse.ArgumentParser(description="「破」定时任务")
    parser.add_argument("task", choices=["assessment", "reminder", "backup"],
                        help="任务类型")
    args = parser.parse_args()
    
    # 加载配置
    config = get_config()
    
    # 初始化存储
    from ..storage.gist_store import get_storage
    storage = get_storage(config.github_token, config.gist_id)
    
    # 执行任务
    if args.task == "assessment":
        result = run_weekly_assessment(storage)
    elif args.task == "reminder":
        result = run_reminder(storage)
    elif args.task == "backup":
        result = run_backup(storage)
    
    print(result)
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
