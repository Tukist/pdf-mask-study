# -*- coding: utf-8 -*-
"""对示例 PDF 的解析与渲染结果做断言。

运行：  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pdfmask import analyze, doc_key, render, stats          # noqa: E402

SAMPLE = os.path.join(ROOT, "examples", "sample.pdf")


def ensure_sample() -> str:
    """没有示例 PDF 就现场生成一个（示例文件本身不进版本库也没关系）。"""
    if not os.path.isfile(SAMPLE):
        subprocess.check_call([sys.executable,
                               os.path.join(ROOT, "tools", "make_sample.py")])
    return SAMPLE


def hidden_fragments(pages) -> list[str]:
    """把「被遮住的连续文字」抽出来，方便断言。"""
    out = []
    for page in pages:
        for block in page["blocks"]:
            if block["kind"] in ("h1", "h2"):
                continue
            buf = ""
            for ch in block["chars"]:
                if ch["ans"]:
                    buf += ch["c"]
                else:
                    if buf.strip():
                        out.append(buf.strip())
                    buf = ""
            if buf.strip():
                out.append(buf.strip())
    return out


class AnalyzeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_sample()
        cls.pages = analyze(SAMPLE)

    def test_page_count(self):
        self.assertEqual(len(self.pages), 2)

    def test_bold_emphasis_is_masked(self):
        hidden = hidden_fragments(self.pages)
        for expect in ("中国工人阶级的先锋队", "中国人民和中华民族的先锋队",
                       "实现共产主义", "人民代表大会制度"):
            self.assertTrue(any(expect in h for h in hidden),
                            "黑体重点应被遮住：%s（实际遮住 %s）" % (expect, hidden))

    def test_underlined_text_is_masked(self):
        hidden = hidden_fragments(self.pages)
        for expect in ("一切从实际出发", "实践中检验真理和发展真理",
                       "金黄色党徽图案", "密切联系群众", "脱离群众",
                       "1921", "全心全意为人民服务", "民主集中制"):
            self.assertTrue(any(expect in h for h in hidden),
                            "下划线内容应被遮住：%s（实际遮住 %s）" % (expect, hidden))

    def test_titles_are_never_masked(self):
        for page in self.pages:
            for block in page["blocks"]:
                if block["kind"] in ("h1", "h2"):
                    text = "".join(c["c"] for c in block["chars"])
                    self.assertFalse(any(ch["ans"] for ch in block["chars"]),
                                     "标题不该被遮：%s" % text)

    def test_answer_key_letter_is_masked(self):
        hidden = hidden_fragments(self.pages)
        self.assertIn("A", hidden)
        self.assertIn("B", hidden)

    def test_plain_text_stays_visible(self):
        text = "".join(c["c"] for p in self.pages
                       for b in p["blocks"] for c in b["chars"])
        for keep in ("是中国特色社会主义事业的领导核心",
                     "党的最大政治优势是",
                     "党的纪律处分中"):
            self.assertIn(keep, text)
            self.assertFalse(any(keep in h for h in hidden_fragments(self.pages)),
                             "普通正文不该被遮：%s" % keep)

    def test_stats_in_reasonable_range(self):
        info = stats(self.pages)
        self.assertGreater(info["total"], 300)
        self.assertGreater(info["hidden"], 50)
        self.assertLess(info["ratio"], 60.0)

    def test_text_is_lossless(self):
        """分析不能丢字：拼回来的文本要和 PDF 直接提取的一致。"""
        import fitz
        doc = fitz.open(SAMPLE)
        raw = "".join(doc[i].get_text() for i in range(doc.page_count))
        doc.close()
        got = "".join(c["c"] for p in self.pages
                      for b in p["blocks"] for c in b["chars"])
        norm = lambda s: re.sub(r"\s+", "", s)                # noqa: E731
        self.assertEqual(norm(raw), norm(got))


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_sample()
        cls.pages = analyze(SAMPLE)

    def test_html_contains_interactions(self):
        html = render(self.pages, "测试标题", "")
        for token in ('<b class="b">', 'canvas.ink', 'id="penBtn"', 'id="undoInk"',
                      'id="exp"', "Ctrl+Z", "pdfmask-notes::", "pdfmask-ink::",
                      "pdfmask-mask::", 'data-b="', "selmenu", "readBlock", "applyOverrides"):
            self.assertIn(token, html, "生成的 HTML 缺少：%s" % token)

    def test_every_block_has_index(self):
        """每个正文块都要带 data-b，否则「划选涂黑」定位不到段落。"""
        html = render(self.pages, "t", "")
        body = html.split("<main>")[1].split("</main>")[0]
        paras = re.findall(r'<p data-b="\d+">', body)
        heads = re.findall(r'<h[12] class="t" data-b="\d+">', body)
        self.assertGreater(len(paras) + len(heads), 5)
        # 不带 data-b 的 <p> 不该存在
        plain = re.findall(r"<p>", body)
        self.assertEqual(plain, [], "有段落漏了 data-b")

    def test_title_and_placeholders_are_filled(self):
        html = render(self.pages, "我的资料", "页脚示例")
        self.assertIn("我的资料", html)
        self.assertIn("页脚示例", html)
        self.assertNotIn("__BODY__", html)
        self.assertNotIn("__TITLE__", html)
        self.assertNotIn("__DOCKEY__", html)

    def test_rendered_text_matches_analysis(self):
        html = render(self.pages, "t", "")
        body = html.split("<main>")[1].split("</main>")[0]
        body = re.sub(r'<span class="pn">.*?</span>', "", body)      # 页码不是原文
        import html as html_mod
        got = html_mod.unescape(re.sub(r"<[^>]+>", "", body))
        want = "".join(c["c"] for p in self.pages
                       for b in p["blocks"] for c in b["chars"])
        norm = lambda s: re.sub(r"\s+", "", s)                # noqa: E731
        self.assertEqual(norm(want), norm(got))

    def test_doc_key_is_stable_and_distinct(self):
        a1 = doc_key("甲", self.pages)
        a2 = doc_key("甲", self.pages)
        b = doc_key("乙", self.pages)
        self.assertEqual(a1, a2, "同一份资料每次算出的 key 必须一样")
        self.assertNotEqual(a1, b, "不同标题应该得到不同的 key")


if __name__ == "__main__":
    unittest.main(verbosity=2)
