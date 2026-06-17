"""
数字人模块 - 图片驱动说话视频
支持: SadTalker / LivePortrait / HeyGem
"""

import os
import subprocess
from pathlib import Path
from loguru import logger


def check_gpu() -> dict:
    """检查 GPU 状态"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            return {
                "available": True,
                "name": parts[0] if parts else "Unknown",
                "memory_total": parts[1] if len(parts) > 1 else "Unknown",
                "memory_free": parts[2] if len(parts) > 1 else "Unknown",
            }
    except Exception:
        pass
    return {"available": False}


def generate_digital_human(photo_path: str, audio_path: str, output_dir: str) -> dict:
    """
    生成数字人视频
    photo_path: 正面照片路径
    audio_path: 配音音频路径
    output_dir: 输出目录
    """
    gpu = check_gpu()
    if not gpu["available"]:
        return {"success": False, "error": "未检测到 GPU，数字人功能需要 GPU 加速"}

    logger.info(f"生成数字人: {photo_path} + {audio_path}")

    # 方案 1: 尝试 SadTalker（已安装）
    sadtalker_path = _find_sadtalker()
    if sadtalker_path:
        return _run_sadtalker(sadtalker_path, photo_path, audio_path, output_dir)

    # 方案 2: 尝试 LivePortrait
    liveportrait_path = _find_liveportrait()
    if liveportrait_path:
        return _run_liveportrait(liveportrait_path, photo_path, audio_path, output_dir)

    # 方案 3: 尝试 HeyGem API
    try:
        return _run_heygem_api(photo_path, audio_path, output_dir)
    except Exception:
        pass

    return {
        "success": False,
        "error": "未找到数字人工具。请安装 SadTalker、LivePortrait 或 HeyGem。",
        "install_guide": """
安装方法（任选其一）：

1. SadTalker（推荐，最简单）：
   git clone https://github.com/OpenTalker/SadTalker.git
   cd SadTalker && pip install -r requirements.txt

2. LivePortrait（效果最好）：
   git clone https://github.com/KwaiVGI/LivePortrait.git
   cd LivePortrait && pip install -r requirements.txt

3. HeyGem（专业级）：
   访问 https://github.com/HeyGem/HeyGem 下载安装
        """,
    }


def _find_sadtalker() -> str:
    """查找 SadTalker"""
    candidates = [
        "D:/SadTalker",
        "D:/Claude code测试/SadTalker",
        os.path.expanduser("~/SadTalker"),
    ]
    for path in candidates:
        if os.path.exists(os.path.join(path, "inference.py")):
            return path
    return ""


def _find_liveportrait() -> str:
    """查找 LivePortrait"""
    candidates = [
        "D:/LivePortrait",
        "D:/Claude code测试/LivePortrait",
        os.path.expanduser("~/LivePortrait"),
    ]
    for path in candidates:
        if os.path.exists(os.path.join(path, "src")):
            return path
    return ""


def _run_sadtalker(sadtalker_path: str, photo_path: str, audio_path: str, output_dir: str) -> dict:
    """运行 SadTalker"""
    logger.info(f"使用 SadTalker: {sadtalker_path}")
    output_path = os.path.join(output_dir, "dh_output.mp4")

    cmd = [
        "python", os.path.join(sadtalker_path, "inference.py"),
        "--driven_audio", audio_path,
        "--source_image", photo_path,
        "--result_dir", output_dir,
        "--enhancer", "gfpgan",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=sadtalker_path)

    # 查找输出文件
    for f in Path(output_dir).glob("*.mp4"):
        if "result" in f.name or "dh_output" in f.name:
            return {"success": True, "video_path": str(f)}

    return {"success": False, "error": "SadTalker 处理失败"}


def _run_liveportrait(liveportrait_path: str, photo_path: str, audio_path: str, output_dir: str) -> dict:
    """运行 LivePortrait"""
    logger.info(f"使用 LivePortrait: {liveportrait_path}")
    output_path = os.path.join(output_dir, "dh_output.mp4")

    cmd = [
        "python", os.path.join(liveportrait_path, "src", "gradio_demo.py"),
        "--driven_audio", audio_path,
        "--source_image", photo_path,
        "--output_dir", output_dir,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=liveportrait_path)

    if os.path.exists(output_path):
        return {"success": True, "video_path": output_path}

    for f in Path(output_dir).glob("*.mp4"):
        return {"success": True, "video_path": str(f)}

    return {"success": False, "error": "LivePortrait 处理失败"}


def _run_heygem_api(photo_path: str, audio_path: str, output_dir: str) -> dict:
    """尝试调用 HeyGem API"""
    import requests

    # HeyGem 默认本地 API 地址
    heygem_url = os.environ.get("HEYGEM_URL", "http://127.0.0.1:8080")

    with open(photo_path, "rb") as f_photo, open(audio_path, "rb") as f_audio:
        files = {
            "photo": (os.path.basename(photo_path), f_photo, "image/jpeg"),
            "audio": (os.path.basename(audio_path), f_audio, "audio/mpeg"),
        }
        resp = requests.post(f"{heygem_url}/api/digital-human", files=files, timeout=300)

    if resp.status_code == 200:
        output_path = os.path.join(output_dir, "dh_output.mp4")
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return {"success": True, "video_path": output_path}

    return {"success": False, "error": f"HeyGem API 返回 {resp.status_code}"}
