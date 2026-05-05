"""
知识图谱模板系统 - Layer 3
声明式 YAML 模板：Schema + Guideline 分离
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import yaml
import json


@dataclass
class EntitySchema:
    """实体Schema定义"""
    name: str
    type: str = "string"
    required: bool = True
    list: bool = False
    description: str = ""
    enum_values: List[str] = None  # 枚举值
    
    @classmethod
    def from_dict(cls, d: dict) -> 'EntitySchema':
        return cls(
            name=d.get('name', ''),
            type=d.get('type', 'string'),
            required=d.get('required', True),
            list=d.get('list', False),
            description=d.get('description', ''),
            enum_values=d.get('values')
        )


@dataclass
class RelationSchema:
    """关系Schema定义"""
    name: str
    from_entity: str
    to_entity: str
    relation_type: str = "edge"  # edge, hyperedge, temporal, spatial
    type_args: Dict[str, Any] = field(default_factory=dict)  # 超边时的实体列表、时空属性等
    description: str = ""
    
    @classmethod
    def from_dict(cls, d: dict) -> 'RelationSchema':
        return cls(
            name=d.get('name', ''),
            from_entity=d.get('from', ''),
            to_entity=d.get('to', ''),
            relation_type=d.get('type', 'edge'),
            type_args=d.get('type_args', {}),
            description=d.get('description', '')
        )


@dataclass
class KGSchema:
    """知识图谱Schema"""
    entities: List[EntitySchema] = field(default_factory=list)
    relations: List[RelationSchema] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, d: dict) -> 'KGSchema':
        entities = [EntitySchema.from_dict(e) for e in d.get('entities', [])]
        relations = [RelationSchema.from_dict(r) for r in d.get('relations', [])]
        return cls(entities=entities, relations=relations)
    
    def to_prompt(self) -> str:
        """转换为LLM提示词"""
        parts = ["## 实体类型定义"]
        for e in self.entities:
            parts.append(f"- **{e.name}** ({e.type}){'[列表]' if e.list else ''}: {e.description}")
            if e.enum_values:
                parts.append(f"  可选值: {', '.join(e.enum_values)}")
        
        parts.append("\n## 关系类型定义")
        for r in self.relations:
            if r.relation_type == 'hyperedge':
                parts.append(f"- **{r.name}** (超边): {r.description}")
            elif r.relation_type == 'temporal':
                parts.append(f"- **{r.name}** (时序边): {r.description}")
            elif r.relation_type == 'spatial':
                parts.append(f"- **{r.name}** (空间边): {r.description}")
            else:
                parts.append(f"- **{r.name}**: {r.from_entity} → {r.to_entity} | {r.description}")
        
        return '\n'.join(parts)


@dataclass  
class KGTemplate:
    """知识图谱模板"""
    name: str
    language: str = "zh"
    domain: str = "general"
    version: str = "1.0"
    description: str = ""
    schema: KGSchema = None
    guideline: str = ""
    identifiers: Dict[str, str] = field(default_factory=dict)
    display: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'KGTemplate':
        """从YAML字符串加载"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, d: dict) -> 'KGTemplate':
        schema = KGSchema.from_dict(d.get('schema', {}))
        return cls(
            name=d.get('name', 'unnamed'),
            language=d.get('language', 'zh'),
            domain=d.get('domain', 'general'),
            version=d.get('version', '1.0'),
            description=d.get('description', ''),
            schema=schema,
            guideline=d.get('guideline', ''),
            identifiers=d.get('identifiers', {}),
            display=d.get('display', {})
        )
    
    @classmethod
    def from_file(cls, filepath: str) -> 'KGTemplate':
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_yaml(f.read())
    
    def to_prompt(self) -> str:
        """生成提取提示词"""
        parts = [f"# {self.name}"]
        parts.append(f"语言: {self.language} | 领域: {self.domain}")
        parts.append(f"\n{self.description}\n")
        
        if self.schema:
            parts.append(self.schema.to_prompt())
        
        if self.guideline:
            parts.append(f"\n## 提取指南\n{self.guideline}\n")
        
        return '\n'.join(parts)
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'language': self.language,
            'domain': self.domain,
            'version': self.version,
            'description': self.description,
            'schema': {
                'entities': [
                    {'name': e.name, 'type': e.type, 'required': e.required, 'list': e.list, 'description': e.description}
                    for e in (self.schema.entities if self.schema else [])
                ],
                'relations': [
                    {'name': r.name, 'from': r.from_entity, 'to': r.to_entity, 'type': r.relation_type, 'description': r.description}
                    for r in (self.schema.relations if self.schema else [])
                ]
            },
            'guideline': self.guideline,
            'identifiers': self.identifiers,
            'display': self.display
        }


# ==================== 预置模板 ====================

