"""TaskBreaker - 想法拆解为核心任务"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from datetime import datetime
import re


@dataclass
class SubTask:
    """子任务"""
    title: str
    description: str
    task_type: str = "development"  # development, research, design, testing, deployment
    estimated_hours: float = 1.0
    priority: int = 0  # 0=高, 1=中, 2=低
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务 ID
    hints: List[str] = field(default_factory=list)  # 实现提示
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BreakdownResult:
    """拆解结果"""
    original_idea: str
    subtasks: List[SubTask] = field(default_factory=list)
    estimated_total_hours: float = 0.0
    risk_notes: str = ""
    success_criteria: str = ""
    breakdown_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_idea": self.original_idea,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "estimated_total_hours": self.estimated_total_hours,
            "risk_notes": self.risk_notes,
            "success_criteria": self.success_criteria,
            "breakdown_time": self.breakdown_time
        }
    
    def format(self) -> str:
        """格式化输出"""
        lines = [f"## 📋 任务拆解\n"]
        lines.append(f"**原始想法**: {self.original_idea}\n")
        lines.append(f"**预估总工时**: {self.estimated_total_hours} 小时\n")
        
        if self.risk_notes:
            lines.append(f"\n⚠️ **风险提示**: {self.risk_notes}\n")
        
        lines.append(f"\n### ✅ 验收标准\n{self.success_criteria}\n")
        
        lines.append(f"\n### 📌 任务清单\n")
        for i, task in enumerate(self.subtasks, 1):
            emoji = "🔴" if task.priority == 0 else "🟡" if task.priority == 1 else "🟢"
            lines.append(f"\n{emoji} **{i}. {task.title}**")
            lines.append(f"   - 类型: `{task.task_type}`")
            lines.append(f"   - 预估: {task.estimated_hours}h")
            lines.append(f"   - 说明: {task.description}")
            
            if task.hints:
                lines.append(f"   - 💡 提示: {', '.join(task.hints)}")
            
            if task.dependencies:
                lines.append(f"   - 🔗 依赖: {', '.join(task.dependencies)}")
        
        return "\n".join(lines)


class TaskBreaker:
    """
    想法拆解为核心任务
    
    将用户的想法拆解为可执行的具体任务列表
    """
    
    # 关键词映射到任务类型
    TASK_TYPE_KEYWORDS = {
        "development": ["开发", "实现", "编程", "写代码", "构建", "创建", "APP", "网站", "软件", "系统"],
        "research": ["研究", "调研", "分析", "学习", "探索", "调查"],
        "design": ["设计", "规划", "方案", "架构", "UI", "UX"],
        "testing": ["测试", "验证", "调试", "优化"],
        "deployment": ["部署", "上线", "发布", "发布"]
    }
    
    # 复杂度关键词
    COMPLEXITY_KEYWORDS = {
        "high": ["复杂", "困难", "大型", "全新", "首创"],
        "medium": ["中等", "改进", "优化", "升级"],
        "low": ["简单", "快速", "轻量", "MVP", "最小"]
    }
    
    def breakdown(self, idea: str) -> BreakdownResult:
        """
        拆解想法为任务列表
        
        Args:
            idea: 用户的想法描述
            
        Returns:
            拆解结果
        """
        # 检测任务类型
        task_types = self._detect_task_types(idea)
        
        # 检测复杂度
        complexity = self._detect_complexity(idea)
        
        # 生成任务列表
        subtasks = self._generate_subtasks(idea, task_types, complexity)
        
        # 计算总工时
        total_hours = sum(t.estimated_hours for t in subtasks)
        
        # 生成风险提示
        risk_notes = self._generate_risk_notes(idea, complexity)
        
        # 生成验收标准
        success_criteria = self._generate_success_criteria(idea)
        
        return BreakdownResult(
            original_idea=idea,
            subtasks=subtasks,
            estimated_total_hours=total_hours,
            risk_notes=risk_notes,
            success_criteria=success_criteria
        )
    
    def _detect_task_types(self, idea: str) -> List[str]:
        """检测任务类型"""
        detected = set()
        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            if any(kw in idea for kw in keywords):
                detected.add(task_type)
        
        # 默认至少包含 development
        if not detected:
            detected.add("development")
        
        return list(detected)
    
    def _detect_complexity(self, idea: str) -> str:
        """检测复杂度"""
        for level, keywords in self.COMPLEXITY_KEYWORDS.items():
            if any(kw in idea for kw in keywords):
                return level
        return "medium"  # 默认中等
    
    def _generate_subtasks(self, idea: str, task_types: List[str], complexity: str) -> List[SubTask]:
        """生成子任务"""
        tasks = []
        
        # 基础任务流程
        base_tasks = [
            SubTask(
                title="需求分析与确认",
                description="明确核心需求，确定 MVP 范围，输出需求文档",
                task_type="research",
                estimated_hours=2.0,
                priority=0,
                hints=["使用 5W1H 方法分析", "确定核心价值主张"]
            ),
            SubTask(
                title="技术方案设计",
                description="选择技术栈，设计系统架构，确定数据模型",
                task_type="design",
                estimated_hours=3.0,
                priority=0,
                hints=["画出系统架构图", "选择最小可行的技术栈"]
            ),
        ]
        tasks.extend(base_tasks)
        
        # 根据复杂度调整开发任务
        if complexity == "high":
            dev_hours = 20.0
            tasks.append(SubTask(
                title="核心功能开发",
                description="实现核心业务逻辑，完成功能模块",
                task_type="development",
                estimated_hours=dev_hours,
                priority=1,
                hints=["采用敏捷开发模式", "每两天一个里程碑"]
            ))
            test_hours = 5.0
        elif complexity == "medium":
            dev_hours = 10.0
            test_hours = 3.0
        else:
            dev_hours = 5.0
            test_hours = 1.0
        
        tasks.append(SubTask(
            title="功能开发与迭代",
            description="编码实现，迭代优化",
            task_type="development",
            estimated_hours=dev_hours,
            priority=1,
            hints=["先实现核心功能", "保持 MVP 原则"]
        ))
        
        # 测试任务
        tasks.append(SubTask(
            title="测试与修复",
            description="编写测试用例，修复 bug，优化性能",
            task_type="testing",
            estimated_hours=test_hours,
            priority=2,
            dependencies=["功能开发与迭代"],
            hints=["先自动化测试", "覆盖核心路径"]
        ))
        
        # 部署任务
        tasks.append(SubTask(
            title="部署与上线",
            description="配置环境，部署上线，建立监控",
            task_type="deployment",
            estimated_hours=2.0,
            priority=2,
            dependencies=["测试与修复"],
            hints=["使用 CI/CD 自动化", "建立日志和告警"]
        ))
        
        # 如果是研究类任务，添加调研任务
        if "research" in task_types:
            tasks.insert(1, SubTask(
                title="市场与竞品调研",
                description="调研市场现状，竞品分析，找差异化点",
                task_type="research",
                estimated_hours=4.0,
                priority=0,
                hints=["访谈潜在用户", "分析 Top 3 竞品"]
            ))
        
        # 如果涉及设计类任务
        if "design" in task_types:
            tasks.insert(2, SubTask(
                title="原型设计与评审",
                description="绘制原型，收集反馈，迭代设计",
                task_type="design",
                estimated_hours=3.0,
                priority=1,
                dependencies=["需求分析与确认"],
                hints=["先低保真原型", "快速验证核心流程"]
            ))
        
        return tasks
    
    def _generate_risk_notes(self, idea: str, complexity: str) -> str:
        """生成风险提示"""
        risks = []
        
        if complexity == "high":
            risks.append("项目复杂度较高，建议分阶段交付")
        
        # 检查资源风险
        if "资源" not in idea and "资金" not in idea:
            risks.append("未明确资源需求，需提前规划")
        
        # 检查时间风险
        if "时间" not in idea and "周期" not in idea:
            risks.append("建议设定明确的里程碑和时间节点")
        
        # 检查技术风险
        tech_risks = ["AI", "机器学习", "区块链", "大数据"]
        if any(t in idea for t in tech_risks):
            risks.append("涉及新技术，需要预留学习时间")
        
        return "；".join(risks) if risks else "整体风险可控，建议按计划推进"
    
    def _generate_success_criteria(self, idea: str) -> str:
        """生成验收标准"""
        criteria = []
        
        # 基础验收标准
        criteria.append("1. 核心功能可正常运行，无致命 bug")
        criteria.append("2. 用户可完成主要操作流程")
        criteria.append("3. 性能满足基本要求（响应时间 < 2秒）")
        criteria.append("4. 代码质量达标（有基本测试覆盖）")
        
        return "\n".join(criteria)
