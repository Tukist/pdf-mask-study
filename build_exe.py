# -*- coding: utf-8 -*-
"""用 PyInstaller 打包成单文件 exe。

    python build_exe.py            # 只打图形界面版（给普通用户）
    python build_exe.py --all      # 图形界面版 + 命令行版

产物放在 dist/ 目录。需要先 `pip install pyinstaller`。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SEP = ";" if sys.platform.startswith("win") else ":"

COMMON = [
    "--noconfirm", "--clean", "--onefile",
    "--add-data", "pdfmask/assets%sassets" % SEP,
    # 这些用不到，排掉能让 exe 小一圈
    "--exclude-module", "numpy",
    "--exclude-module", "matplotlib",
    "--exclude-module", "PIL",
    "--exclude-module", "pandas",
    "--exclude-module", "setuptools",
]


def build(entry: str, name: str, windowed: bool) -> None:
    args = [sys.executable, "-m", "PyInstaller", *COMMON,
            "--name", name,
            "--windowed" if windowed else "--console",
            entry]
    print("\n>>> " + " ".join(args) + "\n")
    subprocess.check_call(args, cwd=ROOT)


def main() -> int:
    try:
        import PyInstaller                                    # noqa: F401
    except ImportError:
        print("先安装 PyInstaller：pip install pyinstaller", file=sys.stderr)
        return 2
    if sys.version_info < (3, 9):
        print("建议用 Python 3.9 以上", file=sys.stderr)
        return 2

    build("run_gui.py", "pdf-mask-study", windowed=True)

    if "--all" in sys.argv:
        build("run_cli.py", "pdfmask-cli", windowed=False)

    out = os.path.join(ROOT, "dist")
    print("\n打包完成，产物：")
    if os.path.isdir(out):
        for name in sorted(os.listdir(out)):
            path = os.path.join(out, name)
            if os.path.isfile(path):
                print("  %-28s %6.1f MB" % (name, os.path.getsize(path) / 1024 / 1024))
    # PyInstaller 的中间产物没必要留
    for junk in ("build", "__pycache__"):
        shutil.rmtree(os.path.join(ROOT, junk), ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
