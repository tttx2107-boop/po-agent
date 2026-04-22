"""风险预警路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.services.risk_warning import (
    RiskWarningService, RiskItem, RiskReport, RiskLevel
)

router = APIRouter(prefix="/risk", tags=["风险预警"])
service = RiskWarningService()


# ==================== 请求/响应模型 ====================

class RiskAnalyzeRequest(BaseModel):
    """风险分析请求"""
    idea_id: str = Field(..., description="想法ID")
    idea_content: str = Field(..., description="想法内容")


class RiskResponse(BaseModel):
    """风险项响应"""
    id: str
    idea_id: str
    risk_type: str
    title: str
    description: str
    level: str
    probability: float
    impact: float
    score: float
    mitigation: str
    status: str
    created_at: str

    @classmethod
    def from_risk_item(cls, item: RiskItem) -> "RiskResponse":
        return cls(
            id=item.id,
            idea_id=item.idea_id,
            risk_type=item.risk_type,
            title=item.title,
            description=item.description,
            level=item.level,
            probability=item.probability,
            impact=item.impact,
            score=item.calculate_score(),
            mitigation=item.mitigation,
            status=item.status,
            created_at=item.created_at
        )


class RiskReportResponse(BaseModel):
    """风险报告响应"""
    idea_id: str
    idea_content: str
    risks: List[RiskResponse]
    total_risks: int
    high_risks: int
    avg_score: float
    recommendations: List[str]

    @classmethod
    def from_report(cls, report: RiskReport) -> "RiskReportResponse":
        return cls(
            idea_id=report.idea_id,
            idea_content=report.idea_content,
            risks=[RiskResponse.from_risk_item(r) for r in report.risks],
            total_risks=report.total_risks,
            high_risks=report.high_risks,
            avg_score=report.avg_score,
            recommendations=report.recommendations
        )


class RiskResolveRequest(BaseModel):
    """解决风险请求"""
    risk_id: str
    notes: Optional[str] = ""


# ==================== API 端点 ====================

@router.post("/analyze", response_model=RiskReportResponse)
async def analyze_risk(request: RiskAnalyzeRequest) -> RiskReportResponse:
    """
    分析想法的风险
    
    - 分析想法内容的潜在风险
    - 生成风险报告和建议
    """
    try:
        report = service.analyze_idea(
            idea_content=request.idea_content,
            idea_id=request.idea_id
        )
        return RiskReportResponse.from_report(report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/idea/{idea_id}", response_model=List[RiskResponse])
async def get_idea_risks(idea_id: str) -> List[RiskResponse]:
    """获取想法的所有风险"""
    risks = service.get_idea_risks(idea_id)
    return [RiskResponse.from_risk_item(r) for r in risks]


@router.get("/active", response_model=List[RiskResponse])
async def get_active_risks() -> List[RiskResponse]:
    """获取所有活跃风险"""
    risks = service.get_active_risks()
    return [RiskResponse.from_risk_item(r) for r in risks]


@router.get("/high", response_model=List[RiskResponse])
async def get_high_risks() -> List[RiskResponse]:
    """获取高风险项"""
    risks = service.get_high_risks()
    return [RiskResponse.from_risk_item(r) for r in risks]


@router.post("/resolve", response_model=dict)
async def resolve_risk(request: RiskResolveRequest) -> dict:
    """解决风险"""
    service.resolve_risk(request.risk_id, request.notes or "")
    return {"status": "success", "risk_id": request.risk_id}


@router.get("/report/{idea_id}", response_model=str)
async def get_risk_report_markdown(idea_id: str) -> str:
    """获取风险报告（Markdown格式）"""
    risks = service.get_idea_risks(idea_id)
    if not risks:
        return "## 暂无风险数据\n"
    
    # 构建简单报告
    from src.services.risk_warning import RiskReport
    report = RiskReport(
        idea_id=idea_id,
        idea_content="",
        risks=risks
    )
    report.total_risks = len(risks)
    report.high_risks = len([r for r in risks if r.level in 
                           [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]])
    report.avg_score = sum(r.calculate_score() for r in risks) / len(risks)
    
    return report.format_report()
