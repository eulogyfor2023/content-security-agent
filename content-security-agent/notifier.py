import os
import httpx
from dotenv import load_dotenv

load_dotenv()


class WeChatNotifier:
    """微信通知服务，支持 Server酱 和 企业微信机器人"""

    def __init__(self):
        self.serverchan_key = os.getenv("SERVERCHAN_SENDKEY", "")
        self.wecom_webhook = os.getenv("WECOM_WEBHOOK_URL", "")

    def send(self, title: str, content: str) -> bool:
        success = False

        if self.serverchan_key and self.serverchan_key != "your_serverchan_sendkey_here":
            success = self._send_via_serverchan(title, content)

        if not success and self.wecom_webhook:
            success = self._send_via_wecom(title, content)

        if not success:
            print(f"[WeChatNotifier] 所有通知渠道均不可用，消息未发送：{title}")

        return success

    def _send_via_serverchan(self, title: str, content: str) -> bool:
        try:
            url = f"https://sctapi.ftqq.com/{self.serverchan_key}.send"
            resp = httpx.post(url, json={"title": title, "desp": content}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    print(f"[ServerChan] 通知发送成功：{title}")
                    return True
            print(f"[ServerChan] 通知发送失败：{resp.text}")
            return False
        except Exception as e:
            print(f"[ServerChan] 发送异常：{e}")
            return False

    def _send_via_wecom(self, title: str, content: str) -> bool:
        try:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {title}\n\n{content}"
                },
            }
            resp = httpx.post(self.wecom_webhook, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("errcode") == 0:
                    print(f"[WeCom] 通知发送成功：{title}")
                    return True
            print(f"[WeCom] 通知发送失败：{resp.text}")
            return False
        except Exception as e:
            print(f"[WeCom] 发送异常：{e}")
            return False


_notifier_instance = None


def get_notifier() -> WeChatNotifier:
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = WeChatNotifier()
    return _notifier_instance