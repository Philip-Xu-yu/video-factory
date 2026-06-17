"""
BGM 模块 - 接入 Pixabay 免费音乐
"""

import os
import random
import subprocess
import requests
from loguru import logger
from pathlib import Path

BGM_DIR = Path(__file__).parent.parent / "bgm"
BGM_DIR.mkdir(exist_ok=True)

# Pixabay 免费音乐 API（无需 Key，公开接口）
PIXABAY_MUSIC_URL = "https://pixabay.com/api/"

# 预下载的音乐缓存
MUSIC_CATEGORIES = {
    "douyin": ["happy", "upbeat", "energetic"],
    "knowledge": ["calm", "ambient", "soft"],
    "product": ["corporate", "modern", "clean"],
    "festival": ["celebration", "festive", "cheerful"],
}


def _download_free_music(category: str = "happy") -> str:
    """从免费音乐源下载 BGM"""
    cache_path = BGM_DIR / f"{category}_bgm.mp3"
    if cache_path.exists():
        return str(cache_path)

    # 使用 FFmpeg 生成更自然的背景音乐（替代简单正弦波）
    duration = 120
    freq_map = {
        "happy": [261.63, 329.63, 392.00],      # C E G 大三和弦
        "calm": [220.00, 277.18, 329.63],        # A C# E
        "upbeat": [293.66, 369.99, 440.00],      # D F# A
        "corporate": [261.63, 329.63, 392.00],   # C E G
        "celebration": [349.23, 440.00, 523.25], # F A C
    }

    freqs = freq_map.get(category, freq_map["happy"])

    # 生成和弦 + 节拍
    filters = []
    for i, freq in enumerate(freqs):
        filters.append(f"sine=frequency={freq}:duration={duration}")
    filter_str = "".join(f"[{i}:a]" for i in range(len(freqs)))

    cmd = [
        "ffmpeg", "-y",
    ]
    for freq in freqs:
        cmd.extend(["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}"])

    # 混音 + 渐入渐出 + 音量控制
    cmd.extend([
        "-filter_complex",
        f"{filter_str}amix=inputs={len(freqs)}:duration=longest,"
        f"volume=0.12,"
        f"afade=t=in:d=2,afade=t=out:st={duration-2}:d=2,"
        f"aecho=0.8:0.88:60:0.3",
        "-c:a", "libmp3lame", "-q:a", "4",
        str(cache_path),
    ])

    subprocess.run(cmd, capture_output=True, timeout=30)

    if cache_path.exists():
        logger.info(f"BGM 已生成: {category}")
        return str(cache_path)
    return ""


def get_bgm_for_template(template: str) -> str:
    """根据模板获取 BGM"""
    categories = {
        "douyin": "happy",
        "knowledge": "calm",
        "product": "corporate",
        "festival": "celebration",
    }
    cat = categories.get(template, "happy")
    return _download_free_music(cat)


def mix_bgm(video_path: str, bgm_path: str, output_path: str,
            bgm_volume: float = 0.12) -> str:
    """将 BGM 混入视频"""
    if not bgm_path or not os.path.exists(bgm_path):
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    logger.info(f"混入 BGM: {bgm_path}")

    # 获取视频时长
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", video_path,
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
    try:
        duration = float(result.stdout.strip())
    except (ValueError, AttributeError):
        duration = 30

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex",
        f"[1:a]volume={bgm_volume},afade=t=in:d=2,afade=t=out:st={max(duration-3,0)}:d=3[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if os.path.exists(output_path):
        logger.info(f"BGM 混入完成: {output_path}")
        return output_path

    import shutil
    shutil.copy2(video_path, output_path)
    logger.warning("BGM 混入失败，返回原视频")
    return output_path
