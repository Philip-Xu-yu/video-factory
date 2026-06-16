"""
字体工具 - 自动检测系统字体路径
"""

import os
import platform
from loguru import logger

_font_path = None


def get_font_path() -> str:
    """获取系统中文字体路径"""
    global _font_path
    if _font_path:
        return _font_path

    system = platform.system()

    candidates = []
    if system == "Windows":
        candidates = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/simsun.ttc",
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        ]

    for path in candidates:
        if os.path.exists(path):
            _font_path = path.replace("\\", "/")
            logger.info(f"使用字体: {_font_path}")
            return _font_path

    # 尝试 fc-list 查找
    try:
        import subprocess
        result = subprocess.run(
            ["fc-list", ":lang=zh", "-f", "%{file}\n"],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            _font_path = result.stdout.strip().split("\n")[0]
            return _font_path
    except Exception:
        pass

    logger.warning("未找到中文字体，FFmpeg 文字渲染可能失败")
    return ""


def get_ffmpeg_font_filter() -> str:
    """获取 FFmpeg 字体参数"""
    path = get_font_path()
    if not path:
        return ""
    # FFmpeg 需要转义冒号和反斜杠
    safe = path.replace("\\", "/").replace(":", "\\:")
    return f"fontfile={safe}:"
