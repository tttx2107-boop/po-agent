"""命令路由"""
import re
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class RouteResult:
    """路由结果"""
    success: bool
    module: str  # idea, task, assessment, stats, help, system
    action: str   # list, detail, create, trigger, etc.
    args: Dict[str, Any]  # 解析出的参数
    raw_input: str  # 原始输入


class CommandRouter:
    """
    统一入口路由
    
    支持的命令：
    - 直接发送想法 → 想法录入
    - 查看想法 / list → 列表
    - 查看详情 [ID] / detail [ID] → 详情
    - 立即评估 / eval → 深度评估
    - 统计 / stats → 统计
    - 帮助 / help → 帮助
    """
    
    # 命令模式定义
    # 格式: (模块, 动作, 参数提取函数)
    COMMANDS = {
        # 帮助
        "帮助": ("help", "show", {}),
        "help": ("help", "show", {}),
        "?": ("help", "show", {}),
        
        # 想法相关
        "查看想法": ("idea", "list", {}),
        "list": ("idea", "list", {}),
        "想法列表": ("idea", "list", {}),
        
        # 想法详情
        "查看详情": ("idea", "detail", "parse_id"),
        "detail": ("idea", "detail", "parse_id"),
        "详情": ("idea", "detail", "parse_id"),
        
        # 想法状态更新
        "确认执行": ("idea", "confirm", "parse_id"),
        "暂缓": ("idea", "defer", "parse_id"),
        "否决": ("idea", "reject", "parse_id"),
        
        # 评估相关
        "立即评估": ("assessment", "trigger", {}),
        "eval": ("assessment", "trigger", {}),
        "评估": ("assessment", "trigger", {}),
        "开始评估": ("assessment", "trigger", {}),
        
        # 任务相关
        "查看任务": ("task", "list", {}),
        "tasks": ("task", "list", {}),
        "任务列表": ("task", "list", {}),
        
        "任务详情": ("task", "detail", "parse_id"),
        "tdetail": ("task", "detail", "parse_id"),
        
        "完成任务": ("task", "done", "parse_id"),
        "done": ("task", "done", "parse_id"),
        
        "创建任务": ("task", "create", "parse_idea_id"),
        "task": ("task", "create", "parse_idea_id"),
        
        # 统计
        "统计": ("stats", "show", {}),
        "stats": ("stats", "show", {}),
        "状态": ("stats", "show", {}),
        
        # 系统
        "同步": ("system", "sync", {}),
        "sync": ("system", "sync", {}),
        "备份": ("system", "backup", {}),
        "backup": ("system", "backup", {}),
    }
    
    # 参数模式
    ID_PATTERNS = [
        r"(?:查看详情|detail|详情)\s+(\S+)",
        r"(?:确认执行|暂缓|否决)\s+(\S+)",
        r"(?:任务详情|tdetail)\s+(\S+)",
        r"(?:完成任务|done)\s+(\S+)",
    ]
    
    IDEA_ID_PATTERNS = [
        r"(?:创建任务|task)\s+(\S+)",
    ]
    
    def route(self, message: str) -> RouteResult:
        """
        路由用户消息
        
        Args:
            message: 用户输入
            
        Returns:
            RouteResult: 路由结果
        """
        message = message.strip()
        
        if not message:
            return RouteResult(
                success=False,
                module="system",
                action="empty",
                args={},
                raw_input=message
            )
        
        # 1. 精确匹配
        if message in self.COMMANDS:
            module, action, arg_parser = self.COMMANDS[message]
            args = self._parse_args(message, arg_parser)
            return RouteResult(True, module, action, args, message)
        
        # 2. 前缀匹配
        for cmd in self.COMMANDS:
            if message.startswith(cmd):
                module, action, arg_parser = self.COMMANDS[cmd]
                args = self._parse_args(message, arg_parser)
                return RouteResult(True, module, action, args, message)
        
        # 3. 作为想法录入
        return RouteResult(True, "idea", "create", {"content": message}, message)
    
    def _parse_args(self, message: str, arg_parser: str) -> Dict[str, Any]:
        """解析参数"""
        if arg_parser == "parse_id":
            return self._extract_id(message)
        elif arg_parser == "parse_idea_id":
            return self._extract_idea_id(message)
        return {}
    
    def _extract_id(self, message: str) -> Dict[str, Any]:
        """提取 ID"""
        for pattern in self.ID_PATTERNS:
            match = re.search(pattern, message)
            if match:
                return {"id": match.group(1)}
        return {}
    
    def _extract_idea_id(self, message: str) -> Dict[str, Any]:
        """提取想法 ID"""
        for pattern in self.IDEA_ID_PATTERNS:
            match = re.search(pattern, message)
            if match:
                return {"idea_id": match.group(1)}
        return {}
    
    def is_command(self, message: str) -> bool:
        """判断是否为命令"""
        message = message.strip()
        if message in self.COMMANDS:
            return True
        for cmd in self.COMMANDS:
            if message.startswith(cmd):
                return True
        return False
