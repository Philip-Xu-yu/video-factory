"""
自动清理模块 - 定期清理临时文件和过期任务
"""

import os
import time
import shutil
from loguru import logger

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cleanup_old_tasks(max_age_hours: int = 24):
    """清理超过指定时间的任务目录"""
    output_dir = os.path.join(BASE_DIR, "output")
    upload_dir = os.path.join(BASE_DIR, "uploads")

    cleaned = 0
    now = time.time()

    for d in [output_dir, upload_dir]:
        if not os.path.exists(d):
            continue
        for item in os.listdir(d):
            item_path = os.path.join(d, item)
            if not os.path.isdir(item_path):
                # 清理上传的大文件
                if os.path.getmtime(item_path) < now - max_age_hours * 3600:
                    os.remove(item_path)
                    cleaned += 1
                continue

            # 清理任务目录
            age_hours = (now - os.path.getmtime(item_path)) / 3600
            if age_hours > max_age_hours:
                shutil.rmtree(item_path, ignore_errors=True)
                cleaned += 1

    if cleaned:
        logger.info(f"清理了 {cleaned} 个过期文件/目录")
    return cleaned


def cleanup_temp_files():
    """清理系统临时目录中的视频工厂文件"""
    import tempfile
    temp_dir = tempfile.gettempdir()
    cleaned = 0

    for item in os.listdir(temp_dir):
        if item.startswith("tmp") and os.path.isdir(os.path.join(temp_dir, item)):
            item_path = os.path.join(temp_dir, item)
            # 检查是否包含视频文件
            try:
                files = os.listdir(item_path)
                if any(f.endswith((".mp4", ".mp3", ".wav")) for f in files):
                    age_hours = (time.time() - os.path.getmtime(item_path)) / 3600
                    if age_hours > 1:
                        shutil.rmtree(item_path, ignore_errors=True)
                        cleaned += 1
            except:
                pass

    if cleaned:
        logger.info(f"清理了 {cleaned} 个临时目录")
    return cleaned


def get_disk_usage() -> dict:
    """获取磁盘使用情况"""
    output_dir = os.path.join(BASE_DIR, "output")
    upload_dir = os.path.join(BASE_DIR, "uploads")

    total_size = 0
    file_count = 0

    for d in [output_dir, upload_dir]:
        if not os.path.exists(d):
            continue
        for root, dirs, files in os.walk(d):
            for f in files:
                fp = os.path.join(root, f)
                total_size += os.path.getsize(fp)
                file_count += 1

    return {
        "total_size_mb": round(total_size / 1024 / 1024, 1),
        "file_count": file_count,
    }
