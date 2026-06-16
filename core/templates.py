"""
模板系统 - 4 种视频风格
"""

TEMPLATES = {
    "douyin": {
        "name": "🔥 抖音热门",
        "desc": "30秒-1分钟精华短视频，动态字幕，卡点BGM",
        "subtitle_style": "tiktok",
        "crop": True,
        "remove_silence": True,
        "aspect": "9:16",
        "voice": "xiaoxiao",
    },
    "knowledge": {
        "name": "📚 知识分享",
        "desc": "1-2分钟知识卡片，清晰字幕，舒适节奏",
        "subtitle_style": "default",
        "crop": True,
        "remove_silence": True,
        "aspect": "9:16",
        "voice": "yunjian",
    },
    "product": {
        "name": "💼 产品介绍",
        "desc": "30秒产品展示，专业配音，字幕清晰",
        "subtitle_style": "default",
        "crop": True,
        "remove_silence": False,
        "aspect": "9:16",
        "voice": "yunyang",
    },
    "festival": {
        "name": "🎉 节日营销",
        "desc": "节日氛围视频，动态文字，喜庆BGM",
        "subtitle_style": "tiktok",
        "crop": True,
        "remove_silence": False,
        "aspect": "9:16",
        "voice": "xiaoxiao",
    },
}


def get_template(template_id: str) -> dict:
    return TEMPLATES.get(template_id, TEMPLATES["douyin"])


def list_templates() -> list[dict]:
    return [{"id": k, **v} for k, v in TEMPLATES.items()]
