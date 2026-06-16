"""
文案模块 - 提取文案 + AI 仿写 + 标题生成
接入 MiMo LLM
"""

import os
import requests
from loguru import logger

# MiMo API 配置 - 从环境变量读取，禁止硬编码
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


def extract_copy(transcript: str) -> str:
    """从转录文字中提取核心文案"""
    logger.info("提取核心文案...")
    prompt = f"""从以下视频转录文字中，提取核心观点和金句，整理成简洁的文案。
去掉口头禅、重复、废话，保留有价值的内容。

转录文字：
{transcript}

要求：
1. 保留核心观点
2. 去掉"嗯"、"啊"、"就是说"等口头禅
3. 语句通顺，适合短视频文案
4. 长度控制在 200 字以内"""

    result = _call_llm(prompt, system="你是一个专业的短视频文案编辑。")
    return result if result else transcript


def rewrite_copy(original: str, style: str = "douyin") -> str:
    """AI 仿写文案"""
    logger.info(f"AI 仿写文案 [{style}]...")

    style_prompts = {
        "douyin": "短视频爆款风格，节奏快，有钩子，有反转，适合 15-30 秒",
        "knowledge": "知识分享风格，专业但易懂，有干货，适合 1-2 分钟",
        "product": "产品介绍风格，突出卖点，有说服力，适合 30 秒",
        "festival": "节日营销风格，喜庆热闹，有优惠信息，适合 15-30 秒",
    }

    style_desc = style_prompts.get(style, style_prompts["douyin"])

    prompt = f"""请根据以下原文，仿写一段短视频文案。

原文：
{original}

要求：
1. 风格：{style_desc}
2. 保留原文核心意思
3. 语言口语化，适合真人出镜
4. 开头要有钩子（吸引注意力）
5. 结尾要有行动号召
6. 长度：100-300 字"""

    result = _call_llm(prompt, system="你是一个短视频文案高手，擅长写爆款文案。")
    return result if result else original


def generate_title(content: str, template: str = "douyin") -> str:
    """生成视频标题"""
    logger.info("生成视频标题...")

    prompt = f"""为以下短视频内容生成 3 个标题选项，用户会选择最好的一个。

内容：
{content[:300]}

模板类型：{template}

要求：
1. 标题要吸引点击
2. 包含关键词，利于搜索
3. 不要标题党，要真实
4. 每个标题 15-25 字
5. 用 | 分隔三个标题"""

    result = _call_llm(prompt, system="你是一个短视频运营专家。")
    if result:
        # 取第一个标题
        titles = [t.strip() for t in result.split("|") if t.strip()]
        return titles[0] if titles else result.split("\n")[0]
    return "AI 生成视频"


def generate_cover_text(content: str) -> dict:
    """生成封面文字"""
    logger.info("生成封面文字...")

    prompt = f"""为以下短视频内容生成封面文字。

内容：
{content[:300]}

要求：
1. 主标题：6-10 个字，大号加粗
2. 副标题：10-20 个字，补充说明
3. 要吸引眼球，适合手机竖屏

格式：
主标题：xxx
副标题：xxx"""

    result = _call_llm(prompt, system="你是一个短视频封面设计专家。")
    if result:
        lines = result.strip().split("\n")
        main_title = ""
        sub_title = ""
        for line in lines:
            if "主标题" in line:
                main_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif "副标题" in line:
                sub_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        return {"main": main_title or "AI 生成", "sub": sub_title or ""}
    return {"main": "AI 生成", "sub": ""}
