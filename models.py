from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentSource(str, Enum):
    COMMENT = "comment"
    POST = "post"
    CHAT = "chat"
    LIVESTREAM = "livestream"
    OTHER = "other"


class ContentAnalysisRequest(BaseModel):
    content: str = Field(..., description="待分析的内容文本")
    user_group: str = Field(default="general", description="用户群体标识")
    source: ContentSource = Field(default=ContentSource.OTHER, description="内容来源")
    user_tags: Optional[List[str]] = Field(default=None, description="用户标签")


class ContentAnalysisResponse(BaseModel):
    risk_level: RiskLevel = Field(..., description="风险等级")
    risk_score: float = Field(..., ge=0, le=100, description="风险评分 0-100")
    summary: str = Field(..., description="分析摘要")
    strategy: str = Field(..., description="运营策略建议")
    tags: List[str] = Field(default_factory=list, description="风险标签")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ScheduleRequest(BaseModel):
    title: str = Field(..., description="事件标题")
    description: Optional[str] = Field(default=None, description="事件描述")
    event_time: str = Field(..., description="事件时间 ISO格式如 2026-06-20T14:00:00")
    notify_before_hours: int = Field(default=6, ge=1, le=72, description="提前多少小时提醒")


class ScheduleResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    event_time: str
    notify_before_hours: int
    notified: bool
    created_at: str


class DashboardStats(BaseModel):
    total_analyses: int
    risk_distribution: dict
    recent_alerts: List[dict]
    upcoming_schedules: List[dict]
    user_group_risks: List[dict]


class WeChatNotificationRequest(BaseModel):
    title: str
    content: str


class AnomalyDetectionRequest(BaseModel):
    hours: int = Field(default=24, ge=1, le=168, description="检测时间窗口（小时）")


class ReportRequest(BaseModel):
    report_type: str = Field(default="daily", description="日报/周报/月报: daily/weekly/monthly")


class FunnelRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365, description="分析天数")


class RuleToggleRequest(BaseModel):
    rule_id: str = Field(..., description="规则ID")
    enabled: bool = Field(..., description="启用/禁用")