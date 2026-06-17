"""
TTS 模块 - 文字转语音
使用 edge-tts（免费，中文效果不错）
"""

import edge_tts
import asyncio
import threading
from loguru import logger

VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "yunxia": "zh-CN-YunxiaNeural",
    "yunyang": "zh-CN-YunyangNeural",
}


async def _generate_audio(text: str, voice: str, output_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def text_to_speech(text: str, output_path: str, voice: str = "xiaoxiao") -> str:
    """文字转语音"""
    voice_id = VOICES.get(voice, VOICES["xiaoxiao"])
    logger.info(f"TTS: {voice_id} -> {output_path}")

    # 安全处理事件循环（兼容 FastAPI/Streamlit 环境）
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 已有事件循环在运行，在新线程中执行
        result = [None, None]
        def _run():
            try:
                result[0] = asyncio.run(_generate_audio(text, voice_id, output_path))
            except Exception as e:
                result[1] = e
        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=60)
        if result[1]:
            raise result[1]
    else:
        asyncio.run(_generate_audio(text, voice_id, output_path))

    logger.info(f"TTS 完成: {output_path}")
    return output_path
