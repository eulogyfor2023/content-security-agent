#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
填充演示数据到数据库
模拟一个运营了一段时间的内容安全监控系统
"""

import sys
import os
import json
from datetime import datetime, timedelta
from random import random, choice

sys.path.insert(0, os.path.dirname(__file__))

from database import (
    get_db,
    init_db,
    save_analysis,
    save_schedule,
    create_alert,
)


def random_date(days_ago: int = 30) -> str:
    """生成一个随机日期，在过去 N 天内"""
    delta = timedelta(days=random() * days_ago, hours=random() * 24, minutes=random() * 60)
    dt = datetime.now() - delta
    return dt.isoformat()


def generate_demo_analyses():
    """生成模拟的内容分析数据"""
    demos = [
        {
            "content": "感谢楼主分享，这个产品确实不错！我已经买了一个，用着感觉很好。",
            "user_group": "general",
            "source": "comment",
            "risk_level": "low",
            "risk_score": 5,
            "summary": "正常用户评论，内容合规",
            "strategy": "正常展示，无需干预",
            "tags": ["正常内容"],
        },
        {
            "content": "大家别信这个，这个就是骗人的，我被骗了一万多，大家小心点！",
            "user_group": "general",
            "source": "comment",
            "risk_level": "medium",
            "risk_score": 45,
            "summary": "用户投诉被骗，但未明确提及诈骗手法",
            "strategy": "标记内容，人工复核是否存在虚假信息",
            "tags": ["投诉", "诈骗嫌疑"],
        },
        {
            "content": "加我微信xxx88888，我这里有内部渠道，比官网便宜一半，保证正品货到付款。",
            "user_group": "new",
            "source": "comment",
            "risk_level": "high",
            "risk_score": 85,
            "summary": "公开引流到微信进行私下交易，涉嫌诈骗",
            "strategy": "立即删除内容，禁言该用户，通知用户群体提高警惕",
            "tags": ["引流", "私下交易", "诈骗"],
        },
        {
            "content": "这里有最新的在线网站链接，点进去就能看：http://xxx.xxx.com",
            "user_group": "high_risk",
            "source": "post",
            "risk_level": "critical",
            "risk_score": 100,
            "summary": "公开发布违规网址，严重违反内容安全规定",
            "strategy": "删除帖子，封禁账号，上报平台管理员",
            "tags": ["色情", "严重违规"],
        },
        {
            "content": "这个游戏外挂真好用，我分享给大家，点这个链接下载：xxx.com",
            "user_group": "teenager",
            "source": "chat",
            "risk_level": "high",
            "risk_score": 80,
            "summary": "分享游戏外挂，破坏游戏公平",
            "strategy": "删除链接，对青少年用户加强内容审核力度",
            "tags": ["外挂", "违规内容"],
        },
        {
            "content": "今天我生日，祝我生日快乐！分享一下今天的美食照片。",
            "user_group": "vip",
            "source": "post",
            "risk_level": "low",
            "risk_score": 0,
            "summary": "用户正常生活分享",
            "strategy": "正常展示，无干预",
            "tags": ["正常内容"],
        },
        {
            "content": "这个主播说话真难听，长得也丑，赶紧滚出平台吧！",
            "user_group": "general",
            "source": "comment",
            "risk_level": "medium",
            "risk_score": 40,
            "summary": "人身攻击辱骂主播",
            "strategy": "隐藏评论，警告用户文明发言",
            "tags": ["辱骂", "人身攻击"],
        },
        {
            "content": "点击领取你的新人红包188元，只需要点击链接注册：http://scam.example.com",
            "user_group": "new",
            "source": "livestream",
            "risk_level": "high",
            "risk_score": 88,
            "summary": "直播中发布虚假红包诈骗链接",
            "strategy": "踢出发言人，禁言直播间，记录IP",
            "tags": ["诈骗", "红包链接", "虚假福利"],
        },
        {
            "content": "有没有人需要发票？各种发票都可以开，点数优惠，微信联系。",
            "user_group": "general",
            "source": "chat",
            "risk_level": "high",
            "risk_score": 78,
            "summary": "公开招揽代开发票业务，涉嫌违法",
            "strategy": "立即删除，封禁账号，上报",
            "tags": ["发票", "违法", "广告"],
        },
        {
            "content": "最近天气真热，大家注意防暑降温，多喝点水。",
            "user_group": "general",
            "source": "post",
            "risk_level": "low",
            "risk_score": 0,
            "summary": "正常话题讨论，无风险",
            "strategy": "正常展示",
            "tags": ["正常内容"],
        },
        {
            "content": "我告诉你，这个公司就是垃圾，老板是骗子，欠我工资不还，大家别来！",
            "user_group": "general",
            "source": "comment",
            "risk_level": "medium",
            "risk_score": 55,
            "summary": "用户负面投诉，情绪激动但未涉及违法",
            "strategy": "保留内容，转给运营部门跟进处理",
            "tags": ["投诉", "负面"],
        },
        {
            "content": "【包过】驾照科目一科目四保过，联系我包你拿证，不用考试。",
            "user_group": "general",
            "source": "comment",
            "risk_level": "high",
            "risk_score": 82,
            "summary": "违法服务广告，保过驾照涉嫌作弊",
            "strategy": "删除内容，拉黑用户",
            "tags": ["违法广告", "作弊"],
        },
        {
            "content": "需要刷赞刷粉刷评论，直播间热度提升，联系我价格优惠。",
            "user_group": "general",
            "source": "chat",
            "risk_level": "high",
            "risk_score": 75,
            "summary": "黑产刷量服务广告",
            "strategy": "删除，禁言，标记账号",
            "tags": ["黑产", "刷量", "广告"],
        },
        {
            "content": "一起玩呀，我这边有福利群，每天都有红包抢，扫码进群。",
            "user_group": "new",
            "source": "post",
            "risk_level": "medium",
            "risk_score": 50,
            "summary": "引流用户进外部福利群，潜在风险",
            "strategy": "对新用户发布的引流内容加强审核，建议人工复核",
            "tags": ["引流", "可疑"],
        },
        {
            "content": "这款产品实测效果确实不错，给大家测评一下，链接放在评论区。",
            "user_group": "vip",
            "source": "post",
            "risk_level": "low",
            "risk_score": 10,
            "summary": "VIP用户正常测评分享，内容合规",
            "strategy": "正常展示，增加曝光",
            "tags": ["测评", "正常内容"],
        },
        {
            "content": "这个视频里有恐怖画面，小孩子别看了，容易吓着。",
            "user_group": "general",
            "source": "comment",
            "risk_level": "low",
            "risk_score": 5,
            "summary": "用户善意提醒，内容合规",
            "strategy": "正常展示，无需处理",
            "tags": ["提醒", "正常内容"],
        },
        {
            "content": "转发这个锦鲤，一个月内必有好事发生！",
            "user_group": "general",
            "source": "post",
            "risk_level": "low",
            "risk_score": 0,
            "summary": "网络流行文化，无违规内容",
            "strategy": "正常展示",
            "tags": ["正常内容"],
        },
        {
            "content": " fuck you！你妈死了，你全家都死了！",
            "user_group": "high_risk",
            "source": "chat",
            "risk_level": "high",
            "risk_score": 90,
            "summary": "重度脏话辱骂，人身攻击",
            "strategy": "禁言7天，记录违规次数，累计多次直接封禁",
            "tags": ["脏话", "辱骂", "人身攻击"],
        },
        {
            "content": "我这边可以帮你洗白征信，修复信用记录，只要你交钱，不成功不收费。",
            "user_group": "general",
            "source": "post",
            "risk_level": "critical",
            "risk_score": 95,
            "summary": "宣传征信修复骗局，典型诈骗",
            "strategy": "立即删除，封禁账号，上报公安机关",
            "tags": ["诈骗", "征信修复", "严重违法"],
        },
        {
            "content": "今天下班早，去健身房练了两个小时，舒服！",
            "user_group": "general",
            "source": "post",
            "risk_level": "low",
            "risk_score": 0,
            "summary": "用户日常生活分享，无风险",
            "strategy": "正常展示",
            "tags": ["正常内容"],
        },
    ]

    conn = get_db()

    for demo in demos:
        created = random_date(days_ago=30)
        conn.execute(
            """INSERT INTO content_analyses
               (content, user_group, source, risk_level, risk_score, summary, strategy, tags, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                demo["content"],
                demo["user_group"],
                demo["source"],
                demo["risk_level"],
                demo["risk_score"],
                demo["summary"],
                demo["strategy"],
                json.dumps(demo["tags"]),
                created,
            ),
        )

    conn.commit()
    conn.close()

    print(f"✓ 已插入 {len(demos)} 条内容分析数据")
    return len(demos)


