# -*- coding: utf-8 -*-
"""把 analyze() 的分析结果渲染成一个自带全部交互的单文件 HTML。

生成的 HTML 不依赖任何外部文件、不联网，双击就能用：
黑幕自测、悬停显示、批注、手绘、撤销、导出备份都在里面。
"""

from __future__ import annotations

import hashlib
import html
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


def render_chars(chars: list[dict]) -> str:
    """把一串字符渲染成 HTML：答案是黑幕块，留白填空是横线。"""
    pieces: list[tuple] = []
    buf, state = "", None
    for ch in chars:
        if ch.get("hole"):
            if buf:
                pieces.append((state, buf))
                buf = ""
            pieces.append(("hole", ch))
            continue
        st = ch["ans"]
        if state is None:
            state = st
        if st != state:
            pieces.append((state, buf))
            buf, state = "", st
        buf += ch["c"]
    if buf:
        pieces.append((state, buf))

    out = []
    for kind, val in pieces:
        if kind == "hole":
            out.append('<i class="cl" style="width:%sem"></i>' % val["w"])
            continue
        if not kind:
            out.append(escape(val))
            continue
        core = val.strip(" ")
        if not core:
            out.append(escape(val))
            continue
        pad_l = len(val) - len(val.lstrip(" "))
        pad_r = len(val) - len(val.rstrip(" "))
        out.append(" " * pad_l + '<b class="b">%s</b>' % escape(core) + " " * pad_r)
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
    body = []
    for page in pages:
        parts = []
        for block in page["blocks"]:
            chars = block["chars"]
            if not "".join(c["c"] for c in chars).strip():
                continue
            tag = block["kind"]
            if tag in ("h1", "h2"):
                parts.append('<%s class="t">%s</%s>' % (tag, render_chars(chars), tag))
            else:
                parts.append("<p>%s</p>" % render_chars(chars))
        body.append('<section class="page" id="p%d">'
                    '<span class="pn">%d</span>\n%s\n</section>'
                    % (page["page"], page["page"], "\n".join(parts)))

    tpl = load_template()
    for key, val in (("__TITLE__", escape(title)),
                     ("__PAGES__", str(len(pages))),
                     ("__BODY__", "\n".join(body)),
                     ("__DOCKEY__", doc_key(title, pages)),
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
