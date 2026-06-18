import math
from datetime import datetime, timedelta
from typing import List, Optional
from database import get_db


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0


def _std(values: List[float], mean_val: float) -> float:
    if len(values) < 2:
        return 0
    return math.sqrt(sum((v - mean_val) ** 2 for v in values) / (len(values) - 1))


def detect_anomalies(
    hours: int = 24,
    zscore_threshold: float = 2.0,
    spike_ratio: float = 3.0,
) -> dict:
    """多维度异常检测"""
    now = datetime.now()
    since = now - timedelta(hours=hours)
    conn = get_db()

    rows = conn.execute(
        """SELECT risk_level, strftime('%Y-%m-%dT%H', created_at) as hour_bucket
           FROM content_analyses WHERE created_at >= ?""",
        (since.isoformat(),),
    ).fetchall()
    conn.close()

    if not rows:
        return {"anomalies": [], "summary": "数据不足，无法检测异常", "level": "normal"}

    buckets = {}
    for row in rows:
        h = row["hour_bucket"]
        buckets[h] = buckets.get(h, 0) + 1

    sorted_buckets = sorted(buckets.items())
    counts = [c for _, c in sorted_buckets]

    anomalies = []
    mean_val = _mean(counts)
    std_val = _std(counts, mean_val)

    for i, (hour, count) in enumerate(sorted_buckets):
        if std_val == 0:
            continue
        z = (count - mean_val) / std_val

        if abs(z) >= zscore_threshold:
            anomalies.append({
                "hour": hour,
                "count": count,
                "mean": round(mean_val, 1),
                "z_score": round(z, 2),
                "type": "spike" if z > 0 else "drop",
                "severity": "critical" if abs(z) >= 4 else "high" if abs(z) >= 3 else "medium",
                "message": (
                    f"在 {hour} 检测到异常突增：{count} 条分析请求"
                    f"（均值 {mean_val:.1f}，偏离 {z:.1f} 个标准差）"
                ) if z > 0 else (
                    f"在 {hour} 检测到异常下降：{count} 条分析请求"
                    f"（均值 {mean_val:.1f}，偏离 {z:.1f} 个标准差）"
                ),
            })

    if i > 0:
        for i in range(1, len(sorted_buckets)):
            prev_count = sorted_buckets[i - 1][1]
            curr_count = sorted_buckets[i][1]
            curr_hour = sorted_buckets[i][0]
            if prev_count > 0 and curr_count / prev_count >= spike_ratio:
                already = any(a["hour"] == curr_hour for a in anomalies)
                if not already:
                    anomalies.append({
                        "hour": curr_hour,
                        "count": curr_count,
                        "prev_count": prev_count,
                        "ratio": round(curr_count / prev_count, 1),
                        "type": "spike_sudden",
                        "severity": "high" if curr_count / prev_count >= 5 else "medium",
                        "message": (
                            f"在 {curr_hour} 检测到突发激增：{curr_count} 条"
                            f"（前一小时 {prev_count} 条，增长 {curr_count/prev_count:.1f}x）"
                        ),
                    })

    severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    overall = max(
        (severity_levels.get(a["severity"], 1) for a in anomalies),
        default=0,
    )

    level_map = {4: "critical", 3: "high", 2: "medium", 1: "low", 0: "normal"}
    level_labels = {
        "critical": "严重异常 - 需立即响应",
        "high": "高风险异常 - 尽快排查",
        "medium": "中等异常 - 建议关注",
        "low": "低风险波动 - 常规监控",
        "normal": "正常 - 无异常",
    }

    return {
        "anomalies": sorted(anomalies, key=lambda a: a["hour"], reverse=True),
        "total_hours": len(sorted_buckets),
        "mean_per_hour": round(mean_val, 1),
        "std_per_hour": round(std_val, 1),
        "overall_level": level_map.get(overall, "normal"),
        "summary": level_labels.get(level_map.get(overall, "normal"), ""),
        "detected_at": now.isoformat(),
    }


def detect_risk_spikes(hours: int = 24) -> dict:
    """检测高风险内容集中爆发"""
    now = datetime.now()
    since = now - timedelta(hours=hours)
    conn = get_db()

    rows = conn.execute(
        """SELECT risk_level, strftime('%Y-%m-%dT%H', created_at) as hour_bucket
           FROM content_analyses WHERE created_at >= ? AND risk_level IN ('high', 'critical')""",
        (since.isoformat(),),
    ).fetchall()
    conn.close()

    if not rows:
        return {"spikes": [], "summary": "近 24 小时无高风险内容"}

    buckets = {}
    for row in rows:
        h = row["hour_bucket"]
        buckets[h] = buckets.get(h, 0) + 1

    total = sum(buckets.values())
    spikes = sorted(
        [{"hour": h, "count": c} for h, c in buckets.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    return {
        "spikes": spikes,
        "total_high_risk": total,
        "summary": f"近 {hours} 小时共检测到 {total} 条高风险内容，主要集中时段：" +
                   ", ".join(f"{s['hour']} ({s['count']}条)" for s in spikes[:3]),
    }