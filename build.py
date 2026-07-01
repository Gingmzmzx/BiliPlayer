"""PyInstaller 打包脚本。运行: python build.py"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
APP_NAME = "BiliPlayer"
ENTRY = "main.py"
ICON = "BiliPlayer/resources/logo.png"

DATAS = [
    ("BiliPlayer/templates", "BiliPlayer/templates"),
    ("BiliPlayer/resources", "BiliPlayer/resources"),
]


def clean():
    for d in ["build", "dist", f"{APP_NAME}.spec"]:
        p = PROJECT_ROOT / d
        if p.is_dir():
            shutil.rmtree(p)
        elif p.is_file():
            p.unlink()
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache)


def build():
    clean()

    datas_args = []
    for src, dst in DATAS:
        datas_args.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",
        "--onedir",
        "--clean",
        *datas_args,
    ]

    if sys.platform == "darwin":
        if Path(ICON).exists():
            cmd.extend(["--icon", ICON])
        cmd.extend(["--osx-bundle-identifier", "com.biliplayer.app"])

    if sys.platform == "win32" and Path(ICON).exists():
        cmd.extend(["--icon", ICON])

    for mod in ["tkinter", "matplotlib", "numpy", "pandas", "scipy", "jupyter", "IPython"]:
        cmd.extend(["--exclude-module", mod])

    cmd.append(ENTRY)

    print(f"[build] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
    print(f"\n[build] 完成 -> dist/{APP_NAME}")

    # 复制 Playwright 浏览器
    for base in [
        Path.home() / "Library/Caches/ms-playwright",
        Path.home() / ".cache/ms-playwright",
        Path.home() / "AppData/Local/ms-playwright",
    ]:
        if base.exists():
            app_bundle = PROJECT_ROOT / "dist" / f"{APP_NAME}.app"
            if app_bundle.exists():
                dest = app_bundle / "Contents" / "MacOS" / "ms-playwright"
            else:
                dest = PROJECT_ROOT / "dist" / APP_NAME / "ms-playwright"
            if not dest.exists():
                shutil.copytree(base, dest)
                print(f"[build] 浏览器已打包到 {dest}")
            break


if __name__ == "__main__":
    build()
