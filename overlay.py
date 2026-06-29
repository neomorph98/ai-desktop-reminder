"""桌面 UI：半透明置顶悬浮窗 + 确认弹窗。

tkinter 不是线程安全的，所有 UI 操作都在主线程；热键线程通过队列把数据传进来
（见 main.py 的 poll）。
"""
import tkinter as tk

import store

BG = "#1e1e2e"
FG = "#cdd6f4"
SUB = "#a6adc8"
ACCENT = "#89b4fa"
CARD = "#313244"
FONT = "Microsoft YaHei"


class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)          # 无边框
        self.root.attributes("-topmost", True)    # 置顶
        self.root.attributes("-alpha", 0.92)      # 半透明
        self.root.configure(bg=BG)
        self.width = 300
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{self.width}x220+{sw - self.width - 20}+40")  # 右上角
        self._build()
        self.refresh()
        self.root.after(30000, self._tick)        # 每 30s 自动刷新

    def _build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(header, text="📌 即将提醒", fg=FG, bg=BG,
                 font=(FONT, 11, "bold")).pack(side="left")
        tk.Button(header, text="✕", command=self.root.destroy, bg=BG, fg=SUB, bd=0,
                  activebackground=BG, activeforeground=FG).pack(side="right")
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        # 拖动整个窗
        for w in (self.root, header):
            w.bind("<Button-1>", self._start_move)
            w.bind("<B1-Motion>", self._on_move)

    def _start_move(self, e):
        self._mx, self._my = e.x, e.y

    def _on_move(self, e):
        x = self.root.winfo_x() + e.x - self._mx
        y = self.root.winfo_y() + e.y - self._my
        self.root.geometry(f"+{x}+{y}")

    def _tick(self):
        self.refresh()
        self.root.after(30000, self._tick)

    def refresh(self):
        for w in self.body.winfo_children():
            w.destroy()
        items = store.upcoming()
        if not items:
            tk.Label(self.body, text="暂无提醒。复制文字后按快捷键添加。", fg=SUB, bg=BG,
                     font=(FONT, 9), wraplength=self.width - 30, justify="left").pack(anchor="w")
            return
        for it in items:
            self._row(it)

    def _row(self, it):
        icon = "📅" if it.get("type") == "event" else "✅"
        t = it.get("start_time") or "（无时间）"
        loc = f"  @ {it['location']}" if it.get("location") else ""
        card = tk.Frame(self.body, bg=CARD)
        card.pack(fill="x", pady=3)
        tk.Label(card, text=f"{icon} {it.get('title', '')}", fg=FG, bg=CARD, font=(FONT, 10),
                 wraplength=self.width - 70, justify="left").pack(anchor="w", padx=8, pady=(5, 0))
        tk.Label(card, text=f"{t}{loc}", fg=SUB, bg=CARD,
                 font=(FONT, 8)).pack(anchor="w", padx=8)
        tk.Button(card, text="完成", command=lambda r=it["id"]: self._done(r), bg=CARD, fg=ACCENT,
                  bd=0, font=(FONT, 8), activebackground=CARD).pack(anchor="e", padx=6, pady=(0, 4))

    def _done(self, rid):
        store.mark_done(rid)
        self.refresh()


def show_confirm(root, data, source_text, on_save):
    """弹出可编辑的确认窗；点保存时调用 on_save(dict, source_text)。"""
    win = tk.Toplevel(root)
    win.title("确认提醒")
    win.attributes("-topmost", True)
    win.configure(bg=BG)
    win.geometry("380x300")

    fields = {}

    def add_field(label, key, default):
        tk.Label(win, text=label, fg=FG, bg=BG, font=(FONT, 9)).pack(anchor="w", padx=18, pady=(8, 0))
        var = tk.StringVar(value=default if default is not None else "")
        tk.Entry(win, textvariable=var).pack(padx=18, fill="x")
        fields[key] = var

    add_field("类型 (event / todo)", "type", data.get("type", "todo"))
    add_field("标题", "title", data.get("title"))
    add_field("时间 (YYYY-MM-DDTHH:MM:SS，可留空)", "time", data.get("time"))
    add_field("地点（可留空）", "location", data.get("location"))

    btns = tk.Frame(win, bg=BG)
    btns.pack(pady=16)

    def save():
        d = {k: (v.get().strip() or None) for k, v in fields.items()}
        on_save(d, source_text)
        win.destroy()

    tk.Button(btns, text="保存", command=save, bg=ACCENT, fg=BG, font=(FONT, 10, "bold"),
              width=8).pack(side="left", padx=6)
    tk.Button(btns, text="取消", command=win.destroy, bg=CARD, fg=FG, width=8).pack(side="left", padx=6)


def show_message(root, msg):
    win = tk.Toplevel(root)
    win.title("提示")
    win.attributes("-topmost", True)
    win.configure(bg=BG)
    tk.Label(win, text=msg, fg=FG, bg=BG, font=(FONT, 10),
             wraplength=300, justify="left").pack(padx=24, pady=20)
    tk.Button(win, text="好", command=win.destroy, bg=CARD, fg=FG, width=8).pack(pady=(0, 16))
    win.after(5000, win.destroy)
