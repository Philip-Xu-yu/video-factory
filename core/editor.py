"""
自动剪辑模块 - 去静音 + 裁剪
"""

import subprocess
import sys
import os
from loguru import logger


def remove_silence(video_path: str, output_path: str,
                   silence_threshold: float = -35,
                   min_silence: float = 0.5) -> str:
    """
    去除视频中的静音片段
    """
    logger.info(f"去静音: {video_path}")

    cmd = [
        sys.executable, "-m", "auto_editor",
        video_path,
        "--output", output_path,
        "--margin", "0.1s",
        "--silence-threshold", f"{silence_threshold}dB",
        "--minimum-silence", f"{min_silence}s",
        "--video-codec", "libx264",
        "--audio-codec", "aac",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.warning(f"auto-editor 失败: {result.stderr[:200]}")

    if os.path.exists(output_path):
        logger.info(f"去静音完成: {output_path}")
        return output_path

    # 查找 auto-editor 实际输出
    base = os.path.splitext(video_path)[0]
    for f in os.listdir(os.path.dirname(output_path)):
        if f.startswith(os.path.basename(base)) and f.endswith(".mp4"):
            actual = os.path.join(os.path.dirname(output_path), f)
            if actual != output_path:
                os.rename(actual, output_path)
                return output_path

    logger.warning("去静音失败，返回原文件")
    return video_path


def crop_vertical(video_path: str, output_path: str) -> str:
    """
    裁剪为 9:16 竖屏（从中心裁剪）
    """
    logger.info(f"裁剪竖屏: {video_path}")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", "crop=ih*9/16:ih",
        "-c:v", "libx264", "-c:a", "copy",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        logger.warning(f"裁剪失败: {result.stderr[:200]}")

    if os.path.exists(output_path):
        logger.info(f"裁剪完成: {output_path}")
        return output_path

    logger.warning("裁剪失败，返回原文件")
    return video_path
