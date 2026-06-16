"""
TTS 模块 - 文字转语音
使用 edge-tts（免费，中文效果不错）
后续可替换为 GPT-SoVITS（声音克隆）
"""

import edge_tts
import asyncio
from loguru import logger

# 中文语音列表
VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",    # 女声，温柔
    "xiaoyi": "zh-CN-XiaoyiNeural",        # 女声，活泼
    "yunjian": "zh-CN-YunjianNeural",      # 男声，沉稳
    "yunxi": "zh-CN-YunxiNeural",          # 男声，年轻
    "yunxia": "zh-CN-YunxiaNeural",        # 男声，少年
    "yunyang": "zh-CN-YunyangNeural",      # 男声，播音
}


async def _generate_audio(text: str, voice: str, output_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def text_to_speech(text: str, output_path: str, voice: str = "xiaoxiao") -> str:
    """
    文字转语音
    voice: xiaoxiao/xiaoyi/yunjian/yunxi/yunxia/yunyang
    """
    voice_id = VOICES.get(voice, VOICES["xiaoxiao"])
    logger.info(f"TTS: {voice_id} -> {output_path}")

    asyncio.run(_generate_audio(text, voice_id, output_path))

    logger.info(f"TTS 完成: {output_path}")
    return output_path
