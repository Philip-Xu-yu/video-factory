"""
视频工厂主流程 v4 - 优化版
优化: LLM 1次调用 + GPU 加速 + 实时进度 + 历史记录 + 素材匹配
"""

import os
import uuid
import time
import shutil
import subprocess
from pathlib import Path
from loguru import logger

from core.asr import transcribe
from core.voice_clone import voice_clone
from core.history import add_history
from core.editor import remove_silence, crop_vertical
from core.subtitle import generate_srt, burn_subtitles
from core.bgm import get_bgm_for_template, mix_bgm
from core.intro import generate_intro, generate_outro, concat_videos
from core.templates import get_template
from core.copywriter import generate_all_copy
from core.cover import generate_cover


def create_task_dir(base_dir: str) -> str:
    task_id = str(uuid.uuid4())[:8]
    task_dir = os.path.join(base_dir, task_id)
    os.makedirs(task_dir, exist_ok=True)
    return task_dir


def _report(pct: int, msg: str, callback):
    if callback:
        callback(pct, msg)
    logger.info(f"[{pct}%] {msg}")


def process_video(input_path: str, template: str, output_dir: str,
                  voice: str = "xiaoxiao", progress_callback=None) -> dict:
    """全自动视频处理流程 v4"""
    start = time.time()
    task_dir = create_task_dir(output_dir)
    base = Path(input_path).stem
    tmpl = get_template(template)

    # 1. 语音识别（GPU 加速）
    _report(5, "🎙️ GPU 语音识别...", progress_callback)
    segments = transcribe(input_path, model_size="base")
    if not segments:
        return {"error": "未检测到语音内容"}

    full_text = " ".join([s["text"] for s in segments])

    # 2. 一次 LLM 调用生成所有文案
    _report(15, "✍️ AI 生成文案/标题/封面...", progress_callback)
    copy_data = generate_all_copy(full_text, template)

    # 3. 生成字幕
    _report(30, "📝 生成字幕...", progress_callback)
    srt_path = os.path.join(task_dir, f"{base}.srt")
    generate_srt(segments, srt_path)

    # 4. 去静音
    if tmpl["remove_silence"]:
        _report(40, "🔇 去除静音...", progress_callback)
        edited_path = os.path.join(task_dir, f"{base}_edited.mp4")
        remove_silence(input_path, edited_path)
    else:
        edited_path = input_path
        _report(40, "⏭️ 跳过去静音", progress_callback)

    # 5. 裁剪竖屏
    _report(50, "📐 裁剪 9:16...", progress_callback)
    cropped_path = os.path.join(task_dir, f"{base}_cropped.mp4")
    crop_vertical(edited_path, cropped_path)

    # 6. 烧录字幕
    _report(60, "📝 烧录字幕...", progress_callback)
    subtitled_path = os.path.join(task_dir, f"{base}_subtitled.mp4")
    burn_subtitles(cropped_path, srt_path, subtitled_path, style=tmpl["subtitle_style"])

    # 7. 混入 BGM
    _report(70, "🎵 添加音乐...", progress_callback)
    bgm_path = get_bgm_for_template(template)
    with_bgm_path = os.path.join(task_dir, f"{base}_bgm.mp4")
    mix_bgm(subtitled_path, bgm_path, with_bgm_path)

    # 8. 生成封面
    _report(80, "🎨 生成封面...", progress_callback)
    cover_path = os.path.join(task_dir, f"{base}_cover.jpg")
    generate_cover(with_bgm_path, cover_path, copy_data["cover_main"], copy_data["cover_sub"])

    # 9. 片头片尾 + 拼接
    _report(88, "🎬 拼接成品...", progress_callback)
    intro_path = os.path.join(task_dir, "intro.mp4")
    outro_path = os.path.join(task_dir, "outro.mp4")
    final_path = os.path.join(task_dir, f"{base}_final.mp4")

    generate_intro("AI 视频工厂", intro_path)
    generate_outro(outro_path)

    parts = [p for p in [intro_path, with_bgm_path, outro_path] if p and os.path.exists(p)]
    concat_videos(parts, final_path)

    # 清理中间文件
    for f in [edited_path, cropped_path, subtitled_path, with_bgm_path, intro_path, outro_path]:
        if os.path.exists(f) and f != final_path:
            os.remove(f)

    elapsed = time.time() - start
    _report(100, f"✅ 完成! 耗时 {elapsed:.0f}秒", progress_callback)

    task_id = os.path.basename(task_dir)
    add_history({
        "task_id": task_id, "type": "video", "template": template,
        "title": copy_data.get("title", ""), "duration": 0,
        "elapsed": round(elapsed, 1), "output_path": final_path,
    })

    return {
        "task_id": task_id,
        "output_path": final_path,
        "srt_path": srt_path,
        "cover_path": cover_path if os.path.exists(cover_path) else "",
        "title": copy_data["title"],
        "copy": copy_data["copy"],
        "duration": segments[-1]["end"] if segments else 0,
        "segment_count": len(segments),
        "elapsed": round(elapsed, 1),
        "template": template,
    }


