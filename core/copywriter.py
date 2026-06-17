"""
文案模块 - 合并为 1 次 LLM 调用
提取文案 + 仿写 + 标题 + 封面文字 → 一次搞定
"""

import os
import json
import requests
from loguru import logger

API_KEY = os.environ.get("MIMO_API_KEY", "")
API_URL = "https://api.xiaomimimo.com/v1/chat/completions"
MODEL = "mimo-v2.5-pro"


def _call_llm(prompt: str, system: str = "") -> str:
    """调用 MiMo LLM"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    try:
        resp = requests.post(API_URL, json=data, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return ""


def generate_all_copy(transcript: str, template: str = "douyin") -> dict:
    """
    一次 LLM 调用生成所有文案内容
    返回: {"copy": 仿写文案, "title": 标题, "cover_main": 封面主标题, "cover_sub": 封面副标题}
    """
    logger.info(f"AI 生成所有文案 [{template}]...")

    style_map = {
        "douyin": "短视频爆款风格，节奏快，有钩子，有反转，适合 15-30 秒",
        "knowledge": "知识分享风格，专业但易懂，有干货，适合 1-2 分钟",
        "product": "产品介绍风格，突出卖点，有说服力，适合 30 秒",
        "festival": "节日营销风格，喜庆热闹，有优惠信息，适合 15-30 秒",
    }

    prompt = f"""你是一个短视频文案高手。请根据以下视频转录文字，一次性完成以下任务：

转录文字：
{transcript[:1000]}

视频类型：{style_map.get(template, style_map['douyin'])}

请严格按照以下 JSON 格式返回（不要加任何其他文字）：
{{
    "copy": "仿写后的短视频文案（100-300字，口语化，适合真人出镜）",
    "title": "视频标题（15-25字，吸引点击）",
    "cover_main": "封面主标题（6-10个字，大号加粗）",
    "cover_sub": "封面副标题（10-20个字，补充说明）"
}}"""

    result = _call_llm(prompt, system="你是一个专业的内容创作专家。只返回JSON，不要其他内容。")

    if result:
        # 清理可能的 markdown 代码块
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
        if clean.endswith("```"):
            clean = clean.rsplit("```", 1)[0]
        clean = clean.strip()

        try:
            data = json.loads(clean)
            logger.info("文案生成完成")
            return {
                "copy": data.get("copy", transcript),
                "title": data.get("title", "AI 生成视频"),
                "cover_main": data.get("cover_main", "AI 视频"),
                "cover_sub": data.get("cover_sub", ""),
            }
        except json.JSONDecodeError:
            logger.warning(f"LLM 返回非 JSON: {clean[:100]}")

    # 降级：返回原文
    return {
        "copy": transcript,
        "title": "AI 生成视频",
        "cover_main": "AI 视频",
        "cover_sub": "",
    }


# 保留旧接口兼容
def extract_copy(transcript: str) -> str:
    return generate_all_copy(transcript)["copy"]

def rewrite_copy(original: str, style: str = "douyin") -> str:
    return generate_all_copy(original, style)["copy"]

def generate_title(content: str, template: str = "douyin") -> str:
    return generate_all_copy(content, template)["title"]

def generate_cover_text(content: str) -> dict:
    result = generate_all_copy(content)
    return {"main": result["cover_main"], "sub": result["cover_sub"]}
