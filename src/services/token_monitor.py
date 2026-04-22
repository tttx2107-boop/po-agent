"""
Token 监控服务 - API 使用量追踪与成本分析
支持多模型、成本计算、预算告警
"""
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import json
import os


class TokenMetricType(Enum):
    """指标类型"""
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"
    TOTAL_TOKENS = "total_tokens"
    COST = "cost"
    LATENCY = "latency"
    REQUESTS = "requests"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TokenUsage:
    """Token 使用记录"""
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    latency_ms: float
    request_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelPricing:
    """模型定价"""
    model: str
    input_price_per_1k: float  # 输入每1K token价格
    output_price_per_1k: float  # 输出每1K token价格
    currency: str = "USD"
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """计算成本"""
        return (
            input_tokens * self.input_price_per_1k / 1000 +
            output_tokens * self.output_price_per_1k / 1000
        )


@dataclass
class BudgetAlert:
    """预算告警配置"""
    daily_limit: float = 0.0        # 每日限额
    monthly_limit: float = 0.0      # 每月限额
    warn_threshold: float = 0.8      # 警告阈值 (80%)
    critical_threshold: float = 0.95  # 严重阈值 (95%)


@dataclass
class TokenAlert:
    """Token 告警"""
    level: str
    title: str
    message: str
    current_usage: float
    limit: float
    percentage: float
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class TokenMonitor:
    """
    Token 监控服务
    
    功能：
    1. 使用追踪 - 记录每个 API 调用的 token 使用量
    2. 成本计算 - 基于模型定价计算实际成本
    3. 预算告警 - 设置预算限额并发送告警
    4. 统计分析 - 每日/每周/每月使用报告
    5. 模型对比 - 多模型成本效率对比
    """
    
    # 默认模型定价 (OpenAI 2024 定价)
    DEFAULT_PRICING: Dict[str, ModelPricing] = {
        "gpt-4o": ModelPricing("gpt-4o", 0.005, 0.015),
        "gpt-4o-mini": ModelPricing("gpt-4o-mini", 0.00015, 0.0006),
        "gpt-4-turbo": ModelPricing("gpt-4-turbo", 0.01, 0.03),
        "gpt-3.5-turbo": ModelPricing("gpt-3.5-turbo", 0.0005, 0.0015),
        "claude-3-opus": ModelPricing("claude-3-opus", 0.015, 0.075),
        "claude-3-sonnet": ModelPricing("claude-3-sonnet", 0.003, 0.015),
        "claude-3-haiku": ModelPricing("claude-3-haiku", 0.00025, 0.00125),
        "gemini-pro": ModelPricing("gemini-pro", 0.000125, 0.0005),
    }
    
    def __init__(self, db_path: str = "data/token_usage.json"):
        """
        初始化 Token 监控器
        
        Args:
            db_path: 使用记录存储路径
        """
        self.db_path = db_path
        self._ensure_dir()
        
        self.pricing: Dict[str, ModelPricing] = dict(self.DEFAULT_PRICING)
        self.usage_records: List[TokenUsage] = []
        self.budget_alert = BudgetAlert()
        self.alert_callbacks: List[Callable[[TokenAlert], None]] = []
        
        self._load_usage()
    
    def _ensure_dir(self):
        """确保目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def _load_usage(self):
        """加载使用记录"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.usage_records = [
                        TokenUsage(**record) for record in data.get("records", [])
                    ]
            except Exception:
                self.usage_records = []
    
    def _save_usage(self):
        """保存使用记录"""
        try:
            data = {
                "records": [vars(r) for r in self.usage_records[-10000:]]  # 只保留最近10000条
            }
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def set_model_pricing(self, model: str, input_price: float, output_price: float):
        """设置模型定价"""
        self.pricing[model] = ModelPricing(model, input_price, output_price)
    
    def set_budget_alert(self, daily: float = 0, monthly: float = 0):
        """设置预算告警"""
        self.budget_alert = BudgetAlert(
            daily_limit=daily,
            monthly_limit=monthly
        )
    
    def on_alert(self, callback: Callable[[TokenAlert], None]):
        """注册告警回调"""
        self.alert_callbacks.append(callback)
    
    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        request_id: str = "",
        metadata: Dict[str, Any] = None
    ) -> TokenUsage:
        """
        记录 API 使用
        
        Args:
            model: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            latency_ms: 延迟（毫秒）
            request_id: 请求ID
            metadata: 额外元数据
            
        Returns:
            使用记录
        """
        pricing = self.pricing.get(model, ModelPricing(model, 0, 0))
        cost = pricing.calculate_cost(input_tokens, output_tokens)
        
        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            request_id=request_id,
            metadata=metadata or {}
        )
        
        self.usage_records.append(usage)
        self._save_usage()
        
        # 检查是否需要告警
        self._check_alerts(usage)
        
        return usage
    
    def _check_alerts(self, usage: TokenUsage):
        """检查是否触发告警"""
        if self.budget_alert.daily_limit <= 0 and self.budget_alert.monthly_limit <= 0:
            return
        
        today = datetime.now().date()
        month_start = today.replace(day=1)
        
        # 计算今日/本月使用量
        daily_cost = sum(
            u.cost for u in self.usage_records
            if datetime.fromisoformat(u.timestamp).date() == today
        )
        monthly_cost = sum(
            u.cost for u in self.usage_records
            if datetime.fromisoformat(u.timestamp).date() >= month_start
        )
        
        alerts = []
        
        # 每日限额检查
        if self.budget_alert.daily_limit > 0:
            daily_pct = daily_cost / self.budget_alert.daily_limit
            if daily_pct >= self.budget_alert.critical_threshold:
                alerts.append(TokenAlert(
                    level=AlertLevel.CRITICAL.value,
                    title="每日预算严重超限",
                    message=f"今日成本 ${daily_cost:.4f} 已超过限额 ${self.budget_alert.daily_limit:.4f} 的 {daily_pct:.0%}",
                    current_usage=daily_cost,
                    limit=self.budget_alert.daily_limit,
                    percentage=daily_pct
                ))
            elif daily_pct >= self.budget_alert.warn_threshold:
                alerts.append(TokenAlert(
                    level=AlertLevel.WARNING.value,
                    title="每日预算接近上限",
                    message=f"今日成本 ${daily_cost:.4f} 已达限额的 {daily_pct:.0%}",
                    current_usage=daily_cost,
                    limit=self.budget_alert.daily_limit,
                    percentage=daily_pct
                ))
        
        # 每月限额检查
        if self.budget_alert.monthly_limit > 0:
            monthly_pct = monthly_cost / self.budget_alert.monthly_limit
            if monthly_pct >= self.budget_alert.critical_threshold:
                alerts.append(TokenAlert(
                    level=AlertLevel.CRITICAL.value,
                    title="每月预算严重超限",
                    message=f"本月成本 ${monthly_cost:.4f} 已超过限额 ${self.budget_alert.monthly_limit:.4f} 的 {monthly_pct:.0%}",
                    current_usage=monthly_cost,
                    limit=self.budget_alert.monthly_limit,
                    percentage=monthly_pct
                ))
            elif monthly_pct >= self.budget_alert.warn_threshold:
                alerts.append(TokenAlert(
                    level=AlertLevel.WARNING.value,
                    title="每月预算接近上限",
                    message=f"本月成本 ${monthly_cost:.4f} 已达限额的 {monthly_pct:.0%}",
                    current_usage=monthly_cost,
                    limit=self.budget_alert.monthly_limit,
                    percentage=monthly_pct
                ))
        
        # 触发回调
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception:
                    pass
    
    def get_stats(
        self,
        since: datetime = None,
        model: str = None
    ) -> Dict[str, Any]:
        """
        获取使用统计
        
        Args:
            since: 统计起始时间
            model: 按模型筛选
            
        Returns:
            统计信息
        """
        since = since or (datetime.now() - timedelta(days=30))
        
        records = [
            r for r in self.usage_records
            if datetime.fromisoformat(r.timestamp) >= since
            and (not model or r.model == model)
        ]
        
        if not records:
            return self._empty_stats()
        
        stats = {
            "period": {
                "start": since.isoformat(),
                "end": datetime.now().isoformat()
            },
            "total_requests": len(records),
            "total_tokens": sum(r.total_tokens for r in records),
            "input_tokens": sum(r.input_tokens for r in records),
            "output_tokens": sum(r.output_tokens for r in records),
            "total_cost": sum(r.cost for r in records),
            "avg_latency_ms": sum(r.latency_ms for r in records) / len(records),
            "avg_tokens_per_request": sum(r.total_tokens for r in records) / len(records),
        }
        
        # 按模型分组
        stats["by_model"] = self._stats_by_model(records)
        
        # 每日趋势
        stats["daily"] = self._daily_trend(records)
        
        return stats
    
    def _empty_stats(self) -> Dict[str, Any]:
        """空统计数据"""
        return {
            "period": {"start": "", "end": ""},
            "total_requests": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost": 0.0,
            "avg_latency_ms": 0.0,
            "avg_tokens_per_request": 0.0,
            "by_model": {},
            "daily": []
        }
    
    def _stats_by_model(self, records: List[TokenUsage]) -> Dict[str, Any]:
        """按模型统计"""
        by_model = defaultdict(lambda: {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "latencies": []
        })
        
        for r in records:
            m = by_model[r.model]
            m["requests"] += 1
            m["input_tokens"] += r.input_tokens
            m["output_tokens"] += r.output_tokens
            m["total_tokens"] += r.total_tokens
            m["cost"] += r.cost
            m["latencies"].append(r.latency_ms)
        
        result = {}
        for model, data in by_model.items():
            result[model] = {
                "requests": data["requests"],
                "input_tokens": data["input_tokens"],
                "output_tokens": data["output_tokens"],
                "total_tokens": data["total_tokens"],
                "cost": data["cost"],
                "avg_latency_ms": sum(data["latencies"]) / len(data["latencies"]) if data["latencies"] else 0,
                "avg_cost_per_request": data["cost"] / data["requests"] if data["requests"] > 0 else 0
            }
        
        return result
    
    def _daily_trend(self, records: List[TokenUsage]) -> List[Dict[str, Any]]:
        """每日趋势"""
        daily_data = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0.0})
        
        for r in records:
            day = datetime.fromisoformat(r.timestamp).date().isoformat()
            daily_data[day]["requests"] += 1
            daily_data[day]["tokens"] += r.total_tokens
            daily_data[day]["cost"] += r.cost
        
        return [
            {
                "date": day,
                "requests": data["requests"],
                "tokens": data["tokens"],
                "cost": data["cost"]
            }
            for day, data in sorted(daily_data.items())
        ]
    
    def get_today_cost(self) -> float:
        """获取今日成本"""
        today = datetime.now().date()
        return sum(
            u.cost for u in self.usage_records
            if datetime.fromisoformat(u.timestamp).date() == today
        )
    
    def get_month_cost(self) -> float:
        """获取本月成本"""
        month_start = datetime.now().date().replace(day=1)
        return sum(
            u.cost for u in self.usage_records
            if datetime.fromisoformat(u.timestamp).date() >= month_start
        )
    
    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int = 0
    ) -> float:
        """
        估算成本
        
        Args:
            model: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 预估输出 token 数
            
        Returns:
            预估成本
        """
        pricing = self.pricing.get(model, ModelPricing(model, 0, 0))
        return pricing.calculate_cost(input_tokens, output_tokens)
    
    def get_efficiency_ranking(self, min_requests: int = 5) -> List[Dict[str, Any]]:
        """
        获取模型效率排名
        
        按每美元产生的 token 数排名
        
        Args:
            min_requests: 最少请求数要求
            
        Returns:
            排名列表
        """
        stats = self.get_stats()
        rankings = []
        
        for model, data in stats.get("by_model", {}).items():
            if data["requests"] >= min_requests and data["cost"] > 0:
                efficiency = data["total_tokens"] / data["cost"]
                rankings.append({
                    "model": model,
                    "requests": data["requests"],
                    "total_tokens": data["total_tokens"],
                    "cost": data["cost"],
                    "tokens_per_dollar": efficiency,
                    "avg_latency_ms": data["avg_latency_ms"]
                })
        
        rankings.sort(key=lambda x: x["tokens_per_dollar"], reverse=True)
        return rankings
    
    def export_report(self, format: str = "json") -> str:
        """
        导出报告
        
        Args:
            format: 报告格式 (json/markdown/text)
            
        Returns:
            报告内容
        """
        stats = self.get_stats()
        
        if format == "json":
            return json.dumps(stats, ensure_ascii=False, indent=2)
        
        elif format == "markdown":
            lines = ["# Token 使用报告", ""]
            
            lines.append(f"## 统计周期")
            lines.append(f"- 开始: {stats['period']['start']}")
            lines.append(f"- 结束: {stats['period']['end']}")
            lines.append("")
            
            lines.append(f"## 总体统计")
            lines.append(f"- 总请求数: {stats['total_requests']}")
            lines.append(f"- 总 Token 数: {stats['total_tokens']:,}")
            lines.append(f"  - 输入: {stats['input_tokens']:,}")
            lines.append(f"  - 输出: {stats['output_tokens']:,}")
            lines.append(f"- 总成本: ${stats['total_cost']:.4f}")
            lines.append(f"- 平均延迟: {stats['avg_latency_ms']:.1f}ms")
            lines.append("")
            
            lines.append(f"## 按模型统计")
            lines.append("")
            lines.append("| 模型 | 请求数 | Token | 成本 | 效率 |")
            lines.append("|------|--------|-------|------|------|")
            
            for model, data in stats.get("by_model", {}).items():
                efficiency = data["total_tokens"] / data["cost"] if data["cost"] > 0 else 0
                lines.append(f"| {model} | {data['requests']} | {data['total_tokens']:,} | ${data['cost']:.4f} | {efficiency:,.0f} |")
            
            return "\n".join(lines)
        
        else:
            lines = ["Token Usage Report", "=" * 40]
            lines.append(f"Total Requests: {stats['total_requests']}")
            lines.append(f"Total Tokens: {stats['total_tokens']:,}")
            lines.append(f"Total Cost: ${stats['total_cost']:.4f}")
            return "\n".join(lines)


