"""入口：全局快捷键 → 读剪贴板 → AI 抽取 → 确认 → 存本地 → 桌面显示。

线程模型：
- 主线程跑 tkinter mainloop（所有 UI）。
- keyboard 库的热键回调在另一个线程里跑（含网络请求），结果丢进 events 队列。
- tkinter 用 after() 轮询队列，在主线程里弹窗，保证线程安全。
"""
import os
import queue

from dotenv import load_dotenv
import pyperclip
import keyboard

load_dotenv()

import store
import extractor
from overlay import Overlay, show_confirm, show_message

HOTKEY = os.environ.get("HOTKEY", "ctrl+alt+s")
events = queue.Queue()


def on_hotkey():
    """在 keyboard 线程里执行。"""
    text = pyperclip.paste()
    if not text or not text.strip():
        events.put(("empty", None, None))
        return
    try:
        data = extractor.extract(text)
        events.put(("result", data, text))
    except Exception as e:  # 网络 / 解析等异常
        events.put(("error", str(e), text))


def poll(app):
    try:
        while True:
            kind, data, src = events.get_nowait()
            if kind == "empty":
                show_message(app.root, "剪贴板是空的。先复制一段文字再按快捷键。")
            elif kind == "error":
                show_message(app.root, f"抽取失败：{data}")
            elif kind == "result":
                if isinstance(data, dict) and data.get("type") in ("event", "todo"):
                    show_confirm(app.root, data, src, on_save=lambda d, s: save(app, d, s))
                else:
                    show_message(app.root, "没在剪贴板里找到日程或待办。")
    except queue.Empty:
        pass
    app.root.after(200, lambda: poll(app))


def save(app, data, src):
    store.add_reminder(data.get("type"), data.get("title"), data.get("time"),
                       data.get("location"), src)
    app.refresh()


def main():
    store.init_db()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("⚠️  未检测到 DEEPSEEK_API_KEY，请把 .env.example 复制为 .env 并填入 key。")
    app = Overlay()
    keyboard.add_hotkey(HOTKEY, on_hotkey)
    print(f"✅ 已启动。复制文字后按 {HOTKEY} 添加提醒。点悬浮窗右上角 ✕ 退出。")
    app.root.after(200, lambda: poll(app))
    try:
        app.root.mainloop()
    finally:
        keyboard.unhook_all()


if __name__ == "__main__":
    main()
