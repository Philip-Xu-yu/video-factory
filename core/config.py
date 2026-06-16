"""
配置模块 - 加载 .env 文件
"""

import os
from pathlib import Path

# 加载 .env 文件
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# API Keys
MIMO_API_KEY = os.environ.get("MIMO_API_KEY", "")
FISH_API_KEY = os.environ.get("FISH_API_KEY", "")

# JWT
JWT_SECRET = os.environ.get("JWT_SECRET", "change-this-to-a-random-string")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# Server
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# Paths
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"

# 确保目录存在
for d in [UPLOAD_DIR, OUTPUT_DIR, DATA_DIR]:
    d.mkdir(exist_ok=True)
