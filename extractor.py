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

from openai import OpenAI, BadRequestError

# 网络请求超时（秒）。没有超时的话，断网/服务端卡住时热键线程会永久挂起。
TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "30"))

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

# 提示词里出现 "json" 这个词，部分厂商的 json 模式才生效。
_SYSTEM = """你是一个日程/待办抽取助手。从用户给的文本里抽取一条日程(event)或待办(todo)。
现在的时间是：{now}。

判定规则（重要）：
- 只要文本表达了「要做的事」或「某个约定/安排」，即使时间模糊、甚至没写时间，也要判为 todo 或 event：
  有明确约见/会议/见面 → event；需要去做的任务/事项 → todo。
- 只有在完全没有任何可执行内容（纯闲聊、无任务无安排）时，才用 none。

时间处理：
- 尽量把"明天""下午3点""下周一""周末""月底前"换算成绝对时间，填进 time（ISO8601，如 2026-06-30T15:00:00）。
- 时间模糊到无法换算（如"改天""回头""有空""尽快"）时，time 填 null，但要把原文的时间/期限说法原样写进 time_text。
- 只有日期没具体时刻时，time 用当天 09:00 兜底，并在 time_text 注明（如"上午""全天"）。

只输出 json，不要任何额外文字。字段：
- type: "event" | "todo" | "none"
- title: 简短标题
- time: ISO8601 绝对时间，或 null
- time_text: 原文里的时间/期限说法（如"下周末""月底前""改天"），或 null
- location: 地点，或 null
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


_clients = {}


def _client(cfg) -> OpenAI:
    """按 (base_url, key) 复用客户端，避免每次热键都重建连接池。"""
    key = (cfg["base_url"], cfg["api_key"])
    cli = _clients.get(key)
    if cli is None:
        cli = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"] or None,
                     timeout=TIMEOUT, max_retries=1)
        _clients[key] = cli
    return cli


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
    client = _client(cfg)
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
        except BadRequestError:
            # 只在「参数不被支持」(400) 时回退不带 json 模式重试；
            # 认证/网络等错误直接抛出，别白白重试一次拖慢报错。
            resp = client.chat.completions.create(**kwargs)
    else:
        resp = client.chat.completions.create(**kwargs)
    return _parse_json(resp.choices[0].message.content)
