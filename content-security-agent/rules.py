import json
from datetime import datetime
from typing import Optional
from database import get_db, create_alert


DEFAULT_RULES = [
    {
        "id": "rule_001",
        "name": "高风险内容自动告警",
        "condition": "risk_level IN ('high', 'critical')",
        "action": "alert",
        "params": {"level": "high", "source": "rule_engine"},
        "enabled": True,
        "description": "当内容风险等级为 high 或 critical 时自动创建告警",
    },
    {
        "id": "rule_002",
        "name": "严重违规自动标记",
        "condition": "risk_level == 'critical' OR risk_score >= 90",
        "action": "flag",
        "params": {"flag": "urgent_review"},
        "enabled": True,
        "description": "风险评分 ≥90 或严重违规时标记为紧急复核",
    },
    {
        "id": "rule_003",
        "name": "青少年高风险关注",
        "condition": "user_group == 'teenager' AND risk_level IN ('high', 'critical')",
        "action": "alert",
        "params": {"level": "critical", "source": "teenager_protection"},
        "enabled": True,
        "description": "青少年用户出现高风险内容时立即告警",
    },
    {
        "id": "rule_004",
        "name": "高频违规用户限流",
        "condition": "user_risk_count >= 5 AND period == '1h'",
        "action": "rate_limit",
        "params": {"limit": 10, "duration_minutes": 60},
        "enabled": False,
        "description": "1小时内违规超过5次的用户自动限流",
    },
    {
        "id": "rule_005",
        "name": "直播源异常检测",
        "condition": "source == 'livestream' AND risk_level IN ('high', 'critical')",
        "action": "alert",
        "params": {"level": "high", "source": "livestream_monitor"},
        "enabled": True,
        "description": "直播内容出现高风险时实时告警",
    },
    {
        "id": "rule_006",
        "name": "中风险累积预警",
        "condition": "risk_level == 'medium' AND count_today >= 10",
        "action": "alert",
        "params": {"level": "medium", "source": "cumulative_risk"},
        "enabled": True,
        "description": "当日中风险内容累计超过10条时预警",
    },
    {
        "id": "rule_007",
        "name": "新用户异常行为",
        "condition": "user_group == 'new' AND risk_level IN ('high', 'critical')",
        "action": "flag",
        "params": {"flag": "new_user_suspicious"},
        "enabled": True,
        "description": "新注册用户出现高风险行为标记为可疑",
    },
    {
        "id": "rule_008",
        "name": "VIP用户保护",
        "condition": "user_group == 'vip' AND risk_level IN ('high', 'critical')",
        "action": "alert",
        "params": {"level": "high", "source": "vip_protection"},
        "enabled": True,
        "description": "VIP用户内容异常时优先处理",
    },
]


def _init_rules_table():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            condition TEXT NOT NULL,
            action TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rule_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT,
            action TEXT,
            result TEXT,
            detail TEXT,
            executed_at TEXT NOT NULL
        );
    """)

    for rule in DEFAULT_RULES:
        conn.execute(
            """INSERT OR IGNORE INTO rules (rule_id, name, condition, action, params, enabled, description, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rule["id"],
                rule["name"],
                rule["condition"],
                rule["action"],
                json.dumps(rule["params"]),
                1 if rule["enabled"] else 0,
                rule["description"],
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
        )

    conn.commit()
    conn.close()


