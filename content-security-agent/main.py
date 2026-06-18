import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from models import (
    ContentAnalysisRequest,
    ContentAnalysisResponse,
    ScheduleRequest,
    ScheduleResponse,
    DashboardStats,
    WeChatNotificationRequest,
    AnomalyDetectionRequest,
    ReportRequest,
    FunnelRequest,
    RuleToggleRequest,
)
from database import (
    init_db,
    get_db,
    save_analysis,
    save_schedule,
    get_dashboard_stats,
    get_all_schedules,
    delete_schedule,
    get_all_alerts,
    create_alert,
)
from agent import get_agent
from scheduler import start_scheduler, stop_scheduler
from notifier import get_notifier
from anomaly import detect_anomalies, detect_risk_spikes
from report import generate_report, generate_quick_summary
from funnel import analyze_funnel, analyze_retention, analyze_user_behavior
from rules import get_all_rules, toggle_rule, evaluate_rules, get_rule_logs, get_rule_stats, _init_rules_table

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _auto_seed_if_empty()
    start_scheduler()
    print("=" * 50)
    print("  Content Security Agent 已启动")
    print("  API 文档: http://localhost:8100/docs")
    print("  仪表盘:   http://localhost:8100/dashboard")
    print("=" * 50)
    yield
    stop_scheduler()


def _auto_seed_if_empty():
    """如果数据库为空，自动填充演示数据，确保仪表盘有内容"""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM content_analyses").fetchone()["c"]
    conn.close()
    if count == 0:
        print("[AutoSeed] 数据库为空，自动填充演示数据...")
        try:
            from seed import generate_demo_analyses, generate_demo_schedules, generate_demo_alerts, generate_demo_rule_logs, generate_demo_funnel
            c1 = generate_demo_analyses()
            c2 = generate_demo_schedules()
            c3 = generate_demo_alerts()
            c4 = generate_demo_rule_logs()
            generate_demo_funnel()
            print(f"[AutoSeed] 完成！已插入 {c1 + c2 + c3 + c4} 条演示数据")
        except Exception as e:
            print(f"[AutoSeed] 失败: {e}")


app = FastAPI(
    title="Content Security Agent",
    description="内容安全监控与分析智能体 - 多智能体业务编排系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.get("/")
def root():
    return {"message": "Content Security Agent API", "docs": "/docs", "dashboard": "/dashboard"}


@app.get("/dashboard")
def dashboard():
    return FileResponse(os.path.join(BASE_DIR, "static", "dashboard.html"))


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze_content(req: ContentAnalysisRequest):
    try:
        agent = get_agent()
        result = agent.analyze(
            content=req.content,
            user_group=req.user_group,
            source=req.source.value,
            user_tags=req.user_tags,
        )

        save_analysis(
            content=req.content,
            user_group=req.user_group,
            source=req.source.value,
            risk_level=result["risk_level"],
            risk_score=result["risk_score"],
            summary=result["summary"],
            strategy=result["strategy"],
            tags=result["tags"],
        )

        if result["risk_level"] in ("high", "critical"):
            create_alert(
                title=f"高风险内容告警 - {result['risk_level']}",
                content=f"用户群体: {req.user_group}\n风险评分: {result['risk_score']}\n摘要: {result['summary']}",
                level=result["risk_level"],
                source="content_analysis",
            )

        triggered_rules = evaluate_rules(
            risk_level=result["risk_level"],
            risk_score=result["risk_score"],
            user_group=req.user_group,
            source=req.source.value,
            content=req.content,
        )

        return {
            "risk_level": result["risk_level"],
            "risk_score": result["risk_score"],
            "summary": result["summary"],
            "strategy": result["strategy"],
            "tags": result["tags"],
            "triggered_rules": triggered_rules,
        }
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "api_key" in error_msg.lower() or "apikey" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail="API Key 无效或未配置，请在 .env 文件中填写正确的 OPENAI_API_KEY",
            )
        raise HTTPException(status_code=500, detail=f"分析失败: {error_msg}")


@app.post("/api/schedule", response_model=ScheduleResponse)
def create_schedule(req: ScheduleRequest):
    schedule_id = save_schedule(
        title=req.title,
        description=req.description,
        event_time=req.event_time,
        notify_before_hours=req.notify_before_hours,
    )
    return ScheduleResponse(
        id=schedule_id,
        title=req.title,
        description=req.description,
        event_time=req.event_time,
        notify_before_hours=req.notify_before_hours,
        notified=False,
        created_at="",
    )


@app.get("/api/schedules")
def list_schedules():
    return get_all_schedules()


@app.delete("/api/schedule/{schedule_id}")
def remove_schedule(schedule_id: int):
    if not delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="日程不存在")
    return {"message": "已删除"}


@app.get("/api/dashboard", response_model=DashboardStats)
def dashboard_stats():
    stats = get_dashboard_stats()
    return DashboardStats(**stats)


@app.get("/api/alerts")
def list_alerts():
    return get_all_alerts()


@app.post("/api/notify")
def send_notification(req: WeChatNotificationRequest):
    notifier = get_notifier()
    success = notifier.send(req.title, req.content)
    return {"success": success, "title": req.title}


@app.post("/api/anomaly/detect")
def run_anomaly_detection(req: AnomalyDetectionRequest):
    result = detect_anomalies(hours=req.hours)
    risk_spikes = detect_risk_spikes(hours=req.hours)
    return {"stats": result, "risk_spikes": risk_spikes}


@app.post("/api/report/generate")
def generate_full_report(req: ReportRequest):
    report = generate_report(report_type=req.report_type)
    summary = generate_quick_summary()
    return {"report_text": report, "quick_stats": summary}


@app.get("/api/report/summary")
def get_quick_summary():
    return generate_quick_summary()


@app.post("/api/report/send")
def send_report_to_wechat(req: ReportRequest):
    """生成报表并通过微信发送"""
    report = generate_report(report_type=req.report_type)
    notifier = get_notifier()

    type_labels = {"daily": "日报", "weekly": "周报", "monthly": "月报"}
    label = type_labels.get(req.report_type, "报表")

    title = f"📊 Content Security Agent - {label}"
    success = notifier.send(title, report)

    if success:
        return {"success": True, "message": f"{label}已生成并发送到微信"}
    else:
        return {"success": False, "message": "报表已生成，但微信发送失败（请检查 ServerChan SendKey 配置）", "report_text": report}


@app.post("/api/funnel")
def get_funnel(req: FunnelRequest):
    return analyze_funnel(days=req.days)


@app.get("/api/retention")
def get_retention(days: int = 30):
    return analyze_retention(days=days)


@app.get("/api/user-behavior")
def get_user_behavior(days: int = 30):
    return analyze_user_behavior(days=days)


@app.get("/api/rules")
def list_all_rules():
    return {"rules": get_all_rules(), "stats": get_rule_stats()}


@app.post("/api/rules/toggle")
def toggle_rule_enabled(req: RuleToggleRequest):
    success = toggle_rule(req.rule_id, req.enabled)
    if not success:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"success": True, "rule_id": req.rule_id, "enabled": req.enabled}


@app.get("/api/rules/logs")
def list_rule_logs(limit: int = 50):
    return {"logs": get_rule_logs(limit=limit)}


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Content Security Agent",
        "version": "1.1.0",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8100"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)