# -*- coding: utf-8 -*-
"""PDF 结构分析：找出原文自己标出的「重点」和「填空」。

识别两类标记：

1. **黑体 / 粗体** —— 正文用宋体/仿宋，重点句换成黑体（或带粗体标志），
   这类文字会被当作「填空答案」遮住。
2. **下划线** —— 页面上贴着文字底部的细横线。线上有字的是「画了线的答案」，
   线上没字的是「留白的填空横线」，两者都会处理。

输出的是与渲染无关的中间结构，方便单测：

    [{"page": 1,
      "blocks": [
          {"kind": "h1" | "h2" | "p",
           "chars": [{"c": "字", "ans": False, "size": 13.6, ...}, ...]},
      ]}]
"""

from __future__ import annotations

import re
from collections import Counter

import fitz  # PyMuPDF

# 字体名里出现这些词，就认为它是「加粗 / 加黑」的强调字体
BOLD_HINTS = ("bold", "black", "heavy", "semibold", "hei", "黑")

# 行首是这些模式 → 视作新段落开头
NEW_PARA = re.compile(
    r"^(\d+[、.]\s*|[一二三四五六七八九十百]+、|（[一二三四五六七八九十]+）|"
    r"\([一二三四五六七八九十]+\)|第[一二三四五六七八九十]+[部分章节讲条]|"
    r"材料示例[一二三四五六七八九十]+|【答案】|[A-D][\.、]\s|练习题)"
)

# 这些 span 是「题号 / 选项号」，不代表正文的左边距
NUM_SPAN = re.compile(r"^(\d+[\.、]|[A-D][\.、]|【答案】|材料示例[一二三四五六七八九十]+)")

# 「第X部分」「练习题」这种独占一行的总标题
HARD_H1 = re.compile(r"^(第[一二三四五六七八九十]+[部分章节讲]|练习题)$")

# 「一、xxx」这种短标题
SMALL_TITLE = re.compile(r"^[一二三四五六七八九十]+、[^，。；：]{2,24}$")


# ---------------------------------------------------------------- 文档画像

def document_profile(doc) -> tuple[str, float]:
    """统计全文，推断「正文用什么字体、多大字号」。

    正文一定是占字数最多的那个，标题和重点只占少数。
    """
    fonts: Counter = Counter()
    sizes: Counter = Counter()
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if len(text) < 2:
                        continue
                    fonts[span["font"]] += len(text)
                    sizes[round(span["size"], 1)] += len(text)
    body_font = fonts.most_common(1)[0][0] if fonts else ""
    body_size = sizes.most_common(1)[0][0] if sizes else 12.0
    return body_font, body_size


def is_emphasis(span, body_size: float) -> bool:
    """这个 span 是不是原文标出的「重点」（黑体 / 粗体）？"""
    if round(span["size"], 1) > body_size * 1.25:
        return False                       # 比正文大不少 → 是标题，不是填空
    if span["flags"] & 16:                 # PDF 自带的粗体标志
        return True
    name = span["font"].lower()
    return any(hint in name for hint in BOLD_HINTS)


def span_text(span) -> str:
    return "".join(ch["c"] for ch in span["chars"])


# ---------------------------------------------------------------- 单页提取

def underline_rects(page) -> list:
    """页面上的水平细线（下划线 / 填空横线）。"""
    out = []
    for drawing in page.get_drawings():
        if drawing["type"] != "s":
            continue
        rect = drawing["rect"]
        if rect.height > 2 or rect.width < 3:
            continue
        out.append(rect)
    return out


def normalize_line(text: str) -> str:
    """把页码之类的数字抹平，用来判断两行是不是同一个页眉。"""
    return re.sub(r"\d+", "#", text.strip())


