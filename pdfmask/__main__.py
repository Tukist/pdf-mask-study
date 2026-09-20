# -*- coding: utf-8 -*-
"""让 `python -m pdfmask 文件.pdf` 也能用。"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