class TokenCounter:
    """
    Token 计数器工具类
    
    估算不同模型的 token 数量
    """
    
    # 简单估算：中文约 1.5 token/字符，英文约 0.25 token/字符
    @staticmethod
    def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
        """
        估算 token 数量
        
        Args:
            text: 输入文本
            model: 目标模型
            
        Returns:
            估算的 token 数
        """
        import re
        
        # 统计中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        # 统计其他字符
        other_chars = len(text) - chinese_chars
        
        # 简单估算
        # 中文约 1.5 token/字符，英文/数字约 4字符/token
        estimated = chinese_chars * 1.5 + other_chars / 4
        
        # 模型调整系数
        if "claude" in model.lower():
            estimated *= 1.1  # Claude 需要更多 token
        elif "gemini" in model.lower():
            estimated *= 0.9  # Gemini 效率更高
        
        return max(1, int(estimated))
    
    @staticmethod
    def estimate_messages_tokens(messages: List[Dict[str, str]], model: str = "gpt-4o") -> int:
        """
        估算对话消息的总 token 数
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            model: 目标模型
            
        Returns:
            估算的 token 数
        """
        total = 0
        
        for msg in messages:
            content = msg.get("content", "")
            # 每条消息有额外的 overhead
            total += TokenCounter.estimate_tokens(content, model)
            total += 4  # 每条消息的基础开销
        
        # 如果有 system message
        if any(m.get("role") == "system" for m in messages):
            total += 3  # system 消息额外开销
        
        return total
