from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from database import get_pending_schedules, mark_notified, log_notification
from notifier import get_notifier

scheduler = BackgroundScheduler()
notifier = get_notifier()


def check_and_notify():
    """检查所有待提醒的日程，对即将到期的发送微信通知"""
    print(f"[Scheduler] 检查日程提醒... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pending = get_pending_schedules()

    for schedule in pending:
        schedule_id = schedule["id"]
        title = schedule["title"]
        description = schedule.get("description", "")
        event_time = schedule["event_time"]
        hours_before = schedule["notify_before_hours"]

        notify_title = f"⏰ 日程提醒：{title}"
        notify_content = f"""## 事件：{title}

**时间**：{event_time}
**提前提醒**：{hours_before} 小时

{description if description else ''}

---
> 来自 Content Security Agent 自动提醒"""

        success = notifier.send(notify_title, notify_content)
        if success:
            mark_notified(schedule_id)
            log_notification(schedule_id, notify_title, notify_content, success=True)
            print(f"[Scheduler] 已发送提醒并标记完成：{title}")
        else:
            log_notification(schedule_id, notify_title, notify_content, success=False)
            print(f"[Scheduler] 提醒发送失败：{title}")


def start_scheduler():
    scheduler.add_job(check_and_notify, "interval", minutes=5, id="schedule_check")
    scheduler.start()
    print("[Scheduler] 日程提醒调度器已启动（每5分钟检查一次）")


def stop_scheduler():
    scheduler.shutdown()
    print("[Scheduler] 日程提醒调度器已停止")