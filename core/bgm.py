"""
BGM 模块 - Pexels 免费音乐 + 本地缓存
"""

import os
import random
import subprocess
import requests
from pathlib import Path
from loguru import logger

BGM_DIR = Path(__file__).parent.parent / "bgm"
BGM_DIR.mkdir(exist_ok=True)

# Pexels 免费音乐搜索关键词
BGM_KEYWORDS = {
    "douyin": ["upbeat", "energetic", "pop", "fun"],
    "knowledge": ["calm", "ambient", "soft", "minimal"],
    "product": ["corporate", "modern", "clean", "tech"],
    "festival": ["happy", "celebration", "cheerful", "holiday"],
}

# 音乐缓存
_downloaded = {}


def _search_pexels_music(query: str) -> list[str]:
    """搜索 Pexels 免费音乐"""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": os.environ.get("PEXELS_API_KEY", "")},
            params={"query": query, "per_page": 5},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Pexels 音乐 API 需要付费，这里用视频的音频作为备选
            return []
    except Exception:
        pass
    return []


def _download_free_music(category: str = "happy") -> str:
    """生成自然和弦音乐"""
    cache_path = BGM_DIR / f"{category}_bgm.mp3"
    if cache_path.exists():
        return str(cache_path)

    # 更自然的和弦进行
    chord_progressions = {
        "happy": [
            [261.63, 329.63, 392.00],  # C major
            [293.66, 369.99, 440.00],  # D major
            [349.23, 440.00, 523.25],  # F major
            [392.00, 493.88, 587.33],  # G major
        ],
        "calm": [
            [220.00, 277.18, 329.63],  # A minor
            [246.94, 311.13, 369.99],  # B diminished
            [261.63, 329.63, 392.00],  # C major
            [220.00, 277.18, 329.63],  # A minor
        ],
        "corporate": [
            [261.63, 329.63, 392.00],  # C major
            [349.23, 440.00, 523.25],  # F major
            [392.00, 493.88, 587.33],  # G major
            [261.63, 329.63, 392.00],  # C major
        ],
        "celebration": [
            [349.23, 440.00, 523.25],  # F major
            [392.00, 493.88, 587.33],  # G major
            [440.00, 554.37, 659.25],  # A major
            [349.23, 440.00, 523.25],  # F major
        ],
    }

    progression = chord_progressions.get(category, chord_progressions["happy"])
    duration = 120  # 2 分钟循环

    # 生成每个和弦的音频
    temp_files = []
    for i, chord in enumerate(progression):
        temp_path = BGM_DIR / f"temp_chord_{i}.wav"
        freq_args = []
        for freq in chord:
            freq_args.extend(["-f", "lavfi", "-i", f"sine=frequency={freq}:duration=4"])

        inputs = " ".join(f"[{j}:a]" for j in range(len(chord)))
        cmd = [
            "ffmpeg", "-y",
            *freq_args,
            "-filter_complex",
            f"{inputs}amix=inputs={len(chord)}:duration=longest,volume=0.15",
            "-c:a", "pcm_s16le",
            str(temp_path),
        ]
        subprocess.run(cmd, capture_output=True, timeout=10)
        temp_files.append(temp_path)

    # 拼接和弦 + 循环到指定时长
    concat_list = BGM_DIR / "concat_list.txt"
    with open(concat_list, "w") as f:
        for _ in range(duration // (4 * len(progression)) + 1):
            for tp in temp_files:
                if tp.exists():
                    f.write(f"file '{tp}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-t", str(duration),
        "-af", "afade=t=in:d=2,afade=t=out:st=118:d=2,aecho=0.8:0.88:60:0.3",
        "-c:a", "libmp3lame", "-q:a", "4",
        str(cache_path),
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)

    # 清理临时文件
    for tp in temp_files:
        if tp.exists():
            tp.unlink()
    if concat_list.exists():
        concat_list.unlink()

    if cache_path.exists():
        logger.info(f"BGM 生成: {category}")
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
    return output_path
