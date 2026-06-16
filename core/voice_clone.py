"""
声音克隆模块 - 多后端支持
1. Fish Audio API（在线，效果最好）
2. edge-tts（本地免费，效果一般）
3. GPT-SoVITS（本地 GPU，效果最好，待集成）
"""

import os
import requests
from loguru import logger

# Fish Audio API（免费额度 10000 字符/月）
FISH_API_URL = "https://api.fish.audio/v1/tts"
FISH_API_KEY = os.environ.get("FISH_API_KEY", "")

# 预设声音模型（Fish Audio 上的公开模型）
FISH_VOICES = {
    "温柔女声": "7f92bb84-1295-423e-b8f0-a13135b22c61",
    "新闻播报": "83b132a5-e3db-46c6-b858-04e530d03e4f",
    "活泼女声": "2c5c931a-1ad3-493e-a77a-af86da7c1524",
    "沉稳男声": "f083f88a-5188-421f-b210-d99a1c87d21e",
}


def clone_with_fish(text: str, voice_id: str, output_path: str) -> str:
    """Fish Audio API 声音克隆"""
    if not FISH_API_KEY:
        logger.warning("Fish Audio API Key 未设置，使用 edge-tts 替代")
        return clone_with_edge_tts(text, "xiaoxiao", output_path)

    logger.info(f"Fish Audio TTS: {voice_id}")

    headers = {
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "text": text,
        "reference_id": voice_id,
        "format": "mp3",
        "mp3_bitrate": 128,
    }

    try:
        resp = requests.post(FISH_API_URL, json=data, headers=headers, timeout=60)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        logger.info(f"Fish Audio TTS 完成: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Fish Audio TTS 失败: {e}")
        return clone_with_edge_tts(text, "xiaoxiao", output_path)


def clone_with_edge_tts(text: str, voice: str, output_path: str) -> str:
    """edge-tts 免费 TTS（降级方案）"""
    from core.tts import text_to_speech
    return text_to_speech(text, output_path, voice)


def voice_clone(text: str, voice_style: str = "温柔女声",
                method: str = "auto", output_path: str = "output.mp3") -> str:
    """
    声音克隆统一接口
    method: auto / fish / edge / gptsovits
    """
    if method == "fish" or (method == "auto" and FISH_API_KEY):
        voice_id = FISH_VOICES.get(voice_style, list(FISH_VOICES.values())[0])
        return clone_with_fish(text, voice_id, output_path)
    else:
        # 降级到 edge-tts
        voice_map = {
            "温柔女声": "xiaoxiao",
            "新闻播报": "yunyang",
            "活泼女声": "xiaoyi",
            "沉稳男声": "yunjian",
        }
        edge_voice = voice_map.get(voice_style, "xiaoxiao")
        return clone_with_edge_tts(text, edge_voice, output_path)
