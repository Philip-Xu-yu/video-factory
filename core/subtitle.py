"""
字幕模块 - 生成字幕 + 烧录到视频
"""

import subprocess
import os
from loguru import logger


def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(segments: list[dict], output_path: str) -> str:
    """生成 SRT 字幕文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = format_srt_time(seg["start"])
            end = format_srt_time(seg["end"])
            f.write(f"{i}\n{start} --> {end}\n{seg['text']}\n\n")
    logger.info(f"SRT 生成: {output_path}")
    return output_path


def burn_subtitles(video_path: str, srt_path: str, output_path: str,
                   style: str = "tiktok") -> str:
    """
    将字幕烧录到视频
    style: tiktok(抖音黄字), default(通用白字), minimal(简约白字)
    """
    logger.info(f"烧录字幕: {video_path}")

    styles = {
        "tiktok": "FontName=Microsoft YaHei,FontSize=28,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,Outline=3,Bold=1,Alignment=5,MarginV=0",
        "default": "FontName=Microsoft YaHei,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=30",
        "minimal": "FontName=Microsoft YaHei,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,Outline=1,Alignment=2,MarginV=50",
    }

    force_style = styles.get(style, styles["tiktok"])
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"subtitles='{srt_escaped}':force_style='{force_style}'",
        "-c:a", "copy",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if os.path.exists(output_path):
        logger.info(f"字幕烧录完成: {output_path}")
        return output_path

    # 失败则复制原文件
    import shutil
    shutil.copy2(video_path, output_path)
    logger.warning("字幕烧录失败，返回无字幕版本")
    return output_path
