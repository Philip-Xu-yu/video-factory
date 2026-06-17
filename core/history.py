"""
历史记录模块 - 本地 JSON 存储
"""

import json
import os
import time
from pathlib import Path
from loguru import logger

HISTORY_FILE = Path(__file__).parent.parent / "data" / "history.json"
HISTORY_FILE.parent.mkdir(exist_ok=True)

MAX_HISTORY = 50


def _load() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save(history: list[dict]):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[:MAX_HISTORY], f, ensure_ascii=False, indent=2)


def add_history(entry: dict):
    """添加一条历史记录"""
    history = _load()
    entry["timestamp"] = time.time()
    entry["time_str"] = time.strftime("%Y-%m-%d %H:%M:%S")
    history.insert(0, entry)
    _save(history)
    logger.info(f"历史记录已保存: {entry.get('task_id', 'unknown')}")


def get_history(limit: int = 20) -> list[dict]:
    """获取历史记录"""
    history = _load()
    return history[:limit]


def delete_history(task_id: str):
    """删除一条历史记录"""
    history = _load()
    history = [h for h in history if h.get("task_id") != task_id]
    _save(history)


def clear_history():
    """清空历史记录"""
    _save([])