def detect_running_heads(doc, sample: int = 30) -> tuple[set, set]:
    """找出在多数页面的顶部/底部反复出现的文字 —— 那就是页眉页脚。

    只看位置是不够的：有些资料第一页的大标题也在顶部，按位置一刀切会丢内容。
    重复出现才是页眉的本质特征。

    采样要**均匀铺开**：有些资料前后两段的页眉不一样，只看开头几页会漏掉。
    """
    top: Counter = Counter()
    bottom: Counter = Counter()
    total = doc.page_count
    n = min(sample, total)
    step = max(1, total // n)
    indexes = list(range(0, total, step))[:n]

    for i in indexes:
        page = doc[i]
        height = page.rect.height
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                text = normalize_line("".join(s["text"] for s in line["spans"]))
                if not text:
                    continue
                if line["bbox"][3] < height * 0.15:
                    top[text] += 1
                elif line["bbox"][1] > height * 0.85:
                    bottom[text] += 1
    # 门槛＝采样数的 15%（至少 3 次）。一份资料前后换页眉、或页眉只覆盖
    # 前几章都很常见，用「过半」会漏；而「同一位置 + 整行文字完全相同」
    # 本身已经足够严格，不会把正文误判进来。
    need = max(3, int(len(indexes) * 0.15))
    return ({k for k, v in top.items() if v >= need},
            {k for k, v in bottom.items() if v >= need})


def collect_rows(page, body_size: float,
                 heads: set = frozenset(), feet: set = frozenset()) -> list[dict]:
    """把一页的文字按「视觉行」聚合，并逐字标出哪些属于填空答案。"""
    page_h = page.rect.height
    ulines = underline_rects(page)
    used_lines = set()

    spans = []
    for block in page.get_text("rawdict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            line_text = normalize_line("".join(span_text(s) for s in line["spans"]))
            if line["bbox"][3] < page_h * 0.15 and line_text in heads:
                continue                           # 反复出现的页眉
            if line["bbox"][1] > page_h * 0.85 and line_text in feet:
                continue                           # 反复出现的页脚（页码等）
            for span in line["spans"]:
                if not span_text(span).strip():
                    continue
                spans.append(span)

    # 按纵向位置聚成视觉行（同一行的不同字体，y 会差几个 pt）
    spans.sort(key=lambda s: (s["bbox"][1] + s["bbox"][3]) / 2)
    rows: list[dict] = []
    for span in spans:
        yc = (span["bbox"][1] + span["bbox"][3]) / 2
        if rows and abs(yc - rows[-1]["y"]) < 7:
            rows[-1]["spans"].append(span)
        else:
            rows.append({"y": yc, "spans": [span]})

    for row in rows:
        row["spans"].sort(key=lambda s: s["bbox"][0])
        chars: list[dict] = []
        prev_end = None
        for span in row["spans"]:
            gap = span["bbox"][0] - prev_end if prev_end is not None else 0
            if prev_end is not None and gap > 5:
                chars.append({"c": " ", "ans": False, "size": 13.6,
                              "font": span["font"], "x0": prev_end, "x1": prev_end,
                              "y1": row["y"]})
            emphasized = is_emphasis(span, body_size)
            black = span["color"] == 0
            for ch in span["chars"]:
                x0, _, x1, y1 = ch["bbox"]
                cx = (x0 + x1) / 2
                under = False
                if not ch["c"].isspace():
                    for idx, rect in enumerate(ulines):
                        if (rect.x0 - 1.3 <= cx <= rect.x1 + 1.3
                                and rect.y0 - 3.6 <= y1 <= rect.y0 + 3.6):
                            under = True
                            used_lines.add(idx)
                            break
                chars.append({
                    "c": ch["c"],
                    "ans": bool(emphasized or (under and black)),
                    "size": round(span["size"], 1),
                    "font": span["font"],
                    "x0": x0, "x1": x1, "y1": y1,
                })
            prev_end = span["bbox"][2]
        row["chars"] = chars

        # 行的「有效左边距」：跳过题号之类的编号
        effective_x0 = row["spans"][0]["bbox"][0]
        for span in row["spans"]:
            text = span_text(span).strip()
            if text and not NUM_SPAN.match(text):
                effective_x0 = span["bbox"][0]
                break
        row["x0"] = effective_x0
        sizes = [c["size"] for c in chars if c["c"].strip()]
        row["size"] = max(sizes) if sizes else body_size
        row["fonts"] = {c["font"] for c in chars if c["c"].strip()}

    # 留白的填空横线：线上一个字都没有 → 生成一条占位横线
    for idx, rect in enumerate(ulines):
        if idx in used_lines:
            continue
        has_char = False
        for row in rows:
            for ch in row["chars"]:
                if not ch["c"].strip():
                    continue
                cx = (ch["x0"] + ch["x1"]) / 2
                if (rect.x0 - 1.3 <= cx <= rect.x1 + 1.3
                        and abs(ch["y1"] - rect.y0) < 3.6):
                    has_char = True
                    break
            if has_char:
                break
        if has_char:
            continue
        target, best = None, 99.0
        for row in rows:
            for ch in row["chars"]:
                if not ch["c"].strip():
                    continue
                d = abs(ch["y1"] - rect.y0)
                if d < best:
                    best, target = d, row
            if target is not None and best < 3.6:
                break
        if target is None or best >= 3.6:
            continue
        pos = len(target["chars"])
        for i, ch in enumerate(target["chars"]):
            if ch["x0"] > rect.x0 - 2:
                pos = i
                break
        width_em = (rect.x1 - rect.x0) / max(10.0, target["size"])
        target["chars"].insert(pos, {
            "c": "", "ans": False, "hole": True, "w": round(width_em, 2),
            "size": target["size"], "x0": rect.x0, "x1": rect.x1, "y1": rect.y0,
        })

    return rows


def mark_answer_key(rows: list[dict]) -> list[dict]:
    """选择题的「【答案】A」：把选项字母也一起遮住。"""
    for row in rows:
        text = "".join(c["c"] for c in row["chars"])
        if not re.match(r"^【答案】\s*[A-Za-z]", text):
            continue
        for ch in row["chars"][text.index("】") + 1:]:
            if ch["c"].strip():
                ch["ans"] = True
    return rows


# ---------------------------------------------------------------- 段落重建

def is_big_title(row, body_size: float, title_fonts: set[str]) -> bool:
    """这一行是不是标题？（标题一律不遮）

    注意 title_fonts 里**不能**放正文字体：有些资料的大段正文本身就是
    14 号往上（比如填空题部分），只按字号一刀切会把整段正文误判成标题。
    """
    text = "".join(c["c"] for c in row["chars"]).strip()
    if HARD_H1.match(text) or SMALL_TITLE.match(text):
        return True
    if row["size"] >= body_size * 1.12:          # 明显比正文大
        return True
    return row["size"] >= 14.0 and row["fonts"] <= title_fonts


def build_blocks(rows: list[dict], body_size: float,
                 title_fonts: set[str]) -> list[dict]:
    """把行合并成段落 / 标题块。"""
    blocks: list[dict] = []
    prev_y = None
    for row in rows:
        plain = "".join(c["c"] for c in row["chars"]).strip()
        if not plain:
            continue
        gap = (row["y"] - prev_y) if prev_y is not None else 0

        if is_big_title(row, body_size, title_fonts):
            hard = bool(HARD_H1.match(plain))
            prev_text = ""
            if blocks:
                prev_text = "".join(c["c"] for b in blocks[-1]["rows"]
                                    for c in b["chars"]).strip()
            prev_hard = bool(HARD_H1.match(prev_text))
            if (blocks and blocks[-1]["kind"] in ("h1", "h2")
                    and gap <= 30 and not hard and not prev_hard):
                blocks[-1]["rows"].append(row)          # 标题的换行续行
            else:
                first = not blocks                      # 开篇的大字标题按一级标题走
                kind = "h1" if (hard or row["size"] >= 19
                                or (first and row["size"] >= 15.0)) else "h2"
                blocks.append({"kind": kind, "rows": [row]})
            prev_y = row["y"]
            continue

        new_para = True
        if blocks and blocks[-1]["kind"] == "p":
            last = blocks[-1]["rows"][-1]
            if not NEW_PARA.match(plain) and row["x0"] - last["x0"] < 12 and gap <= 34:
                new_para = False
        if new_para:
            blocks.append({"kind": "p", "rows": [row]})
        else:
            blocks[-1]["rows"].append(row)
        prev_y = row["y"]

    out = []
    for block in blocks:
        chars = [c for r in block["rows"] for c in r["chars"]]
        if block["kind"] in ("h1", "h2"):
            for ch in chars:                       # 标题是给人看的，不遮
                ch["ans"] = False
        out.append({"kind": block["kind"], "chars": chars})
    return out


# ---------------------------------------------------------------- 对外接口

def analyze(path: str, progress=None) -> list[dict]:
    """分析 PDF，返回逐页的结构化数据。

    progress: 可选回调 progress(done, total)，用于给界面报进度。
    """
    doc = fitz.open(path)
    body_font, body_size = document_profile(doc)
    # 标题字体：只认这些「一眼就是标题」的字体，绝不把正文字体算进来
    title_fonts = {"SimHei", "MicrosoftYaHei", "SimSun", "STHeiti",
                   "Arial", "Helvetica", "TCXBSJW--GB1-0"}

    heads, feet = detect_running_heads(doc)

    pages = []
    total = doc.page_count
    for i in range(total):
        rows = mark_answer_key(collect_rows(doc[i], body_size, heads, feet))
        blocks = build_blocks(rows, body_size, title_fonts)
        pages.append({"page": i + 1, "blocks": blocks})
        if progress:
            progress(i + 1, total)
    doc.close()
    return pages


def stats(pages: list[dict]) -> dict:
    """统计遮住了多少字，用于给用户反馈。"""
    total = hidden = 0
    for page in pages:
        for block in page["blocks"]:
            for ch in block["chars"]:
                if not ch["c"].strip():
                    continue
                total += 1
                if ch["ans"]:
                    hidden += 1
    return {"total": total, "hidden": hidden,
            "ratio": round(100.0 * hidden / total, 1) if total else 0.0}
