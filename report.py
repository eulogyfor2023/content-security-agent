import json
from datetime import datetime, timedelta
from database import get_db
from agent import get_agent


def _query_data(table: str, since: str) -> list:
    conn = get_db()
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE created_at >= ? ORDER BY created_at DESC",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def generate_report(report_type: str = "daily") -> str:
    """生成日报/周报/月报"""
    now = datetime.now()
    if report_type == "daily":
        since = (now - timedelta(days=1)).isoformat()
        label = "日报"
    elif report_type == "weekly":
        since = (now - timedelta(days=7)).isoformat()
        label = "周报"
    elif report_type == "monthly":
        since = (now - timedelta(days=30)).isoformat()
        label = "月报"
    else:
        since = (now - timedelta(days=1)).isoformat()
        label = "日报"

    analyses = _query_data("content_analyses", since)
    alerts = _query_data("alerts", since)

    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    source_counts = {}
    group_counts = {}
    total_score = 0

    for a in analyses:
        risk_counts[a["risk_level"]] = risk_counts.get(a["risk_level"], 0) + 1
        source_counts[a["source"]] = source_counts.get(a["source"], 0) + 1
        group_counts[a["user_group"]] = group_counts.get(a["user_group"], 0) + 1
        total_score += a["risk_score"]

    total = len(analyses)
    avg_score = round(total_score / total, 1) if total > 0 else 0
    high_rate = round((risk_counts["high"] + risk_counts["critical"]) / total * 100, 1) if total > 0 else 0

    top_risks = sorted(
        [a for a in analyses if a["risk_level"] in ("high", "critical")],
        key=lambda x: x["risk_score"],
        reverse=True,
    )[:5]

    stats_text = f"""## 内容安全{label}

**报告时间**：{now.strftime('%Y-%m-%d %H:%M')}
**统计周期**：{since[:10]} ~ {now.strftime('%Y-%m-%d')}

### 核心指标
- 总分析量：{total} 条
- 平均风险评分：{avg_score} 分
- 高风险占比：{high_rate}%
- 告警总数：{len(alerts)} 条

### 风险分布
- 低风险：{risk_counts['low']} 条
- 中风险：{risk_counts['medium']} 条
- 高风险：{risk_counts['high']} 条
- 严重风险：{risk_counts['critical']} 条

### 内容来源分布
{chr(10).join(f'- {k}: {v} 条' for k, v in sorted(source_counts.items(), key=lambda x: x[1], reverse=True))}

### 用户群体分布
{chr(10).join(f'- {k}: {v} 条' for k, v in sorted(group_counts.items(), key=lambda x: x[1], reverse=True))}
"""

    if top_risks:
        stats_text += "\n### TOP 高风险内容\n"
        for i, r in enumerate(top_risks, 1):
            content_preview = r["content"][:80].replace("\n", " ")
            stats_text += f"{i}. [{r['risk_level']}] {content_preview}... (评分:{r['risk_score']})\n"

    try:
        agent = get_agent()
        response = agent.client.chat.completions.create(
            model=agent.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是内容安全运营专家，请根据数据生成一段简洁的运营建议（不超过150字），要点化表达。",
                },
                {
                    "role": "user",
                    "content": f"以下是{label}数据，请生成运营建议：\n\n{stats_text}",
                },
            ],
            temperature=0.5,
            max_tokens=300,
        )
        ai_advice = response.choices[0].message.content.strip()
    except Exception:
        ai_advice = "（AI 建议生成失败，请人工编写总结）"

    full_report = f"""{stats_text}

### AI 运营建议
{ai_advice}

---
> 由 Content Security Agent 自动生成
"""
    return full_report


def generate_quick_summary() -> dict:
    """快速摘要（用于仪表盘顶部）"""
    now = datetime.now()
    since = (now - timedelta(hours=24)).isoformat()
    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) as c FROM content_analyses WHERE created_at >= ?",
        (since,),
    ).fetchone()["c"]

    high_count = conn.execute(
        "SELECT COUNT(*) as c FROM content_analyses WHERE created_at >= ? AND risk_level IN ('high', 'critical')",
        (since,),
    ).fetchone()["c"]

    alert_count = conn.execute(
        "SELECT COUNT(*) as c FROM alerts WHERE created_at >= ?",
        (since,),
    ).fetchone()["c"]

    schedule_count = conn.execute(
        "SELECT COUNT(*) as c FROM schedules WHERE notified = 0",
    ).fetchone()["c"]

    conn.close()

    return {
        "today_total": total,
        "today_high_risk": high_count,
        "today_alerts": alert_count,
        "pending_schedules": schedule_count,
        "period": "24h",
    }