def generate_demo_schedules():
    """生成模拟的日程提醒数据"""
    from datetime import datetime, timedelta

    now = datetime.now()

    schedules = [
        {
            "title": "周度内容安全审核会",
            "description": "汇总本周高风险内容，讨论运营策略调整",
            "event_time": (now + timedelta(days=1, hours=2)).isoformat(),
            "notify_before_hours": 6,
        },
        {
            "title": "月度用户风险画像分析",
            "description": "统计不同用户群体的风险分布，输出月报",
            "event_time": (now + timedelta(days=3)).isoformat(),
            "notify_before_hours": 12,
        },
        {
            "title": "青少年内容专项整治会议",
            "description": "针对青少年用户群体的内容安全策略讨论",
            "event_time": (now + timedelta(days=5, hours=1)).isoformat(),
            "notify_before_hours": 6,
        },
        {
            "title": "第三方内容安全服务商对接",
            "description": "与第三方AI审核平台对接测试",
            "event_time": (now + timedelta(days=2)).isoformat(),
            "notify_before_hours": 24,
        },
        {
            "title": "五一假期内容安全预案评审",
            "description": "制定假期期间流量高峰的审核预案",
            "event_time": (now + timedelta(days=10)).isoformat(),
            "notify_before_hours": 24,
        },
    ]

    for item in schedules:
        save_schedule(
            title=item["title"],
            description=item["description"],
            event_time=item["event_time"],
            notify_before_hours=item["notify_before_hours"],
        )

    print(f"✓ 已插入 {len(schedules)} 条日程提醒")
    return len(schedules)


