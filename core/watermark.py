"""
水印模块 - 免费版带水印，付费版去水印
"""

import os
import subprocess
from loguru import logger
from core.font_utils import get_ffmpeg_font_filter


def add_watermark(video_path: str, output_path: str,
                  text: str = "AI视频工厂 · 免费版",
                  position: str = "bottom-right") -> str:
    """
    给视频加文字水印
    position: top-left, top-right, bottom-left, bottom-right
    """
    positions = {
        "top-left": "x=20:y=20",
        "top-right": "x=w-tw-20:y=20",
        "bottom-left": "x=20:y=h-th-20",
        "bottom-right": "x=w-tw-20:y=h-th-20",
    }
    pos = positions.get(position, positions["bottom-right"])

    # 只允许安全字符
    import re
    safe_text = re.sub(r'[^\w\s·]', '', text)

    font_filter = get_ffmpeg_font_filter()
    if not font_filter:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", (
            f"drawtext=text='{safe_text}':"
            f"{font_filter}"
            "fontsize=24:fontcolor=white@0.6:"
            f"{pos}:"
            "box=1:boxcolor=black@0.4:boxborderw=8"
        ),
        "-c:v", "libx264", "-c:a", "copy",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if os.path.exists(output_path):
        logger.info(f"水印已添加: {output_path}")
        return output_path

    import shutil
    shutil.copy2(video_path, output_path)
    logger.warning("水印添加失败，返回原视频")
    return output_path


def remove_watermark(video_path: str, output_path: str) -> str:
    """付费版：直接复制（没有水印的原始版本）"""
    import shutil
    shutil.copy2(video_path, output_path)
    return output_path
