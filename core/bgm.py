"""
BGM 模块 - 自动配背景音乐
内置免版权音乐 + 自动调节音量
"""

import os
import random
import subprocess
from loguru import logger

# 免版权 BGM 来源（使用 FFmpeg 合成的简单旋律作为演示）
# 正式版可替换为真实 BGM 文件路径
BGM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bgm")


def ensure_bgm_dir():
    os.makedirs(BGM_DIR, exist_ok=True)
    # 如果没有 BGM 文件，生成几个简单的合成音乐
    bgm_files = [f for f in os.listdir(BGM_DIR) if f.endswith((".mp3", ".wav"))]
    if not bgm_files:
        _generate_demo_bgm()


def _generate_demo_bgm():
    """生成几个简单的演示 BGM"""
    styles = {
        "upbeat": "sine=frequency=440:beep_factor=4",
        "calm": "sine=frequency=330:beep_factor=8",
        "warm": "sine=frequency=392:beep_factor=6",
    }
    for name, source in styles.items():
        path = os.path.join(BGM_DIR, f"{name}.mp3")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"{source}:duration=120",
            "-af", "volume=0.15,afade=t=in:d=2,afade=t=out:st=118:d=2",
            "-c:a", "libmp3lame", "-q:a", "9",
            path,
        ]
        subprocess.run(cmd, capture_output=True)
    logger.info(f"已生成 {len(styles)} 个演示 BGM")


def get_bgm_for_template(template: str) -> str:
    """根据模板选择合适的 BGM"""
    ensure_bgm_dir()
    mapping = {
        "douyin": "upbeat",
        "knowledge": "calm",
        "product": "warm",
        "festival": "upbeat",
    }
    bgm_name = mapping.get(template, "upbeat")
    bgm_path = os.path.join(BGM_DIR, f"{bgm_name}.mp3")
    if os.path.exists(bgm_path):
        return bgm_path
    # fallback
    files = [f for f in os.listdir(BGM_DIR) if f.endswith((".mp3",))]
    if files:
        return os.path.join(BGM_DIR, random.choice(files))
    return ""


def mix_bgm(video_path: str, bgm_path: str, output_path: str,
            bgm_volume: float = 0.15) -> str:
    """
    将 BGM 混入视频，自动降低 BGM 音量，保留人声
    """
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
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip()) if result.stdout.strip() else 30

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex",
        f"[1:a]volume={bgm_volume},afade=t=in:d=2,afade=t=out:st={duration-2}:d=2[bgm];"
        f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(output_path):
        logger.info(f"BGM 混入完成: {output_path}")
        return output_path

    import shutil
    shutil.copy2(video_path, output_path)
    logger.warning("BGM 混入失败，返回原视频")
    return output_path
