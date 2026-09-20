# -*- coding: utf-8 -*-
"""生成用于演示和测试的示例 PDF（examples/sample.pdf）。

内容全部是公开的党史常识，不含任何真实资料；排版刻意模仿常见的
「复习资料」样式：正文用仿宋，重点句换黑体，填空处画下划线。
"""

from __future__ import annotations

import os
import sys

import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "examples", "sample.pdf")

# 常见中文字体，按平台挑一个能用的
FONT_CANDIDATES = {
    "body": [r"C:\Windows\Fonts\simfang.ttf", r"C:\Windows\Fonts\simsun.ttc",
             "/System/Library/Fonts/Supplemental/Songti.ttc",
             "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"],
    "bold": [r"C:\Windows\Fonts\simhei.ttf",
             "/System/Library/Fonts/Supplemental/Heiti.ttc",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"],
}


def pick_font(kind: str) -> str:
    for path in FONT_CANDIDATES[kind]:
        if os.path.isfile(path):
            return path
    raise SystemExit("找不到可用的中文字体（%s），无法生成示例 PDF" % kind)


BODY = pick_font("body")
BOLD = pick_font("bold")
F_BODY = fitz.Font(fontfile=BODY)
F_BOLD = fitz.Font(fontfile=BOLD)
SIZE = 13.6
LEAD = 28.0          # 行距
LEFT = 72.0


class Sheet:
    """一页纸 + 逐行排版的游标。"""

    def __init__(self, doc, top=90.0):
        self.page = doc.new_page()          # A4
        self.page.insert_font(fontname="body", fontfile=BODY)
        self.page.insert_font(fontname="bold", fontfile=BOLD)
        self.y = top

    def line(self, segments, size=SIZE, indent=0.0):
        """segments: [(文本, 'body'|'bold'|'u'|'u-bold'), ...] 画在一行上。"""
        x = LEFT + indent
        y = self.y
        for text, style in segments:
            bold = style.endswith("bold")
            name = "bold" if bold else "body"
            font = F_BOLD if bold else F_BODY
            self.page.insert_text((x, y), text, fontname=name, fontsize=size, color=(0, 0, 0))
            width = font.text_length(text, size)
            if style.startswith("u"):       # 画在字下方
                self.page.draw_line(fitz.Point(x, y + 2.5), fitz.Point(x + width, y + 2.5),
                                    color=(0, 0, 0), width=0.6)
            x += width
        self.y += LEAD

    def blank(self):
        self.y += LEAD * 0.4

    def title(self, text, size=15.9):
        width = F_BOLD.text_length(text, size)
        self.page.insert_text(((595 - width) / 2, self.y), text,
                              fontname="bold", fontsize=size, color=(0, 0, 0))
        self.y += LEAD * 1.3


def wrap(text: str, limit: int = 33) -> list[str]:
    return [text[i:i + limit] for i in range(0, len(text), limit)]


def main() -> None:
    doc = fitz.open()

    # ---------------- 第 1 页：知识点（黑体重点 + 下划线答案）
    s = Sheet(doc)
    s.title("党的基础知识学习资料（示例）")
    s.blank()
    s.line([("一、党的性质与目标", "bold")])
    s.blank()
    s.line([("1. 中国共产党是", "body"), ("中国工人阶级的先锋队", "bold"),
            ("，同时是", "body"), ("中国人民和中华民族的先锋队", "bold"), ("，", "body")])
    s.line([("是中国特色社会主义事业的领导核心。党的最高理想和最终目标", "body")])
    s.line([("是", "body"), ("实现共产主义", "bold"), ("。", "body")])
    s.blank()
    s.line([("2. 我国的根本政治制度是", "body"), ("人民代表大会制度", "bold"),
            ("，基本政治制度包括", "body")])
    s.line([("中国共产党领导的多党合作和政治协商制度、民族区域自治制度以", "body")])
    s.line([("及基层群众自治制度。", "body")])
    s.blank()
    s.line([("3. 党的思想路线是", "body"), ("一切从实际出发，理论联系实际，实事求是，", "u"),
            ("在", "body")])
    s.line([("实践中检验真理和发展真理", "u"), ("。", "body")])
    s.blank()
    s.line([("4. 中国共产党的党旗是旗面缀有 ", "body"), ("金黄色党徽图案", "u"),
            (" 的红旗。", "body")])
    s.line([("5. 党的最大政治优势是 ", "body"), ("密切联系群众", "u"),
            (" ，执政后的最大危险是 ", "body"), ("脱离群众", "u"), (" 。", "body")])

    # ---------------- 第 2 页：练习题（填空 + 选择题）
    s = Sheet(doc)
    s.title("练习题")
    s.blank()
    s.line([("一、填空题", "bold")])
    s.blank()
    s.line([("1. 中国共产党第一次全国代表大会于 ", "body"), ("1921", "u"),
            (" 年 ", "body"), ("7", "u"), (" 月在上海召开。", "body")])
    s.line([("2. 党的宗旨是 ", "body"), ("全心全意为人民服务", "u"), (" 。", "body")])
    s.line([("3. 党的组织原则是 ", "body"), ("民主集中制", "u"), (" 。", "body")])
    s.blank()
    s.line([("二、选择题", "bold")])
    s.blank()
    s.line([("1. 党的纪律处分中，最轻的一种是（　　）", "body")])
    s.line([("A. 警告　　　　B. 严重警告", "body")], indent=26)
    s.line([("C. 撤销党内职务　D. 留党察看", "body")], indent=26)
    s.line([("【答案】A", "body")], indent=26)
    s.blank()
    s.line([("2. 下列说法中，符合党章规定的是（　　）", "body")])
    s.line([("A. 党员可以不参加党的组织生活", "body")], indent=26)
    s.line([("B. 党员必须履行党员义务，遵守党的纪律", "body")], indent=26)
    s.line([("C. 党员可以自行决定是否缴纳党费", "body")], indent=26)
    s.line([("【答案】B", "body")], indent=26)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    try:
        doc.subset_fonts()          # 只嵌入用到的字，不然动辄十几 MB
    except Exception:               # noqa: BLE001
        pass
    doc.save(OUT, deflate=True, garbage=4)
    doc.close()
    size_kb = os.path.getsize(OUT) / 1024
    print("已生成示例 PDF：%s（%.1f KB，2 页）" % (OUT, size_kb))


if __name__ == "__main__":
    sys.exit(main())
