import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """你是一个专业的内容安全监控与分析智能体。你的职责是：

1. 分析用户提供的内容，评估其安全风险等级
2. 识别内容中的潜在风险标签（如：涉黄、涉政、暴恐、辱骂、诈骗、广告、隐私泄露等）
3. 针对不同用户群体，给出差异化的运营策略建议
4. 返回结构化的 JSON 分析结果

风险等级定义：
- low: 内容安全，无风险
- medium: 存在轻微风险，需要关注
- high: 明显违规内容，需要立即处理
- critical: 严重违规，需要紧急处理并上报

你必须严格按照以下 JSON 格式返回，不要包含任何其他文字：
{
  "risk_level": "low|medium|high|critical",
  "risk_score": 0-100的整数,
  "summary": "一句话总结分析结果",
  "strategy": "针对该内容的具体运营策略建议",
  "tags": ["标签1", "标签2"]
}"""


class ContentSecurityAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
        self.model = os.getenv("MODEL_NAME", "qwen-plus")

    def analyze(self, content: str, user_group: str = "general", source: str = "other", user_tags: list = None) -> dict:
        user_prompt = f"""请分析以下内容的安全风险：

内容来源：{source}
用户群体：{user_group}
用户标签：{json.dumps(user_tags or [], ensure_ascii=False)}
待分析内容：
{content}

请返回 JSON 格式的分析结果。"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        result_text = response.choices[0].message.content.strip()

        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:-3].strip()

        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            result = {
                "risk_level": "medium",
                "risk_score": 50,
                "summary": "AI 分析结果解析异常，请人工复核",
                "strategy": "建议人工审核该内容",
                "tags": ["解析异常"],
            }

        result.setdefault("risk_level", "medium")
        result.setdefault("risk_score", 50)
        result.setdefault("summary", "")
        result.setdefault("strategy", "")
        result.setdefault("tags", [])

        return result


_agent_instance = None


def get_agent() -> ContentSecurityAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ContentSecurityAgent()
    return _agent_instance