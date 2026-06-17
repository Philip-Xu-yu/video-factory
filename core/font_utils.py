"""
字体工具 - 自动检测 + 自动下载
"""

import os
import platform
import subprocess
import requests
from pathlib import Path
from loguru import logger

_font_path = None
FONT_DIR = Path(__file__).parent.parent / "fonts"
FONT_DIR.mkdir(exist_ok=True)

# 免费中文字体下载地址
FONT_URLS = {
    "NotoSansSC-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
}


def _download_font():
    """下载免费中文字体"""
    for name, url in FONT_URLS.items():
        target = FONT_DIR / name
        if target.exists():
            continue
        logger.info(f"下载字体: {name}")
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            target.write_bytes(resp.content)
            logger.info(f"字体下载完成: {target}")
        except Exception as e:
            logger.warning(f"字体下载失败: {e}")


def get_font_path() -> str:
    """获取系统中文字体路径"""
    global _font_path
    if _font_path:
        return _font_path

    # 1. 检查本地 fonts 目录
    for f in FONT_DIR.iterdir():
        if f.suffix.lower() in (".ttf", ".otf", ".ttc"):
            _font_path = str(f)
            return _font_path

    # 2. 检查系统字体
    system = platform.system()
    candidates = []
    if system == "Windows":
        candidates = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/simsun.ttc",
        ]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        ]

    for path in candidates:
        if os.path.exists(path):
            _font_path = path.replace("\\", "/")
            return _font_path

    # 3. 尝试 fc-list
    try:
        result = subprocess.run(
            ["fc-list", ":lang=zh", "-f", "%{file}\n"],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            _font_path = result.stdout.strip().split("\n")[0]
            return _font_path
    except Exception:
        pass

    # 4. 下载字体
    try:
        import requests
        _download_font()
        for f in FONT_DIR.iterdir():
            if f.suffix.lower() in (".ttf", ".otf", ".ttc"):
                _font_path = str(f)
                return _font_path
    except Exception:
        pass

    logger.warning("未找到中文字体")
    return ""


def get_ffmpeg_font_filter() -> str:
    """获取 FFmpeg 字体参数"""
    path = get_font_path()
    if not path:
        return ""
    safe = path.replace("\\", "/").replace(":", "\\:")
    return f"fontfile={safe}:"