def process_text_to_video(text: str, template: str, output_dir: str,
                          voice: str = "xiaoxiao", progress_callback=None) -> dict:
    """文字转视频 v4"""
    start = time.time()
    task_dir = create_task_dir(output_dir)
    tmpl = get_template(template)

    # 1. 一次 LLM 生成所有文案
    _report(10, "✍️ AI 优化文案...", progress_callback)
    copy_data = generate_all_copy(text, template)
    final_copy = copy_data["copy"]

    # 2. 声音克隆
    _report(25, "🎙️ 声音合成...", progress_callback)
    audio_path = os.path.join(task_dir, "tts_audio.mp3")
    voice_clone(final_copy, voice_style="温柔女声", output_path=audio_path)

    # 3. 生成黑底视频
    _report(40, "🎬 生成视频...", progress_callback)
    probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", audio_path]
    result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
    try:
        duration = float(result.stdout.strip())
    except (ValueError, AttributeError):
        duration = 10

    video_path = os.path.join(task_dir, "tts_video.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={duration}",
        "-i", audio_path,
        "-shortest",
        "-c:v", "libx264", "-c:a", "aac",
        video_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)

    # 4. 识别字幕
    _report(50, "📝 识别字幕...", progress_callback)
    segments = transcribe(video_path, model_size="base")
    srt_path = os.path.join(task_dir, "subtitles.srt")
    generate_srt(segments, srt_path)

    # 5. 烧录字幕
    _report(60, "📝 烧录字幕...", progress_callback)
    subtitled_path = os.path.join(task_dir, "subtitled.mp4")
    burn_subtitles(video_path, srt_path, subtitled_path, style=tmpl["subtitle_style"])

    # 6. 混入 BGM
    _report(70, "🎵 添加音乐...", progress_callback)
    bgm_path = get_bgm_for_template(template)
    with_bgm_path = os.path.join(task_dir, "bgm.mp4")
    mix_bgm(subtitled_path, bgm_path, with_bgm_path)

    # 7. 生成封面
    _report(78, "🎨 生成封面...", progress_callback)
    cover_path = os.path.join(task_dir, "cover.jpg")
    generate_cover(with_bgm_path, cover_path, copy_data["cover_main"], copy_data["cover_sub"])

    # 8. 片头片尾
    _report(85, "🎬 拼接成品...", progress_callback)
    intro_path = os.path.join(task_dir, "intro.mp4")
    outro_path = os.path.join(task_dir, "outro.mp4")
    final_path = os.path.join(task_dir, "final.mp4")

    generate_intro("AI 视频工厂", intro_path)
    generate_outro(outro_path)

    parts = [p for p in [intro_path, with_bgm_path, outro_path] if p and os.path.exists(p)]
    concat_videos(parts, final_path)

    # 清理
    for f in [video_path, subtitled_path, with_bgm_path, intro_path, outro_path, audio_path]:
        if os.path.exists(f) and f != final_path:
            os.remove(f)

    elapsed = time.time() - start
    _report(100, f"✅ 完成! 耗时 {elapsed:.0f}秒", progress_callback)

    task_id = os.path.basename(task_dir)
    add_history({
        "task_id": task_id, "type": "video", "template": template,
        "title": copy_data.get("title", ""), "duration": 0,
        "elapsed": round(elapsed, 1), "output_path": final_path,
    })

    return {
        "task_id": task_id,
        "output_path": final_path,
        "srt_path": srt_path,
        "cover_path": cover_path if os.path.exists(cover_path) else "",
        "title": copy_data["title"],
        "copy": copy_data["copy"],
        "duration": round(duration, 1),
        "segment_count": len(segments),
        "elapsed": round(elapsed, 1),
        "template": template,
    }
