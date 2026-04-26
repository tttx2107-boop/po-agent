"""TaskBreaker - 想法拆解为核心任务"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

# 尝试导入用户画像（如果存在）
try:
    from ..models.user_profile import UserProfile, UserRole, OutputGoal
    HAS_USER_PROFILE = True
except ImportError:
    HAS_USER_PROFILE = False
    UserProfile = None
    UserRole = None
    OutputGoal = None


# 任务类型枚举
class TaskType:
    RESEARCH = "research"
    DESIGN = "design"
    DEVELOPMENT = "development"
    HARDWARE = "hardware"  # 新增：硬件相关
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    PAPER = "paper"  # 新增：论文产出
    PATENT = "patent"  # 新增：专利产出
    DELIVERABLE = "deliverable"  # 新增：交付物


@dataclass
class SubTask:
    """子任务"""
    title: str
    description: str
    task_type: str = "development"  # development, research, design, hardware, testing, deployment, paper, patent
    estimated_hours: float = 1.0
    priority: int = 0  # 0=高, 1=中, 2=低
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务 ID
    hints: List[str] = field(default_factory=list)  # 实现提示
    output_form: str = ""  # 交付形式：document/prototype/code/hardware/protocol
    deliverable: str = ""  # 明确产出物
    
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
    
    def breakdown(self, idea: str, user_profile: Optional[Dict[str, Any]] = None) -> BreakdownResult:
        """
        拆解想法为任务列表
        
        Args:
            idea: 用户的想法描述
            user_profile: 用户画像字典（可选），包含:
                - role: 用户角色
                - output_goals: 产出目标列表
                - hardware_experience: 是否有硬件经验
                - tech_level: 技术等级
                - field: 专业领域
                
        Returns:
            拆解结果
        """
        # 检测任务类型
        task_types = self._detect_task_types(idea)
        
        # 检测复杂度
        complexity = self._detect_complexity(idea)
        
        # 检测是否涉及硬件
        is_hardware = self._detect_hardware(idea)
        
        # 生成任务列表
        subtasks = self._generate_subtasks(
            idea, task_types, complexity, 
            user_profile=user_profile,
            is_hardware=is_hardware
        )
        
        # 计算总工时
        total_hours = sum(t.estimated_hours for t in subtasks)
        
        # 生成风险提示
        risk_notes = self._generate_risk_notes(idea, complexity, is_hardware, user_profile)
        
        # 生成验收标准
        success_criteria = self._generate_success_criteria(idea, user_profile)
        
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
    
    def _detect_hardware(self, idea: str) -> bool:
        """检测是否涉及硬件"""
        hardware_keywords = [
            "硬件", "芯片", "传感器", "边缘计算", "IoT", "嵌入式",
            "单片机", "Arduino", "树莓派", "STM32", "ESP32",
            "部署", "安装", "传感器", "设备", "终端", "信标",
            "电路", "PCB", "天线", "蓝牙", "WiFi模块", "LoRa",
            "应急指示", "标识牌", "指示灯"
        ]
        return any(kw in idea for kw in hardware_keywords)
    
    def _detect_output_goals(self, idea: str) -> List[str]:
        """检测产出目标"""
        goals = []
        goal_keywords = {
            "paper": ["论文", "发表", "期刊", "会议", "学术"],
            "patent": ["专利", "申请专利", "知识产权"],
            "product": ["产品", "落地", "商业化", "MVP"],
            "project": ["项目申报", "课题", "基金", "政府项目"],
        }
        for goal, keywords in goal_keywords.items():
            if any(kw in idea for kw in keywords):
                goals.append(goal)
        return goals
    
    def _generate_subtasks(self, idea: str, task_types: List[str], complexity: str, 
                          user_profile: Optional[Dict[str, Any]] = None,
                          is_hardware: bool = False) -> List[SubTask]:
        """生成子任务"""
        tasks = []
        
        # 提取用户画像信息
        profile = user_profile or {}
        output_goals = profile.get("output_goals", [])
        has_hardware_exp = profile.get("hardware_experience", False)
        user_role = profile.get("role", "")
        
        # ========== 第一阶段：调研与需求 ==========
        tasks.append(SubTask(
            title="文献调研与技术预研",
            description="调研相关技术/领域现状，阅读参考文献，确定技术路线",
            task_type="research",
            estimated_hours=3.0,
            priority=0,
            hints=["调研室内定位技术(UWB/蓝牙/WiFi)", "调研边缘计算方案", "调研应急疏散系统现状"],
            deliverable="技术调研报告"
        ))
        
        tasks.append(SubTask(
            title="需求分析与系统定义",
            description="明确核心需求，确定MVP范围，定义系统边界",
            task_type="design",
            estimated_hours=2.0,
            priority=0,
            hints=["使用5W1H方法分析", "确定核心价值主张", "明确角色定义"],
            deliverable="需求文档 + 系统定义"
        ))
        
        # ========== 第二阶段：方案设计 ==========
        if is_hardware:
            # 硬件相关方案设计
            tasks.append(SubTask(
                title="硬件方案设计",
                description="选择硬件架构，设计电路/传感器方案，确定通信协议",
                task_type="hardware",
                estimated_hours=4.0,
                priority=0,
                hints=["选择合适的边缘计算芯片", "设计传感器布局", "确定通信协议(BLE/WiFi/LoRa)"],
                deliverable="硬件设计方案"
            ))
            
            # 硬件选型清单
            tasks.append(SubTask(
                title="硬件选型与采购",
                description="根据方案选择具体硬件型号，编制采购清单",
                task_type="hardware",
                estimated_hours=2.0,
                priority=1,
                dependencies=["硬件方案设计"],
                hints=["优先选择成熟方案", "考虑供货周期", "预留备件"],
                deliverable="采购清单"
            ))
        
        tasks.append(SubTask(
            title="软件架构与接口设计",
            description="设计系统架构，定义数据模型，规划接口协议",
            task_type="design",
            estimated_hours=3.0,
            priority=0,
            dependencies=["需求分析与系统定义"],
            hints=["画出系统架构图", "设计API接口", "定义数据交互格式"],
            deliverable="架构设计文档"
        ))
        
        # ========== 第三阶段：原型/POC ==========
        if is_hardware and not has_hardware_exp:
            # 无硬件经验，增加原型验证阶段
            tasks.append(SubTask(
                title="硬件原型验证",
                description="制作最小可行硬件原型，验证核心技术点",
                task_type="hardware",
                estimated_hours=5.0,
                priority=1,
                dependencies=["硬件选型与采购"],
                hints=["先做最小系统", "逐个验证模块", "做好记录"],
                deliverable="硬件原型 + 验证报告"
            ))
        
        tasks.append(SubTask(
            title="核心功能开发",
            description="实现核心业务逻辑，完成功能模块",
            task_type="development",
            estimated_hours=8.0,
            priority=1,
            dependencies=["软件架构与接口设计"],
            hints=["采用MVP原则", "先实现核心定位功能", "保持代码可扩展"],
            deliverable="可运行的核心系统"
        ))
        
        # ========== 第四阶段：集成与测试 ==========
        if is_hardware:
            tasks.append(SubTask(
                title="软硬件集成",
                description="将软件与硬件集成，调试通信，验证功能",
                task_type="hardware",
                estimated_hours=4.0,
                priority=2,
                dependencies=["核心功能开发", "硬件选型与采购"],
                hints=["先分别调试", "再联合调试", "记录问题"],
                deliverable="集成测试报告"
            ))
        
        tasks.append(SubTask(
            title="系统测试与优化",
            description="功能测试、性能测试、优化改进",
            task_type="testing",
            estimated_hours=3.0,
            priority=2,
            dependencies=["核心功能开发"] if not is_hardware else ["软硬件集成"],
            hints=["编写测试用例", "性能测试(定位精度/响应时间)", "优化瓶颈"],
            deliverable="测试报告"
        ))
        
        # ========== 第五阶段：产出物 ==========
        # 根据产出目标添加对应任务
        if "paper" in output_goals or user_role in ["researcher", "student"]:
            tasks.append(SubTask(
                title="论文撰写",
                description="整理研究成果，撰写论文",
                task_type="paper",
                estimated_hours=5.0,
                priority=2,
                dependencies=["系统测试与优化"],
                hints=["确定目标期刊", "按模板撰写", "提前预留给审稿修改"],
                deliverable="论文初稿"
            ))
        
        if "patent" in output_goals:
            tasks.append(SubTask(
                title="专利申请",
                description="撰写专利申请书，进行专利查新",
                task_type="patent",
                estimated_hours=3.0,
                priority=2,
                dependencies=["系统测试与优化"],
                hints=["先查新", "确定创新点", "按专利模板撰写"],
                deliverable="专利申请书"
            ))
        
        if "project" in output_goals:
            tasks.append(SubTask(
                title="项目申报材料",
                description="编写项目申报书、预算、计划",
                task_type="deliverable",
                estimated_hours=4.0,
                priority=2,
                dependencies=["需求分析与系统定义", "软件架构与接口设计"],
                hints=["按申报指南撰写", "合理编制预算", "突出创新点"],
                deliverable="项目申报书"
            ))
        
        # ========== 第六阶段：部署 ==========
        tasks.append(SubTask(
            title="演示环境部署",
            description="在目标环境部署系统，建立监控",
            task_type="deployment",
            estimated_hours=2.0,
            priority=2,
            dependencies=["系统测试与优化"] if not is_hardware else ["软硬件集成"],
            hints=["使用容器化部署", "建立日志和告警", "准备演示脚本"],
            deliverable="可演示的系统"
        ))
        
        # ========== 第七阶段：交付 ==========
        tasks.append(SubTask(
            title="项目总结与文档",
            description="整理项目文档，编写使用手册",
            task_type="deliverable",
            estimated_hours=2.0,
            priority=3,
            dependencies=["演示环境部署"],
            hints=["整理设计文档", "编写用户手册", "整理代码注释"],
            deliverable="完整项目文档"
        ))
        
        return tasks
    
    def _generate_risk_notes(self, idea: str, complexity: str, is_hardware: bool,
                            user_profile: Optional[Dict[str, Any]] = None) -> str:
        """生成风险提示"""
        risks = []
        profile = user_profile or {}
        
        if complexity == "high":
            risks.append("项目复杂度较高，建议分阶段交付")
        
        # 硬件相关风险
        if is_hardware:
            has_hw_exp = profile.get("hardware_experience", False)
            if not has_hw_exp:
                risks.append("涉及硬件开发，但无相关经验，建议预留额外学习时间")
            risks.append("硬件开发周期长，涉及采购/制造，需提前规划时间节点")
            risks.append("硬件测试需要实际设备，建议尽早搭建测试环境")
        
        # 产出目标风险
        output_goals = profile.get("output_goals", [])
        if "paper" in output_goals:
            risks.append("论文发表周期较长（投稿→审稿→修改→见刊），需预留6-12个月")
        if "patent" in output_goals:
            risks.append("专利申请需要查新和撰写，建议提前3个月准备")
        
        # 检查资源风险
        if "资源" not in idea and "资金" not in idea and not is_hardware:
            risks.append("未明确资源需求，需提前规划")
        
        # 检查时间风险
        if "时间" not in idea and "周期" not in idea:
            risks.append("建议设定明确的里程碑和时间节点")
        
        # 检查技术风险
        tech_risks = ["AI", "机器学习", "机器学习", "深度学习", "区块链", "大数据"]
        if any(t in idea for t in tech_risks):
            risks.append("涉及新技术，需要预留学习时间")
        
        return "；".join(risks) if risks else "整体风险可控，建议按计划推进"
    
    def _generate_success_criteria(self, idea: str, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """生成验收标准"""
        criteria = []
        profile = user_profile or {}
        output_goals = profile.get("output_goals", [])
        
        # 基础验收标准
        criteria.append("1. 核心功能可正常运行，无致命 bug")
        criteria.append("2. 用户可完成主要操作流程")
        criteria.append("3. 性能满足基本要求")
        
        # 根据产出目标添加标准
        if "paper" in output_goals:
            criteria.append("4. 论文框架完整，包含引言/方法/实验/结论")
            criteria.append("5. 实验数据支撑充分，有对比实验")
        
        if "patent" in output_goals:
            criteria.append("4. 专利创新点明确，技术方案可实施")
            criteria.append("5. 权利要求书覆盖核心技术特征")
        
        if "project" in output_goals:
            criteria.append("4. 申报书符合指南要求，预算合理")
            criteria.append("5. 创新点和预期成果明确")
        
        # 默认代码质量标准
        if not output_goals or "paper" not in output_goals:
            criteria.append("4. 代码质量达标（有基本测试覆盖）")
        
        return "\n".join(criteria)
