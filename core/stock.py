"""
素材模块 - Pexels 免费视频素材
用于文字模式匹配画面
"""

import os
import random
import subprocess
import requests
from pathlib import Path
from loguru import logger

STOCK_DIR = Path(__file__).parent.parent / "stock"
STOCK_DIR.mkdir(exist_ok=True)

# 关键词 → 搜索词映射
KEYWORD_MAP = {
    "工作": "office work desk",
    "学习": "student studying library",
    "生活": "lifestyle daily routine",
    "科技": "technology computer",
    "健康": "fitness exercise yoga",
    "美食": "cooking food kitchen",
    "旅行": "travel nature landscape",
    "城市": "city urban skyline",
    "自然": "nature forest mountain",
    "动物": "animals cute pets",
    "运动": "sports running workout",
    "音乐": "music concert performance",
    "爱情": "love couple romantic",
    "家庭": "family home children",
    "商业": "business meeting office",
    "教育": "education school classroom",
}


def search_stock_videos(query: str, count: int = 3) -> list[str]:
    """
    搜索 Pexels 免费视频素材
    返回本地缓存路径列表
    """
    # 缓存目录
    cache_key = query.replace(" ", "_")[:30]
    cache_dir = STOCK_DIR / cache_key
    cache_dir.mkdir(exist_ok=True)

    # 检查缓存
    cached = list(cache_dir.glob("*.mp4"))
    if cached:
        return [str(f) for f in cached[:count]]

    # 从关键词映射搜索
    search_query = KEYWORD_MAP.get(query, query)

    # 尝试 Pexels API（需要 Key）
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    if pexels_key:
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": pexels_key},
                params={"query": search_query, "per_page": count, "size": "medium"},
                timeout=15,
            )
            if resp.status_code == 200:
                videos = resp.json().get("videos", [])
                downloaded = []
                for v in videos[:count]:
                    # 选择合适的视频文件
                    files = v.get("video_files", [])
                    mp4_files = [f for f in files if f.get("file_type") == "video/mp4"]
                    if mp4_files:
                        # 选择 720p
                        chosen = min(mp4_files, key=lambda x: abs(x.get("height", 0) - 720))
                        video_url = chosen.get("link", "")
                        if video_url:
                            local_path = cache_dir / f"{v.get('id', random.randint(1000,9999))}.mp4"
                            _download_video(video_url, str(local_path))
                            downloaded.append(str(local_path))
                if downloaded:
                    logger.info(f"Pexels 下载 {len(downloaded)} 个素材: {query}")
                    return downloaded
        except Exception as e:
            logger.warning(f"Pexels API 失败: {e}")

    return []


def _download_video(url: str, output_path: str):
    """下载视频"""
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        logger.warning(f"视频下载失败: {e}")


def get_random_stock() -> str:
    """随机获取一个缓存的素材"""
    all_videos = list(STOCK_DIR.rglob("*.mp4"))
    if all_videos:
        return str(random.choice(all_videos))
    return ""


def combine_text_with_stock(text_video_path: str, stock_path: str, output_path: str) -> str:
    """将文字视频与素材视频混合（画中画效果）"""
    if not stock_path or not os.path.exists(stock_path):
        import shutil
        shutil.copy2(text_video_path, output_path)
        return output_path

    # 获取两个视频的时长
    def get_duration(p):
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", p]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        try:
            return float(r.stdout.strip())
        except:
            return 10

    dur_text = get_duration(text_video_path)
    dur_stock = get_duration(stock_path)

    # 将素材循环到文字视频时长
    loop_count = int(dur_text / dur_stock) + 1

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(loop_count), "-i", stock_path,
        "-i", text_video_path,
        "-filter_complex",
        "[0:v]scale=1080:1920,boxblur=20:20[bg];"
        "[1:v]scale=1080:1920[fg];"
        "[bg][fg]overlay=0:0:format=auto[out]",
        "-map", "[out]", "-map", "1:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-t", str(dur_text),
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)

    if os.path.exists(output_path):
        logger.info("素材混合完成")
        return output_path

    import shutil
    shutil.copy2(text_video_path, output_path)
    return output_path
