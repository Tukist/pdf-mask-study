# -*- coding: utf-8 -*-
"""图形界面（tkinter，标准库自带，不额外装东西）。

双击 exe 后就是这个窗口：选一个 PDF → 生成黑幕背诵网页 → 用浏览器打开。
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .render import convert, default_output

APP_TITLE = "PDF → 黑幕背诵网页"
INTRO = ("自动找出原文用【黑体】或【下划线】标出的重点与填空，"
         "把它们遮成黑幕，鼠标悬停显示答案。\n"
         "生成的网页不依赖网络，自带批注、手绘、撤销，可单独分享。")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("640x430")
        self.minsize(600, 400)

        self.pdf_var = tk.StringVar()
        self.out_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.status_var = tk.StringVar(value="① 先选一个 PDF 文件")
        self.result_var = tk.StringVar()
        self.queue: queue.Queue = queue.Queue()
        self.busy = False
        self.last_output = ""

        self._build()
        self.after(80, self._poll)

    # ------------------------------------------------------------ 界面
    def _build(self) -> None:
        pad = {"padx": 14, "pady": 6}

        tk.Label(self, text=INTRO, justify="left", fg="#555", font=("Microsoft YaHei UI", 9)
                 ).grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 2))

        ttk.Separator(self, orient="horizontal").grid(
            row=1, column=0, columnspan=3, sticky="ew", padx=14, pady=6)

        tk.Label(self, text="PDF 文件").grid(row=2, column=0, sticky="w", **pad)
        self.pdf_entry = tk.Entry(self, textvariable=self.pdf_var)
        self.pdf_entry.grid(row=2, column=1, sticky="ew", **pad)
        tk.Button(self, text="选择…", width=9, command=self.pick_pdf).grid(row=2, column=2, **pad)

        tk.Label(self, text="输出到").grid(row=3, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self.out_var).grid(row=3, column=1, sticky="ew", **pad)
        tk.Button(self, text="另存为…", width=9, command=self.pick_out).grid(row=3, column=2, **pad)

        tk.Label(self, text="网页标题").grid(row=4, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self.title_var).grid(
            row=4, column=1, columnspan=2, sticky="ew", **pad)

        self.go_btn = tk.Button(self, text="开始生成", width=16, height=2,
                                bg="#333c4a", fg="white", activebackground="#4a5568",
                                activeforeground="white", command=self.start)
        self.go_btn.grid(row=5, column=0, columnspan=3, pady=(12, 6))

        self.bar = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.bar.grid(row=6, column=0, columnspan=3, sticky="ew", padx=14)

        tk.Label(self, textvariable=self.status_var, fg="#333").grid(
            row=7, column=0, columnspan=3, sticky="w", padx=14, pady=(6, 0))
        tk.Label(self, textvariable=self.result_var, fg="#1a7f37", justify="left",
                 wraplength=590).grid(row=8, column=0, columnspan=3, sticky="w",
                                      padx=14, pady=(2, 0))

        self.open_btn = tk.Button(self, text="打开生成的网页", width=16,
                                  state="disabled", command=self.open_result)
        self.open_btn.grid(row=9, column=1, sticky="e", padx=14, pady=10)
        tk.Button(self, text="打开所在文件夹", width=14, state="normal",
                  command=self.open_folder).grid(row=9, column=2, sticky="w", padx=(0, 14), pady=10)

        self.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------ 交互
    def pick_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")])
        if not path:
            return
        self.pdf_var.set(path)
        base = os.path.splitext(os.path.basename(path))[0]
        if not self.title_var.get().strip():
            self.title_var.set(base)
        self.out_var.set(default_output(path))
        self.status_var.set("② 点「开始生成」")

    def pick_out(self) -> None:
        path = filedialog.asksaveasfilename(
            title="保存为", defaultextension=".html",
            initialfile=os.path.basename(self.out_var.get() or "背诵版.html"),
            filetypes=[("网页文件", "*.html")])
        if path:
            self.out_var.set(path)

    def start(self) -> None:
        if self.busy:
            return
        pdf = self.pdf_var.get().strip()
        if not pdf:
            messagebox.showinfo(APP_TITLE, "先选一个 PDF 文件吧")
            return
        if not os.path.isfile(pdf):
            messagebox.showerror(APP_TITLE, "找不到这个文件：\n%s" % pdf)
            return

        self.busy = True
        self.go_btn.config(state="disabled", text="正在生成…")
        self.open_btn.config(state="disabled")
        self.result_var.set("")
        self.bar["value"] = 0
        self.status_var.set("正在分析…")

        out = self.out_var.get().strip() or default_output(pdf)
        title = self.title_var.get().strip()
        footer = "由 pdf-mask-study 生成 · 双击页面可写批注 · 点「✎ 画笔」可随手画线"
        threading.Thread(target=self._work, args=(pdf, out, title, footer),
                         daemon=True).start()

    def _work(self, pdf: str, out: str, title: str, footer: str) -> None:
        try:
            def progress(done: int, total: int) -> None:
                self.queue.put(("progress", (done, total)))

            info = convert(pdf, out, title, footer, progress)
            self.queue.put(("done", info))
        except Exception:                                     # noqa: BLE001
            self.queue.put(("error", traceback.format_exc()))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "progress":
                    done, total = payload
                    self.bar["value"] = 100.0 * done / max(1, total)
                    self.status_var.set("正在分析第 %d / %d 页…" % (done, total))
                elif kind == "done":
                    self._finish(payload)
                else:
                    self._fail(payload)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _finish(self, info: dict) -> None:
        self.busy = False
        self.bar["value"] = 100
        self.go_btn.config(state="normal", text="再生成一次")
        self.last_output = info["output"]
        self.open_btn.config(state="normal")

        if info["hidden"] == 0:
            self.status_var.set("生成完成，但没发现黑体/下划线标记")
            self.result_var.set(
                "⚠ 这份 PDF 里没有识别到「黑体重点」或「下划线填空」，\n"
                "   网页内容是普通文本（仍然可以用批注和画笔）。\n"
                "   输出：%s" % info["output"])
        else:
            self.status_var.set("✓ 完成")
            self.result_var.set(
                "共 %d 页，遮住 %d 个字（占 %.1f%%）\n输出：%s"
                % (info["pages"], info["hidden"], info["ratio"], info["output"]))

        if messagebox.askyesno(APP_TITLE, "生成好了，现在打开看看吗？\n\n%s" % info["output"]):
            self.open_result()

    def _fail(self, text: str) -> None:
        self.busy = False
        self.go_btn.config(state="normal", text="开始生成")
        self.status_var.set("✗ 出错了")
        messagebox.showerror(APP_TITLE, "转换失败：\n\n%s" % text.strip().splitlines()[-1])
        try:
            if sys.stderr is not None:
                print(text, file=sys.stderr)
        except Exception:                                     # noqa: BLE001
            pass

    def open_result(self) -> None:
        if self.last_output and os.path.isfile(self.last_output):
            webbrowser.open("file:///" + os.path.abspath(self.last_output).replace("\\", "/"))

    def open_folder(self) -> None:
        target = os.path.dirname(os.path.abspath(self.last_output)) if self.last_output \
            else os.path.dirname(os.path.abspath(self.pdf_var.get() or "."))
        if not os.path.isdir(target):
            return
        if sys.platform.startswith("win"):
            os.startfile(target)                              # noqa: S606  (Windows 专用)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])


def main() -> None:
    # 带参数启动（比如把 PDF 文件拖到 exe 图标上）→ 直接转换，不弹窗口
    if len(sys.argv) > 1:
        from .cli import main as cli_main
        raise SystemExit(cli_main(sys.argv[1:]))
    App().mainloop()


if __name__ == "__main__":
    main()