# 消防应急模板
FIRE_EMERGENCY_TEMPLATE = """
name: fire_emergency_knowledge
language: zh
domain: emergency
version: 1.0
description: 消防应急事件知识图谱模板，支持超边和时空信息

schema:
  entities:
    - name: 灾害类型
      type: enum
      values: [火灾, 泄漏, 爆炸, 中毒, 其他]
      description: 事故类型分类
    - name: 危险物质
      type: string
      list: true
      description: 涉及的危化品或危险物质
    - name: 气象条件
      type: string
      description: 当时的气象状况
    - name: 地理位置
      type: string
      description: 事故发生地点
    - name: 承灾对象
      type: string
      description: 受影响的人员、设施、建筑
    - name: 应急响应级别
      type: enum
      values: [一级, 二级, 三级, 四级]
      description: 应急响应等级
    - name: 处置措施
      type: string
      list: true
      description: 采取的应急处置行动
    - name: 参与单位
      type: string
      list: true
      description: 参与应急响应的单位

  relations:
    - name: 引发
      from: 灾害类型
      to: 承灾对象
      type: temporal
      description: 灾害导致的后果
    - name: 协同处置
      from: [参与单位1, 参与单位2, 参与单位3]
      to: 灾害类型
      type: hyperedge
      type_args:
        min_entities: 2
      description: 多单位联合处置事件
    - name: 响应
      from: 应急响应级别
      to: 处置措施
      type: edge
      description: 响应级别触发的措施
    - name: 发生于
      from: 灾害类型
      to: 地理位置
      type: spatial
      description: 灾害发生的地点

guideline: |
  1. 灾害类型严格按照GB/T标准分类
  2. 应急响应级别根据事故分级标准判定
  3. 超边"协同处置"需列出所有参与单位及其角色
  4. 时空信息尽量精确，时间使用ISO8601格式
  5. 地理位置尽量提供经纬度坐标

identifiers:
  灾害类型: "{code}_{name}"
  应急响应级别: "响应_{级别}_{时间}"

display:
  icon: 🔥
  color: "#ff5722"
"""

# 学术论文模板
ACADEMIC_PAPER_TEMPLATE = """
name: academic_paper_knowledge
language: zh
domain: academic
version: 1.0
description: 学术论文知识图谱模板

schema:
  entities:
    - name: 核心概念
      type: string
      list: true
      description: 论文研究的核心学术概念
    - name: 理论基础
      type: string
      list: true
      description: 支撑论文的宏观理论框架
    - name: 研究方法
      type: string
      list: true
      description: 采用的研究方法
    - name: 变量
      type: string
      list: true
      description: 自变量、因变量、中介变量、调节变量
    - name: 研究发现
      type: string
      list: true
      description: 主要实证发现
    - name: 研究贡献
      type: string
      description: 论文的理论或实践贡献

  relations:
    - name: 基于
      from: 核心概念
      to: 理论基础
      type: edge
      description: 概念的理论来源
    - name: 影响
      from: 变量1
      to: 变量2
      type: edge
      type_args:
        direction: positive/negative
      description: 变量间的影响关系
    - name: 实证支持
      from: 研究发现
      to: 变量关系
      type: edge
      description: 发现对假设的支持程度
    - name: 提出
      from: 论文
      to: 研究贡献
      type: edge
      description: 论文提出的贡献

guideline: |
  1. 核心概念使用1-3个词定义
  2. 理论基础识别统领性的宏观理论
  3. 变量关系需标注方向（正向/负向）
  4. 研究发现与假设形成闭环对应
  5. 贡献提炼不超过2句话

display:
  icon: 📚
  color: "#1976d2"
"""


# ==================== 模板管理 ====================

class TemplateRegistry:
    """模板注册表"""
    
    def __init__(self):
        self._templates: Dict[str, KGTemplate] = {}
        self._load_presets()
    
    def _load_presets(self):
        """加载预置模板"""
        self.register('fire_emergency', KGTemplate.from_yaml(FIRE_EMERGENCY_TEMPLATE))
        self.register('academic_paper', KGTemplate.from_yaml(ACADEMIC_PAPER_TEMPLATE))
    
    def register(self, name: str, template: KGTemplate):
        """注册模板"""
        self._templates[name] = template
    
    def get(self, name: str) -> Optional[KGTemplate]:
        """获取模板"""
        return self._templates.get(name)
    
    def list_templates(self) -> List[str]:
        """列出所有模板"""
        return list(self._templates.keys())
    
    def add_from_yaml(self, name: str, yaml_str: str):
        """从YAML添加模板"""
        template = KGTemplate.from_yaml(yaml_str)
        self.register(name, template)
    
    def add_from_file(self, name: str, filepath: str):
        """从文件添加模板"""
        template = KGTemplate.from_file(filepath)
        self.register(name, template)


# 全局模板注册表
TEMPLATE_REGISTRY = TemplateRegistry()


def get_template(name: str) -> Optional[KGTemplate]:
    """获取模板"""
    return TEMPLATE_REGISTRY.get(name)


def list_templates() -> List[str]:
    """列出所有模板"""
    return TEMPLATE_REGISTRY.list_templates()
