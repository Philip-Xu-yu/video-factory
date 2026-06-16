"""
封面模块 - 自动生成视频封面
从视频截帧 + 添加文字
"""

import os
import re
import subprocess
from loguru import logger
from core.font_utils import get_ffmpeg_font_filter


def extract_frame(video_path: str, output_path: str, time_sec: float = 1.0) -> str:
    """从视频截取一帧作为封面底图"""
    logger.info(f"截取封面帧: {time_sec}s")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(time_sec),
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)

    if os.path.exists(output_path):
        logger.info(f"封面帧截取完成: {output_path}")
        return output_path
    return ""


def add_cover_text(image_path: str, output_path: str,
                   main_title: str, sub_title: str = "") -> str:
    """在封面上添加文字"""
    logger.info(f"添加封面文字: {main_title}")

    safe_main = re.sub(r'[^\w\s·！？]', '', main_title)
    safe_sub = re.sub(r'[^\w\s·！？]', '', sub_title)

    font_filter = get_ffmpeg_font_filter()
    if not font_filter:
        import shutil
        shutil.copy2(image_path, output_path)
        return output_path

    filters = [
        "drawbox=x=0:y=ih/3:w=iw:h=ih/3:color=black@0.5:t=fill",
        f"drawtext=text='{safe_main}':"
        f"{font_filter}"
        "fontsize=72:fontcolor=white:"
        "x=(w-text_w)/2:y=(h-text_h)/2-40:"
        "borderw=4:bordercolor=black",
    ]

    if safe_sub:
        filters.append(
            f"drawtext=text='{safe_sub}':"
            f"{font_filter}"
            "fontsize=36:fontcolor=white@0.9:"
            "x=(w-text_w)/2:y=(h/2)+40:"
            "borderw=2:bordercolor=black"
        )

    vf = ",".join(filters)

    cmd = ["ffmpeg", "-y", "-i", image_path, "-vf", vf, output_path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if os.path.exists(output_path):
        logger.info(f"封面生成完成: {output_path}")
        return output_path

    import shutil
    shutil.copy2(image_path, output_path)
    logger.warning("封面文字添加失败，返回原图")
    return output_path


def generate_cover(video_path: str, output_path: str,
                   main_title: str, sub_title: str = "") -> str:
    """一键生成封面：截帧 + 加文字"""
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", video_path,
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
    try:
        duration = float(result.stdout.strip())
    except (ValueError, AttributeError):
        duration = 10
    mid_point = duration / 3

    frame_path = output_path.replace(".jpg", "_frame.jpg")
    extract_frame(video_path, frame_path, mid_point)

    if not os.path.exists(frame_path):
        return ""

    final = add_cover_text(frame_path, output_path, main_title, sub_title)

    if os.path.exists(frame_path) and frame_path != final:
        os.remove(frame_path)

    return final
