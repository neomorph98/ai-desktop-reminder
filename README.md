# AI 桌面日程提醒助手（v1）

把任意文字（聊天、邮件里的一句话）一键变成桌面提醒。

> 「公开构建」副业的第一个项目。v1 = 剪贴板 → AI 提取 → 本地提醒 + 桌面悬浮窗。

## 它能做什么

1. 在任何地方复制一段话，例：「明天下午 3 点和张总在会议室开会」
2. 按快捷键 `Ctrl+Alt+S`
3. AI（DeepSeek）自动识别 **类型 / 标题 / 时间 / 地点**，弹窗让你确认或修改
4. 保存后，桌面右上角的半透明悬浮窗显示即将到来的提醒（可拖动、可标记完成）

## 架构

| 文件 | 职责 |
|------|------|
| `main.py` | 全局快捷键 + 主循环（线程安全队列连接热键线程与 UI 线程） |
| `extractor.py` | DeepSeek 抽取：文本 → `{type,title,time,location}` |
| `store.py` | SQLite 存取 |
| `overlay.py` | tkinter 半透明置顶悬浮窗 + 确认弹窗 |

## 运行

```bash
# 1. 装依赖（建议先建虚拟环境）
pip install -r requirements.txt

# 2. 配置 key：复制 .env.example 为 .env，填入 DeepSeek key
#    （到 https://platform.deepseek.com 注册获取，充几块钱够用很久）

# 3. 启动
python main.py
```

启动后，复制一句带时间的话 → 按 `Ctrl+Alt+S`。

## 常见问题

- **快捷键没反应？** Windows 上个别情况 `keyboard` 需要管理员权限，试着用管理员身份运行终端。
- **想换快捷键？** 改 `.env` 里的 `HOTKEY`。
- **时间识别不准？** 调 `extractor.py` 里的提示词。

## 路线图

- [x] v1 剪贴板 + AI 抽取 + 本地提醒 + 桌面文字
- [ ] v2 接 Google Calendar
- [ ] v3 桌面动画提醒（Lively Wallpaper / Qt）
- [ ] v4 浏览器扩展：网页聊天右键一键添加
- [ ] v5 Outlook / 国内邮箱

## License

MIT
