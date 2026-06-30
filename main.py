"""入口：全局快捷键 → 读剪贴板 → AI 抽取 → 确认 → 存本地 → 桌面显示。

线程模型：
- 主线程跑 tkinter mainloop（所有 UI）。
- keyboard 库的热键回调在另一个线程里跑（含网络请求），结果丢进 events 队列。
- tkinter 用 after() 轮询队列，在主线程里弹窗，保证线程安全。
"""
import os
import time
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


def _grab_selection() -> str:
    """模拟 Ctrl+C 复制「当前选中的文字」，再读剪贴板。

    这样用户「选中文字 → 按快捷键」即可，不必先手动 Ctrl+C；
    若没有选中文字，则回退到原有剪贴板内容（兼容「先复制再按键」）。
    """
    prev = ""
    try:
        prev = pyperclip.paste()
    except Exception:
        pass
    # 松开可能还按着的快捷键修饰键，避免和接下来的 Ctrl+C 串台
    for k in ("alt", "ctrl", "shift", "windows"):
        try:
            keyboard.release(k)
        except Exception:
            pass
    try:
        pyperclip.copy("")            # 先清空，便于判断到底有没有复制到东西
    except Exception:
        pass
    time.sleep(0.05)
    keyboard.send("ctrl+c")           # 模拟复制选中的文字
    time.sleep(0.15)                  # 给系统时间把选区写进剪贴板（慢的应用可调大）
    text = ""
    try:
        text = pyperclip.paste()
    except Exception:
        pass
    if not text:                      # 没选中 → 回退到原剪贴板（兼容先复制的用法）
        text = prev
    try:
        pyperclip.copy(prev)          # 还原用户原来的剪贴板，别破坏它
    except Exception:
        pass
    return text


def on_hotkey():
    """在 keyboard 线程里执行。"""
    text = _grab_selection()
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
                show_message(app.root, "没捕捉到文字。请先用鼠标选中一段文字，再按快捷键。")
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
                       data.get("time_text"), data.get("location"), src)
    app.refresh()


def main():
    store.init_db()
    info = extractor.current()
    if not info["has_key"]:
        print(f"⚠️  当前 LLM 供应商 = {info['provider']}，但未找到对应 API key，请在 .env 配置。")
    else:
        print(f"🤖 LLM: {info['provider']} / {info['model']}")
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
