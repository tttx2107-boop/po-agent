"""错误处理与容错系统"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime


class ErrorType(Enum):
    """错误类型"""
    # 想法相关
    CLARITY = "clarity"                 # 想法模糊
    INCOMPLETE = "incomplete"           # 信息不完整
    DUPLICATE = "duplicate"             # 重复想法
    
    # 任务相关
    TASK_FAILURE = "task_failure"       # 任务失败
    RESOURCE = "resource"               # 资源不足
    SKILL_GAP = "skill_gap"            # 技能缺口
    DEPENDENCY = "dependency"          # 依赖问题
    
    # 执行相关
    TIMEOUT = "timeout"                 # 执行超时
    API_ERROR = "api_error"             # API错误
    STORAGE_ERROR = "storage_error"     # 存储错误
    
    # 评估相关
    ASSESSMENT_BIAS = "assessment_bias" # 评估偏差


@dataclass
class RecoveryAction:
    """恢复动作"""
    action_type: str          # replace, retry, escalate, fallback
    description: str
    alternatives: List[str] = field(default_factory=list)
    estimated_impact: str = ""  # 低/中/高


@dataclass
class ErrorContext:
    """错误上下文"""
    error_type: str
    message: str
    timestamp: str
    context_data: Dict[str, Any] = field(default_factory=dict)
    recovery_actions: List[RecoveryAction] = field(default_factory=list)
    resolved: bool = False
    resolution_notes: str = ""


@dataclass
class ClarificationQuestion:
    """澄清问题"""
    question: str
    hint: str = ""
    required: bool = True
    options: List[str] = field(default_factory=list)  # 如果是选择题


class ErrorHandler:
    """
    错误处理器
    
    处理各种错误情况，提供恢复方案
    """
    
    def __init__(self):
        self._error_history: List[ErrorContext] = []
        self._clarification_questions: List[ClarificationQuestion] = []
    
    # ==================== 想法澄清 ====================
    
    def generate_clarification_questions(self, idea_content: str, attempt: int = 0) -> ClarificationQuestion:
        """
        生成澄清问题
        
        Args:
            idea_content: 想法内容
            attempt: 追问次数
            
        Returns:
            澄清问题
        """
        # 分析想法内容，生成针对性的问题
        questions = self._analyze_idea_gaps(idea_content)
        
        if attempt < len(questions):
            return questions[attempt]
        
        return ClarificationQuestion(
            question="这个想法还需要更多信息才能准确评估",
            hint="建议补充：目标、时间、资源等方面的信息",
            required=True
        )
    
    def _analyze_idea_gaps(self, content: str) -> List[ClarificationQuestion]:
        """分析想法缺失的信息"""
        questions = []
        
        # 检查目标
        goal_indicators = ["为了", "目标", "做成", "实现", "得到"]
        if not any(ind in content for ind in goal_indicators):
            questions.append(ClarificationQuestion(
                question="这个想法的目标是什么？",
                hint="比如：做成什么样子？解决什么问题？",
                required=True
            ))
        
        # 检查时间
        time_indicators = ["时间", "多久", "deadline", "周", "天", "小时", "尽快", "慢慢"]
        if not any(ind in content for ind in time_indicators):
            questions.append(ClarificationQuestion(
                question="预计投入多少时间？",
                hint="比如：需要多少天/小时？还是长期坚持？",
                required=False
            ))
        
        # 检查资源
        resource_indicators = ["资源", "人力", "预算", "资金", "设备", "需要", "用"]
        if not any(ind in content for ind in resource_indicators):
            questions.append(ClarificationQuestion(
                question="需要什么资源支持？",
                hint="比如：工具、资金、他人协助？",
                required=False
            ))
        
        # 检查动机
        motivation_indicators = ["因为", "由于", "所以", "为了", "想"]
        if not any(ind in content for ind in motivation_indicators):
            questions.append(ClarificationQuestion(
                question="为什么想做这件事？",
                hint="动机可以帮助评估优先级",
                required=False
            ))
        
        # 如果问题太少，添加通用问题
        if len(questions) < 2:
            questions.append(ClarificationQuestion(
                question="期望达成的成果是什么？",
                hint="具体是什么样的成果或状态？",
                required=True
            ))
        
        return questions[:3]  # 最多返回3个问题
    
    def handle_clarity_request(self, idea_content: str, attempts: int) -> str:
        """
        处理想法模糊的情况
        
        Args:
            idea_content: 想法内容
            attempts: 当前追问次数
            
        Returns:
            追问消息
        """
        if attempts == 0:
            return "请补充：这个想法的目标是什么？想做成什么样子？"
        elif attempts == 1:
            return "请说明：预计投入多少时间和资源？"
        elif attempts == 2:
            return "请明确：你期望的成果是什么？做成什么样子就算成功？"
        else:
            return (
                "📝 想法信息仍不够完整，建议：\n"
                "- 可以先记录下来，后续有时间再补充\n"
                "- 或者直接说「这个想法我还没想清楚，先放着」\n"
                "- 如果有具体目标，可以简单描述一下"
            )
    
    # ==================== 任务失败处理 ====================
    
    def analyze_task_failure(self, task: Dict, error: Dict) -> ErrorContext:
        """
        分析任务失败原因
        
        Args:
            task: 任务信息
            error: 错误信息
            
        Returns:
            错误上下文，包含恢复动作
        """
        error_type = self._classify_task_error(error, task)
        
        context = ErrorContext(
            error_type=error_type,
            message=error.get("message", "任务执行失败"),
            timestamp=datetime.now().isoformat(),
            context_data={
                "task_id": task.get("id"),
                "task_title": task.get("title"),
                "error_details": error
            }
        )
        
        # 根据错误类型生成恢复动作
        if error_type == ErrorType.RESOURCE.value:
            context.recovery_actions = [
                RecoveryAction(
                    action_type="replace",
                    description="资源不足，建议调整任务范围",
                    alternatives=["缩小范围", "延长时间", "寻求帮助", "使用替代资源"],
                    estimated_impact="中"
                )
            ]
        elif error_type == ErrorType.SKILL_GAP.value:
            context.recovery_actions = [
                RecoveryAction(
                    action_type="replace",
                    description="技能缺口，需要学习或外包",
                    alternatives=["开始学习", "找人协作", "使用工具替代", "降低难度"],
                    estimated_impact="高"
                )
            ]
        elif error_type == ErrorType.DEPENDENCY.value:
            context.recovery_actions = [
                RecoveryAction(
                    action_type="replace",
                    description="依赖问题受阻",
                    alternatives=["等待依赖完成", "调整任务顺序", "绕过依赖", "催促依赖方"],
                    estimated_impact="中"
                )
            ]
        elif error_type == ErrorType.API_ERROR.value:
            context.recovery_actions = [
                RecoveryAction(
                    action_type="retry",
                    description="API 调用失败",
                    alternatives=["稍后重试", "检查 API 配置", "使用备用 API"],
                    estimated_impact="低"
                )
            ]
        else:
            context.recovery_actions = [
                RecoveryAction(
                    action_type="escalate",
                    description="需要人工介入处理",
                    alternatives=["查看详细错误", "联系支持", "手动处理"],
                    estimated_impact="高"
                )
            ]
        
        self._error_history.append(context)
        return context
    
    def _classify_task_error(self, error: Dict, task: Dict) -> str:
        """分类任务错误"""
        error_msg = str(error.get("message", "")).lower()
        
        # 资源不足
        resource_keywords = ["资源", "内存", "cpu", "带宽", "配额", "limit", "quota"]
        if any(kw in error_msg for kw in resource_keywords):
            return ErrorType.RESOURCE.value
        
        # 技能缺口
        skill_keywords = ["不会", "不懂", "不知道", "如何", "怎么", "skill", "能力"]
        if any(kw in error_msg for kw in skill_keywords):
            return ErrorType.SKILL_GAP.value
        
        # 依赖问题
        dependency_keywords = ["等待", "依赖", "blocked", "前置"]
        if any(kw in error_msg for kw in dependency_keywords):
            return ErrorType.DEPENDENCY.value
        
        # API 错误
        api_keywords = ["api", "http", "请求", "response", "timeout", "连接"]
        if any(kw in error_msg for kw in api_keywords):
            return ErrorType.API_ERROR.value
        
        # 超时
        if "timeout" in error_msg or "超时" in error_msg:
            return ErrorType.TIMEOUT.value
        
        return ErrorType.TASK_FAILURE.value
    
    def handle_task_failure(self, task: Dict, error: Dict) -> RecoveryAction:
        """
        处理任务失败
        
        返回推荐的恢复动作
        """
        context = self.analyze_task_failure(task, error)
        
        if context.recovery_actions:
            return context.recovery_actions[0]
        
        return RecoveryAction(
            action_type="escalate",
            description="未知错误，需要人工处理",
            estimated_impact="高"
        )
    
    # ==================== 评估偏差处理 ====================
    
    def report_assessment_bias(
        self, 
        idea_id: str, 
        original_assessment: Dict,
        user_feedback: Dict
    ) -> ErrorContext:
        """
        报告评估偏差
        
        用于收集用户对评估结果的反馈
        """
        # 计算偏差
        bias_score = self._calculate_bias_score(original_assessment, user_feedback)
        
        context = ErrorContext(
            error_type=ErrorType.ASSESSMENT_BIAS.value,
            message=f"评估偏差检测：偏差分数 {bias_score}",
            timestamp=datetime.now().isoformat(),
            context_data={
                "idea_id": idea_id,
                "original": original_assessment,
                "user_feedback": user_feedback,
                "bias_score": bias_score
            }
        )
        
        # 根据偏差程度生成建议
        if bias_score > 0.3:
            context.recovery_actions = [
                RecoveryAction(
                    action_type="replace",
                    description="评估与用户预期差异较大",
                    alternatives=[
                        "调整评估模型权重",
                        "考虑用户背景因素",
                        "重新评估"
                    ],
                    estimated_impact="中"
                )
            ]
        
        self._error_history.append(context)
        return context
    
    def _calculate_bias_score(
        self, 
        original: Dict, 
        feedback: Dict
    ) -> float:
        """计算偏差分数"""
        # 简单实现：比较综合评分
        original_score = original.get("overall_score", 50)
        feedback_score = feedback.get("adjusted_score", original_score)
        
        return abs(original_score - feedback_score) / 100
    
    # ==================== 超时处理 ====================
    
    def handle_timeout(
        self,
        task_id: str,
        elapsed_seconds: int,
        checkpoint_data: Optional[Dict] = None
    ) -> RecoveryAction:
        """
        处理执行超时
        
        Args:
            task_id: 任务ID
            elapsed_seconds: 已用时间
            checkpoint_data: 检查点数据
            
        Returns:
            恢复动作
        """
        # 检查是否有检查点
        has_checkpoint = checkpoint_data is not None
        
        context = ErrorContext(
            error_type=ErrorType.TIMEOUT.value,
            message=f"任务执行超时，已运行 {elapsed_seconds} 秒",
            timestamp=datetime.now().isoformat(),
            context_data={
                "task_id": task_id,
                "elapsed_seconds": elapsed_seconds,
                "has_checkpoint": has_checkpoint
            }
        )
        
        if has_checkpoint:
            context.recovery_actions = [
                RecoveryAction(
                    action_type="replace",
                    description="已保存检查点，可以从断点恢复",
                    alternatives=["继续执行", "保存进度稍后继续", "调整超时时间"],
                    estimated_impact="低"
                )
            ]
        else:
            context.recovery_actions = [
                RecoveryAction(
                    action_type="fallback",
                    description="未保存检查点，需要重新开始",
                    alternatives=["重新执行", "分段执行", "简化任务"],
                    estimated_impact="中"
                )
            ]
        
        self._error_history.append(context)
        
        return context.recovery_actions[0]
    
    # ==================== 错误历史 ====================
    
    def get_error_history(
        self, 
        error_type: Optional[str] = None,
        limit: int = 50
    ) -> List[ErrorContext]:
        """获取错误历史"""
        errors = self._error_history
        
        if error_type:
            errors = [e for e in errors if e.error_type == error_type]
        
        return sorted(errors, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def resolve_error(self, error_id: str, notes: str = ""):
        """标记错误为已解决"""
        for error in self._error_history:
            if error.timestamp == error_id or error.error_type == error_id:
                error.resolved = True
                error.resolution_notes = notes
                break
    
    # ==================== 错误报告格式化 ====================
    
    def format_error_report(self, context: ErrorContext) -> str:
        """格式化错误报告"""
        lines = [f"❌ 错误报告\n"]
        lines.append(f"━━━━━━━━━━━━━━━━━━━━\n")
        lines.append(f"类型：{context.error_type}\n")
        lines.append(f"消息：{context.message}\n")
        lines.append(f"时间：{context.timestamp}\n")
        
        if context.recovery_actions:
            lines.append(f"\n💡 建议处理方式：\n")
            for action in context.recovery_actions:
                lines.append(f"• {action.description}")
                if action.alternatives:
                    lines.append(f"  备选：{', '.join(action.alternatives)}")
        
        if context.resolved:
            lines.append(f"\n✅ 已解决：{context.resolution_notes}")
        
        return "\n".join(lines)


# 全局实例
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """获取错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler
