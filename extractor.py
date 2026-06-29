"""LLM 抽取：把一段文本变成结构化的日程/待办。

支持多家「OpenAI 兼容」的国内大模型，通过 .env 里的 LLM_PROVIDER 选择：
  deepseek | glm(智谱) | minimax | qwen(通义) | moonshot(Kimi) | custom
绝大多数国内厂商都提供 OpenAI 兼容端点，所以这里统一用 openai SDK，
只需切换 base_url / model / api_key 即可。
"""
import os
import re
import json
from datetime import datetime

from openai import OpenAI

# 供应商注册表：name -> 默认配置。可被 .env 里的 LLM_* 覆盖。
PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "key_env": "DEEPSEEK_API_KEY",
        "json_mode": True,
    },
    "glm": {  # 智谱 BigModel
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",      # 便宜，常有免费额度
        "key_env": "GLM_API_KEY",
        "json_mode": True,
    },
    "minimax": {
        "base_url": "https://api.minimax.chat/v1",
        "model": "abab6.5s-chat",
        "key_env": "MINIMAX_API_KEY",
        "json_mode": False,          # 保守：靠提示词 + 容错解析
    },
    "qwen": {  # 通义千问 DashScope 兼容模式
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "key_env": "DASHSCOPE_API_KEY",
        "json_mode": True,
    },
    "moonshot": {  # Kimi
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "key_env": "MOONSHOT_API_KEY",
        "json_mode": True,
    },
    "custom": {  # 自建 / 中转 / 其它 OpenAI 兼容端点，全靠 LLM_* 覆盖
        "base_url": "",
        "model": "",
        "key_env": "LLM_API_KEY",
        "json_mode": True,
    },
}

# 提示词里必须出现 "json" 这个词，部分厂商的 json 模式才生效。
_SYSTEM = """你是一个日程/待办抽取助手。从用户给的文本里抽取一条日程(event)或待办(todo)。
现在的时间是：{now}（请据此把"明天""下午3点""下周一"等相对时间换算成绝对时间）。
只输出 JSON，不要任何额外文字。字段：
- type: "event" | "todo" | "none"   // 文本里没有日程/待办时为 "none"
- title: 简短标题（字符串）
- time: ISO8601 本地时间，如 "2026-06-30T15:00:00"；没有明确时间则为 null
- location: 地点字符串；没有则为 null
- confidence: 0~1 之间的小数"""


def _config() -> dict:
    name = os.environ.get("LLM_PROVIDER", "deepseek").strip().lower()
    cfg = dict(PROVIDERS.get(name, PROVIDERS["deepseek"]))
    cfg["name"] = name if name in PROVIDERS else "deepseek"
    # .env 覆盖（优先级最高）：自建 / 中转 / 换模型时用
    cfg["base_url"] = os.environ.get("LLM_BASE_URL") or cfg["base_url"]
    cfg["model"] = os.environ.get("LLM_MODEL") or cfg["model"]
    cfg["api_key"] = os.environ.get("LLM_API_KEY") or os.environ.get(cfg["key_env"], "")
    return cfg


def current() -> dict:
    """给启动信息 / UI 用：当前供应商、模型、是否配了 key。"""
    cfg = _config()
    return {
        "provider": cfg["name"],
        "model": cfg["model"] or "(未指定)",
        "base_url": cfg["base_url"] or "(未指定)",
        "has_key": bool(cfg["api_key"]),
    }


def _parse_json(content: str) -> dict:
    if not content:
        return {"type": "none"}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.DOTALL)  # 容错：抠出花括号包住的部分
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"type": "none", "_raw": content}


def extract(text: str) -> dict:
    """返回 {type,title,time,location,confidence}；无内容/失败时 type='none'。"""
    if not text or not text.strip():
        return {"type": "none"}

    cfg = _config()
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"] or None)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    kwargs = dict(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": _SYSTEM.format(now=now)},
            {"role": "user", "content": text.strip()[:2000]},
        ],
        temperature=0,
    )
    if cfg.get("json_mode"):
        try:
            resp = client.chat.completions.create(
                response_format={"type": "json_object"}, **kwargs)
        except Exception:
            resp = client.chat.completions.create(**kwargs)  # 回退：不带 json 模式
    else:
        resp = client.chat.completions.create(**kwargs)
    return _parse_json(resp.choices[0].message.content)
