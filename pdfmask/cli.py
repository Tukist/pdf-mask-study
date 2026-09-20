# -*- coding: utf-8 -*-
"""命令行入口。

    python -m pdfmask 复习资料.pdf
    python -m pdfmask 复习资料.pdf -o 输出.html -t "期末复习"

也可以把 PDF 文件直接拖到 exe 图标上。
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser

from .render import convert


def prepare_console() -> None:
    """打包成 windowed exe 时没有控制台，标准输出可能不存在或编码不对。

    这里统一兜一下，保证不会因为打印一句话就把程序搞崩。
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                     # noqa: BLE001
            pass


def say(text: str = "") -> None:
    try:
        if sys.stdout is not None:
            print(text)
    except Exception:                                         # noqa: BLE001
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdfmask",
        description="把 PDF 复习资料转成「黑幕自测」网页 —— 自动遮住原文标出的重点和填空，"
                    "鼠标悬停显示答案。",
    )
    parser.add_argument("pdf", help="要转换的 PDF 文件")
    parser.add_argument("-o", "--output", help="输出 HTML 路径（默认：<文件名>_背诵版.html）")
    parser.add_argument("-t", "--title", help="网页标题（默认用文件名）")
    parser.add_argument("--no-open", action="store_true", help="生成后不自动打开浏览器")
    parser.add_argument("--footer", default="", help="页脚说明文字")
    return parser


def main(argv: list[str] | None = None) -> int:
    prepare_console()
    args = build_parser().parse_args(argv)

    if not os.path.isfile(args.pdf):
        say("找不到文件：%s" % args.pdf)
        return 2

    last = [-1]

    def progress(done: int, total: int) -> None:
        if total <= 0 or done == last[0]:
            return
        last[0] = done
        filled = int(done * 30 / total)
        try:
            if sys.stdout is not None:
                sys.stdout.write("\r  分析中 [%s%s] %d/%d 页"
                                 % ("#" * filled, "." * (30 - filled), done, total))
                sys.stdout.flush()
        except Exception:                                     # noqa: BLE001
            pass

    say("正在读取：%s" % args.pdf)
    try:
        info = convert(args.pdf, args.output, args.title, args.footer, progress)
    except Exception as exc:                                  # noqa: BLE001
        say("")
        say("转换失败：%s" % exc)
        return 1
    say("")

    if info["hidden"] == 0:
        say("[!] 没有识别到任何「黑体重点」或「下划线填空」。")
        say("    这份 PDF 可能没有用这两种方式标重点，生成的网页会是普通文本。")
    else:
        say("[OK] 完成：共 %d 页，遮住 %d 个字（占 %.1f%%）"
            % (info["pages"], info["hidden"], info["ratio"]))
    say("[OK] 输出：%s" % info["output"])

    if not args.no_open:
        target = os.path.abspath(info["output"]).replace("\\", "/")
        try:
            webbrowser.open("file:///" + target)
        except Exception:                                     # noqa: BLE001
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