def get_all_rules() -> list:
    conn = get_db()
    rows = conn.execute("SELECT * FROM rules ORDER BY id").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def toggle_rule(rule_id: str, enabled: bool) -> bool:
    conn = get_db()
    cursor = conn.execute(
        "UPDATE rules SET enabled = ?, updated_at = ? WHERE rule_id = ?",
        (1 if enabled else 0, datetime.now().isoformat(), rule_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def evaluate_rules(
    risk_level: str,
    risk_score: float,
    user_group: str,
    source: str,
    content: str = "",
) -> list:
    """根据分析结果评估所有规则，返回触发的规则列表"""
    conn = get_db()
    rules = conn.execute(
        "SELECT * FROM rules WHERE enabled = 1"
    ).fetchall()
    conn.close()

    triggered = []
    for rule in rules:
        rule_dict = dict(rule)
        condition = rule_dict["condition"]

        try:
            ctx = {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "user_group": user_group,
                "source": source,
                "risk_level IN ('high', 'critical')": risk_level in ("high", "critical"),
                "risk_level == 'critical'": risk_level == "critical",
                "risk_score >= 90": risk_score >= 90,
                "user_group == 'teenager'": user_group == "teenager",
                "user_group == 'new'": user_group == "new",
                "user_group == 'vip'": user_group == "vip",
                "source == 'livestream'": source == "livestream",
                "risk_level == 'medium'": risk_level == "medium",
            }

            result = False
            if " OR " in condition:
                parts = condition.split(" OR ")
                result = any(_eval_simple(p.strip(), ctx) for p in parts)
            elif " AND " in condition:
                parts = condition.split(" AND ")
                result = all(_eval_simple(p.strip(), ctx) for p in parts)
            else:
                result = _eval_simple(condition.strip(), ctx)

            if result:
                params = json.loads(rule_dict["params"])
                action = rule_dict["action"]
                detail = f"触发规则: {rule_dict['name']}"

                if action == "alert":
                    create_alert(
                        title=f"规则引擎 - {rule_dict['name']}",
                        content=f"内容: {content[:100]}...\n风险等级: {risk_level}\n评分: {risk_score}\n用户群体: {user_group}",
                        level=params.get("level", "info"),
                        source=params.get("source", "rule_engine"),
                    )

                elif action == "flag":
                    detail = f"标记内容: {params.get('flag', 'unknown')} - {rule_dict['name']}"

                elif action == "rate_limit":
                    detail = f"限流: {params.get('limit', 0)}次/{params.get('duration_minutes', 60)}分钟"

                _log_rule_execution(
                    rule_dict["rule_id"],
                    action,
                    "triggered",
                    detail,
                )

                triggered.append({
                    "rule_id": rule_dict["rule_id"],
                    "name": rule_dict["name"],
                    "action": action,
                    "params": params,
                    "detail": detail,
                })

        except Exception as e:
            _log_rule_execution(
                rule_dict["rule_id"],
                rule_dict["action"],
                "error",
                str(e),
            )

    return triggered


def _eval_simple(cond: str, ctx: dict) -> bool:
    cond = cond.strip()
    if cond in ctx:
        return bool(ctx[cond])
    if " == " in cond:
        left, right = cond.split(" == ", 1)
        left = left.strip().strip("'\"")
        right = right.strip().strip("'\"")
        return str(ctx.get(left, "")) == right
    if " >= " in cond:
        left, right = cond.split(" >= ", 1)
        left = left.strip()
        return ctx.get(left, 0) >= int(right.strip())
    if " IN " in cond:
        return False
    return False


def _log_rule_execution(rule_id: str, action: str, result: str, detail: str):
    conn = get_db()
    conn.execute(
        """INSERT INTO rule_logs (rule_id, action, result, detail, executed_at)
           VALUES (?, ?, ?, ?, ?)""",
        (rule_id, action, result, detail, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_rule_logs(limit: int = 50) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM rule_logs ORDER BY executed_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_rule_stats() -> dict:
    conn = get_db()
    total_rules = conn.execute("SELECT COUNT(*) as c FROM rules").fetchone()["c"]
    enabled_rules = conn.execute("SELECT COUNT(*) as c FROM rules WHERE enabled = 1").fetchone()["c"]
    total_executions = conn.execute("SELECT COUNT(*) as c FROM rule_logs").fetchone()["c"]
    today_executions = conn.execute(
        "SELECT COUNT(*) as c FROM rule_logs WHERE executed_at >= ?",
        (datetime.now().strftime("%Y-%m-%d"),),
    ).fetchone()["c"]
    conn.close()

    return {
        "total_rules": total_rules,
        "enabled_rules": enabled_rules,
        "total_executions": total_executions,
        "today_executions": today_executions,
    }