def generate_demo_alerts():
    """生成模拟的告警数据"""
    alerts = [
        {
            "title": "高风险内容集中爆发",
            "content": "过去一小时内检测到12条高风险违规内容，主要来自新用户群体",
            "level": "high",
            "source": "system",
        },
        {
            "title": "青少年用户色情内容告警",
            "content": "连续检测到3条涉黄内容发布者账号标签为青少年",
            "level": "critical",
            "source": "system",
        },
        {
            "title": "新用户引流异常告警",
            "content": "新注册用户引流行为增加30%，疑似团伙操作",
            "level": "medium",
            "source": "system",
        },
        {
            "title": "直播弹幕违规率上升",
            "content": "今日直播弹幕违规率较昨日上升15%，建议关注",
            "level": "medium",
            "source": "stats",
        },
        {
            "title": "系统巡检完成",
            "content": "每日安全巡检完成，所有服务正常运行",
            "level": "info",
            "source": "system",
        },
    ]

    for item in alerts:
        create_alert(
            title=item["title"],
            content=item["content"],
            level=item["level"],
            source=item["source"],
        )

    print(f"✓ 已插入 {len(alerts)} 条告警记录")
    return len(alerts)


def generate_demo_rule_logs():
    """生成模拟的规则执行日志"""
    conn = get_db()
    rules = conn.execute("SELECT rule_id, action FROM rules WHERE enabled = 1").fetchall()
    conn.close()

    rule_logs = []
    for i in range(30):
        rule = choice(rules)
        actions = ["triggered", "triggered", "triggered", "skipped"]
        log = {
            "rule_id": rule["rule_id"],
            "action": rule["action"],
            "result": choice(actions),
            "detail": f"模拟执行日志 #{i+1}",
            "executed_at": random_date(days_ago=14),
        }
        rule_logs.append(log)

    conn = get_db()
    for log in rule_logs:
        conn.execute(
            """INSERT INTO rule_logs (rule_id, action, result, detail, executed_at)
               VALUES (?, ?, ?, ?, ?)""",
            (log["rule_id"], log["action"], log["result"], log["detail"], log["executed_at"]),
        )
    conn.commit()
    conn.close()

    print(f"✓ 已插入 {len(rule_logs)} 条规则执行日志")
    return len(rule_logs)


def generate_demo_funnel():
    """生成模拟的漏斗数据"""
    conn = get_db()
    stages = ["registered", "activated", "retained", "active"]
    for days_ago in range(7, 0, -1):
        today = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        base = 200 + int(random() * 300)
        for idx, stage in enumerate(stages):
            rate = [1.0, 0.65, 0.40, 0.25][idx]
            conn.execute(
                """INSERT INTO daily_funnels (stage, user_count, conversion_rate, snapshot_date, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (stage, int(base * rate), rate * 100, today, datetime.now().isoformat()),
            )
    conn.commit()
    conn.close()
    print(f"✓ 已插入 7 天漏斗快照数据")


def main():
    print("=" * 50)
    print("  Content Security Agent - 填充演示数据")
    print("=" * 50)

    init_db()
    print("✓ 数据库初始化完成")

    count1 = generate_demo_analyses()
    count2 = generate_demo_schedules()
    count3 = generate_demo_alerts()
    count4 = generate_demo_rule_logs()
    generate_demo_funnel()

    print("-" * 50)
    print(f"总计: {count1 + count2 + count3 + count4} 条演示数据已插入")
    print("完成！现在启动服务打开仪表盘就能看到数据了。")
    print("=" * 50)


if __name__ == "__main__":
    main()