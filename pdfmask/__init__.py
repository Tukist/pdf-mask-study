# -*- coding: utf-8 -*-
"""pdf-mask-study —— 把 PDF 复习资料变成「黑幕自测」网页。

它会自动找出原文里自己标出的重点和填空（黑体字、下划线），
把它们遮成黑幕，鼠标悬停才显示答案，方便自测背诵。

用法::

    from pdfmask import convert
    convert("复习资料.pdf")          # 生成 复习资料_背诵版.html
"""

__version__ = "1.3.0"
__all__ = ["analyze", "render", "convert"]

from .analyze import analyze, stats           # noqa: F401
from .render import convert, render, doc_key  # noqa: F401
