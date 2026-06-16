"""
视频工厂主流程 v3 - 全自动出片
新增: 文案提取 + 仿写 + 标题生成 + 封面生成
"""

import os
import uuid
import time
import shutil
import subprocess
from pathlib import Path
from loguru import logger

from core.asr import transcribe
from core.tts import text_to_speech
from core.voice_clone import voice_clone
from core.editor import remove_silence, crop_vertical
from core.subtitle import generate_srt, burn_subtitles
from core.bgm import get_bgm_for_template, mix_bgm
from core.intro import generate_intro, generate_outro, concat_videos
from core.templates import get_template
from core.copywriter import extract_copy, rewrite_copy, generate_title, generate_cover_text
from core.cover import generate_cover


def create_task_dir(base_dir: str) -> str:
    task_id = str(uuid.uuid4())[:8]
    task_dir = os.path.join(base_dir, task_id)
    os.makedirs(task_dir, exist_ok=True)
    return task_dir


def process_video(input_path: str, template: str, output_dir: str,
                  voice: str = "xiaoxiao", progress_callback=None) -> dict:
    """
    全自动视频处理流程 v3
    """
    start = time.time()
    task_dir = create_task_dir(output_dir)
    base = Path(input_path).stem
    tmpl = get_template(template)

    def report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        logger.info(f"[{pct}%] {msg}")

    # 1. 语音识别
    report(5, "🎙️ 正在识别语音...")
    segments = transcribe(input_path, model_size="base")
    if not segments:
        return {"error": "未检测到语音内容"}

    # 2. 提取文案
    report(15, "📝 提取核心文案...")
    full_text = " ".join([s["text"] for s in segments])
    copy = extract_copy(full_text)

    # 3. AI 仿写
    report(20, "✍️ AI 优化文案...")
    final_copy = rewrite_copy(copy, template)

    # 4. 生成标题
    report(25, "📌 生成视频标题...")
    title = generate_title(final_copy, template)

    # 5. 生成封面文字
    report(28, "🎨 生成封面文字...")
    cover_info = generate_cover_text(final_copy)

    # 6. 生成字幕
    report(30, "📝 生成字幕...")
    srt_path = os.path.join(task_dir, f"{base}.srt")
    generate_srt(segments, srt_path)

    # 7. 去静音
    if tmpl["remove_silence"]:
        report(40, "🔇 去除静音...")
        edited_path = os.path.join(task_dir, f"{base}_edited.mp4")
        remove_silence(input_path, edited_path)
    else:
        edited_path = input_path
        report(40, "⏭️ 跳过去静音")

    # 8. 裁剪竖屏
    report(50, "📐 裁剪 9:16...")
    cropped_path = os.path.join(task_dir, f"{base}_cropped.mp4")
    crop_vertical(edited_path, cropped_path)

    # 9. 烧录字幕
    report(60, "📝 烧录字幕...")
    subtitled_path = os.path.join(task_dir, f"{base}_subtitled.mp4")
    burn_subtitles(cropped_path, srt_path, subtitled_path, style=tmpl["subtitle_style"])

    # 10. 混入 BGM
    report(70, "🎵 添加背景音乐...")
    bgm_path = get_bgm_for_template(template)
    with_bgm_path = os.path.join(task_dir, f"{base}_bgm.mp4")
    mix_bgm(subtitled_path, bgm_path, with_bgm_path)

    # 11. 生成封面
    report(80, "🎨 生成封面...")
    cover_path = os.path.join(task_dir, f"{base}_cover.jpg")
    generate_cover(with_bgm_path, cover_path, cover_info["main"], cover_info["sub"])

    # 12. 片头片尾
    report(88, "🎬 添加片头片尾...")
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
    report(100, "✅ 完成!")

    return {
        "task_id": os.path.basename(task_dir),
        "output_path": final_path,
        "srt_path": srt_path,
        "cover_path": cover_path if os.path.exists(cover_path) else "",
        "title": title,
        "copy": final_copy,
        "duration": segments[-1]["end"] if segments else 0,
        "segment_count": len(segments),
        "elapsed": round(elapsed, 1),
        "template": template,
    }


def process_text_to_video(text: str, template: str, output_dir: str,
                          voice: str = "xiaoxiao", progress_callback=None) -> dict:
    """
    文字转视频 v3
    """
    start = time.time()
    task_dir = create_task_dir(output_dir)
    tmpl = get_template(template)

    def report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        logger.info(f"[{pct}%] {msg}")

    # 1. AI 优化文案
    report(10, "✍️ AI 优化文案...")
    final_copy = rewrite_copy(text, template)

    # 2. 生成标题
    report(15, "📌 生成标题...")
    title = generate_title(final_copy, template)

    # 3. 生成封面文字
    report(18, "🎨 生成封面文字...")
    cover_info = generate_cover_text(final_copy)

    # 4. 声音克隆/合成
    report(25, "🎙️ 生成语音...")
    audio_path = os.path.join(task_dir, "tts_audio.mp3")
    voice_clone(final_copy, voice_style="温柔女声", output_path=audio_path)

    # 5. 获取时长，生成黑底视频
    report(35, "🎬 生成视频...")
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", audio_path,
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip()) if result.stdout.strip() else 10

    video_path = os.path.join(task_dir, "tts_video.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={duration}",
        "-i", audio_path,
        "-shortest",
        "-c:v", "libx264", "-c:a", "aac",
        video_path,
    ]
    subprocess.run(cmd, capture_output=True)

    # 6. 识别字幕
    report(45, "📝 识别字幕...")
    segments = transcribe(video_path, model_size="base")
    srt_path = os.path.join(task_dir, "subtitles.srt")
    generate_srt(segments, srt_path)

    # 7. 烧录字幕
    report(60, "📝 烧录字幕...")
    subtitled_path = os.path.join(task_dir, "subtitled.mp4")
    burn_subtitles(video_path, srt_path, subtitled_path, style=tmpl["subtitle_style"])

    # 8. 混入 BGM
    report(70, "🎵 添加背景音乐...")
    bgm_path = get_bgm_for_template(template)
    with_bgm_path = os.path.join(task_dir, "bgm.mp4")
    mix_bgm(subtitled_path, bgm_path, with_bgm_path)

    # 9. 生成封面
    report(78, "🎨 生成封面...")
    cover_path = os.path.join(task_dir, "cover.jpg")
    generate_cover(with_bgm_path, cover_path, cover_info["main"], cover_info["sub"])

    # 10. 片头片尾
    report(85, "🎬 添加片头片尾...")
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
    report(100, "✅ 完成!")

    return {
        "task_id": os.path.basename(task_dir),
        "output_path": final_path,
        "srt_path": srt_path,
        "cover_path": cover_path if os.path.exists(cover_path) else "",
        "title": title,
        "copy": final_copy,
        "duration": round(duration, 1),
        "segment_count": len(segments),
        "elapsed": round(elapsed, 1),
        "template": template,
    }
