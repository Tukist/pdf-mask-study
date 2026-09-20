# -*- coding: utf-8 -*-
"""程序入口（命令行版）。可以 `python run_cli.py 资料.pdf`，也用于打包 CLI 版 exe。"""

import sys

from pdfmask.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
