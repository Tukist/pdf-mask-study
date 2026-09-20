# -*- coding: utf-8 -*-
"""把 analyze() 的分析结果渲染成一个自带全部交互的单文件 HTML。

生成的 HTML 不依赖任何外部文件、不联网，双击就能用：
黑幕自测、悬停显示、批注、手绘、撤销、导出备份都在里面。
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import sys


def asset_path(name: str) -> str:
    """资源文件位置（兼容 PyInstaller 打包后的临时解包目录）。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", name)


def load_template() -> str:
    with open(asset_path("template.html"), encoding="utf-8") as f:
        return f.read()


def escape(text: str) -> str:
    return html.escape(text, quote=False)


FONT_CN = {
    "simhei": "黑体", "simsun": "宋体", "fangsong": "仿宋", "kaiti": "楷体",
    "microsoftyahei": "微软雅黑", "simkai": "楷体", "msyh": "微软雅黑",
    "timesnewroman": "Times", "arial": "Arial", "helvetica": "Helvetica",
}


def font_cn(name: str) -> str:
    """把字体名翻译成人话，认不出来就用原名。"""
    low = name.lower()
    for key, cn in FONT_CN.items():
        if key in low:
            return cn
    return name


def sig_of(ch: dict) -> tuple:
    """一个字符的「格式」＝ 字体 + 字号 + 粗体 + 下划线。"""
    return (ch["font"], ch["size"], bool(ch.get("bold")), bool(ch.get("ul")))


def format_name(sig: tuple) -> str:
    font, size, bold, ul = sig
    name = font_cn(font)
    parts = [name]
    if bold and not any(k in name for k in ("黑", "粗", "Hei", "Bold")):
        parts.append("粗体")
    parts.append("%g" % size)
    if ul:
        parts.append("下划线")
    return " ".join(parts)


def collect_formats(pages: list[dict]) -> tuple[dict, list]:
    """扫全文给每种格式编号。

    出现最多的那个排 0 号，网页里可以省略不写，省点体积。
    """
    counter: dict = {}
    for page in pages:
        for block in page["blocks"]:
            for ch in block["chars"]:
                if ch.get("hole"):
                    continue
                sig = sig_of(ch)
                counter[sig] = counter.get(sig, 0) + 1
    ordered = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ids = {sig: i for i, (sig, _) in enumerate(ordered)}
    return ids, [format_name(sig) for sig, _ in ordered]


def render_chars(chars: list[dict], fmt_ids: dict) -> str:
    """把一串字符渲染成 HTML。

    包裹方式（黑幕 / 普通）按「是否遮住 + 格式」分组：
    遮住的用 <b class="b">，没遮的用 <span data-f>；0 号格式（最常见那种）
    省略属性，省体积。
    """
    out: list[str] = []
    buf, cur = "", None

    def flush() -> None:
        nonlocal buf, cur
        if not buf:
            return
        if cur is None or not cur[1]:
            # 没遮的普通文字
            if cur is None or cur[0] == 0:
                out.append(escape(buf))
            else:
                out.append('<span data-f="%d">%s</span>' % (cur[0], escape(buf)))
        else:
            core = buf.strip(" ")
            if not core:
                out.append(escape(buf))
            else:
                pad_l = len(buf) - len(buf.lstrip(" "))
                pad_r = len(buf) - len(buf.rstrip(" "))
                fid = ' data-f="%d"' % cur[0] if cur[0] else ""
                out.append(" " * pad_l
                           + '<b class="b"%s>%s</b>' % (fid, escape(core))
                           + " " * pad_r)
        buf = ""

    for ch in chars:
        if ch.get("hole"):
            flush()
            out.append('<i class="cl" style="width:%sem"></i>' % ch["w"])
            continue
        key = (fmt_ids.get(sig_of(ch), 0), ch["ans"])
        if cur is None:
            cur = key
        elif key != cur:
            flush()
            cur = key
        buf += ch["c"]
    flush()
    return "".join(out)


def doc_key(title: str, pages: list[dict]) -> str:
    """给每份资料算一个稳定的 id。

    浏览器里的批注 / 手绘 / 画笔设置是按这个 id 分开存的，
    所以同一个浏览器打开多份资料不会互相串。
    """
    sample = title + "|" + str(len(pages))
    for page in pages[:3]:
        for block in page["blocks"]:
            sample += "".join(c["c"] for c in block["chars"])[:120]
    return hashlib.md5(sample.encode("utf-8")).hexdigest()[:12]


def render(pages: list[dict], title: str, footer: str = "") -> str:
    """pages 来自 analyze()，返回完整的 HTML 文本。"""
    fmt_ids, fmt_names = collect_formats(pages)
    body = []
    for page in pages:
        parts = []
        for bi, block in enumerate(page["blocks"]):
            chars = block["chars"]
            if not "".join(c["c"] for c in chars).strip():
                continue
            # data-b 是该段落在本页内的序号，浏览器里「手动涂黑」靠它定位
            tag = block["kind"]
            if tag in ("h1", "h2"):
                parts.append('<%s class="t" data-b="%d">%s</%s>'
                             % (tag, bi, render_chars(chars, fmt_ids), tag))
            else:
                parts.append('<p data-b="%d">%s</p>'
                             % (bi, render_chars(chars, fmt_ids)))
        body.append('<section class="page" id="p%d">'
                    '<span class="pn">%d</span>\n%s\n</section>'
                    % (page["page"], page["page"], "\n".join(parts)))

    tpl = load_template()
    for key, val in (("__TITLE__", escape(title)),
                     ("__PAGES__", str(len(pages))),
                     ("__BODY__", "\n".join(body)),
                     ("__DOCKEY__", doc_key(title, pages)),
                     ("__FMT__", json.dumps(fmt_names, ensure_ascii=False)),
                     ("__FOOTER__", footer)):
        tpl = tpl.replace(key, val)
    return tpl


def default_output(pdf_path: str) -> str:
    root, _ = os.path.splitext(pdf_path)
    return root + "_背诵版.html"


def convert(pdf_path: str, out_path: str | None = None, title: str | None = None,
            footer: str = "", progress=None) -> dict:
    """一站式转换：PDF → 黑幕背诵网页。

    返回 {"output": 路径, "pages": 页数, "total": 字数, "hidden": 遮住字数}。
    """
    from .analyze import analyze, stats

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(pdf_path)
    if not title:
        title = os.path.splitext(os.path.basename(pdf_path))[0]
    pages = analyze(pdf_path, progress=progress)
    out_path = out_path or default_output(pdf_path)
    html_text = render(pages, title, footer)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    info = stats(pages)
    info["output"] = out_path
    info["pages"] = len(pages)
    return info
