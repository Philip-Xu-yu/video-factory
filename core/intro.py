"""
片头片尾模块 - 自动生成品牌片头片尾
"""

import os
import re
import subprocess
from loguru import logger
from core.font_utils import get_ffmpeg_font_filter


def generate_intro(title: str, output_path: str, duration: float = 2.0) -> str:
    """生成片头：黑底 + 白字标题 + 淡入效果"""
    logger.info(f"生成片头: {title}")

    safe_title = re.sub(r'[^\w\s]', '', title)

    font_filter = get_ffmpeg_font_filter()
    if not font_filter:
        return ""

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={duration}",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", (
            f"drawtext=text='{safe_title}':"
            f"{font_filter}"
            "fontsize=60:fontcolor=white:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            f"alpha='if(lt(t,0.5),t*2,if(gt(t,{duration-0.5}),(1-(t-{duration-0.5})*2),1))'"
        ),
        "-shortest",
        "-c:v", "libx264", "-c:a", "aac",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if os.path.exists(output_path):
        logger.info(f"片头生成完成: {output_path}")
        return output_path

    logger.warning("片头生成失败")
    return ""


def generate_outro(output_path: str, duration: float = 2.0) -> str:
    """生成片尾：黑底 + "关注我" + 淡出效果"""
    logger.info("生成片尾")

    outro_text = "关注我 获取更多内容"

    font_filter = get_ffmpeg_font_filter()
    if not font_filter:
        return ""

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={duration}",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", (
            f"drawtext=text='{outro_text}':"
            f"{font_filter}"
            "fontsize=48:fontcolor=white@0.8:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            f"alpha='if(lt(t,0.5),t*2,if(gt(t,{duration-0.5}),(1-(t-{duration-0.5})*2),1))'"
        ),
        "-shortest",
        "-c:v", "libx264", "-c:a", "aac",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if os.path.exists(output_path):
        logger.info(f"片尾生成完成: {output_path}")
        return output_path

    logger.warning("片尾生成失败")
    return ""


def concat_videos(parts: list[str], output_path: str) -> str:
    """拼接多个视频片段"""
    if len(parts) == 1:
        import shutil
        shutil.copy2(parts[0], output_path)
        return output_path

    logger.info(f"拼接 {len(parts)} 个片段")

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in parts:
            if p and os.path.exists(p):
                f.write(f"file '{p.replace(chr(92), '/')}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-c:a", "aac",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if os.path.exists(concat_file):
        os.remove(concat_file)

    if os.path.exists(output_path):
        logger.info(f"拼接完成: {output_path}")
        return output_path

    logger.warning("拼接失败")
    return parts[0] if parts else ""
