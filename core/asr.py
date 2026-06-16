"""
ASR 模块 - 语音转文字
使用 faster-whisper（轻量，适合快速启动）
后续可替换为 FunASR（更准）
"""

from faster_whisper import WhisperModel
from loguru import logger
import os

# 模型缓存
_model = None


def get_model(model_size: str = "base") -> WhisperModel:
    global _model
    if _model is None:
        logger.info(f"加载 ASR 模型: {model_size}")
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model


def transcribe(video_path: str, model_size: str = "base") -> list[dict]:
    """
    转录音频，返回带时间戳的文字列表
    返回: [{"start": 0.0, "end": 2.5, "text": "大家好"}, ...]
    """
    model = get_model(model_size)
    segments, info = model.transcribe(video_path, beam_size=5, language="zh")

    result = []
    for seg in segments:
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })

    logger.info(f"转录完成: {len(result)} 段, 语言: {info.language}")
    return result
