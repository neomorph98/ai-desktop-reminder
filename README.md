# AI 桌面日程提醒助手（v1）

把任意文字（聊天、邮件里的一句话）一键变成桌面提醒。

> 「公开构建」副业的第一个项目。v1 = 剪贴板 → AI 提取 → 本地提醒 + 桌面悬浮窗。

## 它能做什么

1. 在任何地方复制一段话，例：「明天下午 3 点和张总在会议室开会」
2. 按快捷键 `Ctrl+Alt+S`
3. AI 自动识别 **类型 / 标题 / 时间 / 地点**，弹窗让你确认或修改
4. 保存后，桌面右上角的半透明悬浮窗显示即将到来的提醒（可拖动、可标记完成）

## 支持的 LLM（可配置）

默认 DeepSeek，也支持其它「OpenAI 兼容」的国内大模型，改 `.env` 里的 `LLM_PROVIDER` 即可切换，**代码不用动**：

| `LLM_PROVIDER` | 厂商 / 默认模型 | 需要的 key |
|---|---|---|
| `deepseek` | DeepSeek / `deepseek-chat` | `DEEPSEEK_API_KEY` |
| `glm` | 智谱 / `glm-4-flash` | `GLM_API_KEY` |
| `minimax` | MiniMax / `abab6.5s-chat` | `MINIMAX_API_KEY` |
| `qwen` | 通义千问 / `qwen-plus` | `DASHSCOPE_API_KEY` |
| `moonshot` | Kimi / `moonshot-v1-8k` | `MOONSHOT_API_KEY` |
| `custom` | 任意 OpenAI 兼容端点 | `LLM_API_KEY` |

> 想换模型或用自建/中转端点：用 `LLM_MODEL`、`LLM_BASE_URL`、`LLM_API_KEY` 覆盖默认值。
> MiniMax 的 `base_url`/`model` 可能因账号而异，按其控制台文档调整。

## 架构

| 文件 | 职责 |
|------|------|
| `main.py` | 全局快捷键 + 主循环（线程安全队列连接热键线程与 UI 线程） |
| `extractor.py` | 多供应商 LLM 抽取：文本 → `{type,title,time,location}` |
| `store.py` | SQLite 存取 |
| `overlay.py` | tkinter 半透明置顶悬浮窗 + 确认弹窗 |

## 运行

```bash
# 1. 装依赖（建议先建虚拟环境）
pip install -r requirements.txt

# 2. 配置：复制 .env.example 为 .env，选好 LLM_PROVIDER 并填入对应 key
#    例：LLM_PROVIDER=glm + GLM_API_KEY=...

# 3. 启动
python main.py
```

启动后，复制一句带时间的话 → 按 `Ctrl+Alt+S`。

## 常见问题

- **快捷键没反应？** Windows 上个别情况 `keyboard` 需要管理员权限，试着用管理员身份运行终端。
- **想换快捷键？** 改 `.env` 里的 `HOTKEY`。
- **想换模型？** 改 `.env` 里的 `LLM_PROVIDER`（或用 `LLM_MODEL` 覆盖具体模型）。
- **时间识别不准？** 调 `extractor.py` 里的提示词。

## 路线图

- [x] v1 剪贴板 + AI 抽取（多供应商）+ 本地提醒 + 桌面文字
- [ ] v2 接 Google Calendar
- [ ] v3 桌面动画提醒（Lively Wallpaper / Qt）
- [ ] v4 浏览器扩展：网页聊天右键一键添加
- [ ] v5 Outlook / 国内邮箱

## License

MIT
