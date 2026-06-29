"""DeepSeek 抽取：把一段文本变成结构化的日程/待办。

DeepSeek 的 API 与 OpenAI 兼容，所以直接用 openai SDK 指向它的 base_url。
"""
import os
import json
from datetime import datetime

from openai import OpenAI

_client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
    base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)
_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# 提示词里必须出现 "json" 这个词，DeepSeek 的 json_object 模式才生效。
_SYSTEM = """你是一个日程/待办抽取助手。从用户给的文本里抽取一条日程(event)或待办(todo)。
现在的时间是：{now}（请据此把"明天""下午3点""下周一"等相对时间换算成绝对时间）。
只输出 JSON，不要任何额外文字。字段：
- type: "event" | "todo" | "none"   // 文本里没有日程/待办时为 "none"
- title: 简短标题（字符串）
- time: ISO8601 本地时间，如 "2026-06-30T15:00:00"；没有明确时间则为 null
- location: 地点字符串；没有则为 null
- confidence: 0~1 之间的小数"""


def extract(text: str) -> dict:
    """返回 dict：{type,title,time,location,confidence}。失败/无内容时 type='none'。"""
    if not text or not text.strip():
        return {"type": "none"}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    resp = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM.format(now=now)},
            {"role": "user", "content": text.strip()[:2000]},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {"type": "none", "_raw": content}
