"""
ASR 模块 - 语音转文字（GPU 加速）
使用 faster-whisper + CUDA
"""

import threading
from faster_whisper import WhisperModel
from loguru import logger

# 模型缓存（线程安全）
_model = None
_model_lock = threading.Lock()
_model_size = None


def get_model(model_size: str = "base") -> WhisperModel:
    global _model, _model_size
    with _model_lock:
        if _model is None or _model_size != model_size:
            # 优先 GPU，降级 CPU
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute = "float16" if device == "cuda" else "int8"
            except ImportError:
                device = "cpu"
                compute = "int8"

            logger.info(f"加载 ASR 模型: {model_size} | 设备: {device} | 精度: {compute}")
            _model = WhisperModel(model_size, device=device, compute_type=compute)
            _model_size = model_size
    return _model


def transcribe(video_path: str, model_size: str = "base") -> list[dict]:
    """
    转录音频，返回带时间戳的文字列表
    返回: [{"start": 0.0, "end": 2.5, "text": "大家好"}, ...]
    """
    model = get_model(model_size)
    segments, info = model.transcribe(
        video_path,
        beam_size=5,
        language="zh",
        vad_filter=True,        # 自动过滤静音段
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    result = []
    for seg in segments:
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })

    logger.info(f"转录完成: {len(result)} 段, 语言: {info.language}")
    return result
