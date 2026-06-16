"""
用户系统 - SQLite 存储 + bcrypt 密码 + JWT 认证
"""

import os
import sqlite3
import hashlib
import secrets
import time
import uuid
from pathlib import Path
from loguru import logger

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "users.db"


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    """初始化数据库"""
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            user_id TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            credits INTEGER DEFAULT 10,
            total_used INTEGER DEFAULT 0,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    logger.info("用户数据库初始化完成")


# 启动时初始化
init_db()


def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """PBKDF2 密码哈希（带盐）"""
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations=100000
    )
    return pwd_hash.hex(), salt


def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """验证密码"""
    pwd_hash, _ = _hash_password(password, salt)
    return pwd_hash == stored_hash


def register(username: str, password: str) -> dict:
    """注册新用户"""
    if len(username) < 3:
        return {"error": "用户名至少3个字符"}
    if len(password) < 6:
        return {"error": "密码至少6个字符"}

    conn = _get_db()
    try:
        existing = conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            return {"error": "用户名已存在"}

        pwd_hash, salt = _hash_password(password)
        user_id = uuid.uuid4().hex[:12]

        conn.execute(
            "INSERT INTO users (username, password_hash, salt, user_id, plan, credits, created_at) VALUES (?,?,?,?,?,?,?)",
            (username, pwd_hash, salt, user_id, "free", 10, time.time()),
        )
        conn.commit()
        logger.info(f"新用户注册: {username}")
        return {"success": True, "user_id": user_id, "plan": "free", "credits": 10}
    finally:
        conn.close()


def login(username: str, password: str) -> dict:
    """登录"""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT password_hash, salt, user_id, plan, credits, total_used FROM users WHERE username=?",
            (username,),
        ).fetchone()

        if not row:
            return {"error": "用户名或密码错误"}

        password_hash, salt, user_id, plan, credits, total_used = row

        if not _verify_password(password, password_hash, salt):
            return {"error": "用户名或密码错误"}

        return {
            "success": True,
            "user_id": user_id,
            "plan": plan,
            "credits": credits,
            "total_used": total_used,
        }
    finally:
        conn.close()


def check_credits(username: str) -> dict:
    """检查用户额度"""
    conn = _get_db()
    try:
        row = conn.execute("SELECT credits, plan FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return {"error": "用户不存在"}
        credits, plan = row
        return {"credits": credits, "plan": plan, "can_process": credits > 0}
    finally:
        conn.close()


def use_credit(username: str) -> bool:
    """消耗一次额度（原子操作）"""
    conn = _get_db()
    try:
        result = conn.execute(
            "UPDATE users SET credits=credits-1, total_used=total_used+1 WHERE username=? AND credits>0",
            (username,),
        )
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()


def upgrade_plan(username: str, plan: str) -> dict:
    """升级套餐（需要支付验证）"""
    plans = {
        "free": {"credits": 10, "price": 0},
        "pro": {"credits": 100, "price": 29},
        "business": {"credits": 999, "price": 99},
    }
    if plan not in plans:
        return {"error": "无效套餐"}

    conn = _get_db()
    try:
        conn.execute(
            "UPDATE users SET plan=?, credits=? WHERE username=?",
            (plan, plans[plan]["credits"], username),
        )
        conn.commit()
        return {"success": True, "plan": plan, "credits": plans[plan]["credits"], "price": plans[plan]["price"]}
    finally:
        conn.close()


def generate_token(username: str) -> str:
    """生成 JWT Token"""
    import jwt
    from core.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS

    payload = {
        "sub": username,
        "exp": time.time() + JWT_EXPIRE_HOURS * 3600,
        "iat": time.time(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> str | None:
    """验证 JWT Token，返回 username 或 None"""
    import jwt
    from core.config import JWT_SECRET, JWT_ALGORITHM

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None
