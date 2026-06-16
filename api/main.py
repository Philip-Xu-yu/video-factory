"""
视频工厂 API v3 - 安全版本
修复: 认证 + 路径安全 + 频率限制 + 输入校验
"""

import os
import re
import uuid
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import MIMO_API_KEY, UPLOAD_DIR, OUTPUT_DIR
from core.pipeline import process_video, process_text_to_video
from core.templates import list_templates, get_template
from core.user import (
    register, login, check_credits, use_credit,
    upgrade_plan, generate_token, verify_token,
)

# ===== FastAPI =====
app = FastAPI(title="AI 视频工厂", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8503", "http://127.0.0.1:8503"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# ===== 频率限制（简单内存实现） =====
_rate_limit: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # 秒
RATE_LIMIT_MAX = 30  # 每分钟最多请求数


def check_rate_limit(request: Request):
    ip = request.client.host
    now = time.time()
    if ip not in _rate_limit:
        _rate_limit[ip] = []
    _rate_limit[ip] = [t for t in _rate_limit[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit[ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    _rate_limit[ip].append(now)


# ===== 认证依赖 =====
def get_current_user(request: Request) -> str:
    """从 JWT Token 获取当前用户"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth[7:]
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return username


def get_optional_user(request: Request) -> str:
    """可选认证，未登录返回 guest"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        username = verify_token(auth[7:])
        if username:
            return username
    return "guest"


# ===== 文件名安全处理 =====
def safe_filename(filename: str) -> str:
    """清洗文件名，防止路径遍历"""
    name = os.path.basename(filename)
    name = re.sub(r'[^\w\-.]', '_', name)
    name = f"{uuid.uuid4().hex[:8]}_{name}"
    return name


def safe_task_id(task_id: str) -> str:
    """校验 task_id 格式"""
    if not re.match(r'^[a-f0-9]{8}$', task_id):
        raise HTTPException(status_code=400, detail="无效的任务ID")
    return task_id


# ===== 请求模型 =====
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UpgradeRequest(BaseModel):
    plan: str

class TextVideoRequest(BaseModel):
    text: str
    template: str = "douyin"
    voice: str = "xiaoxiao"


# ===== 白名单 =====
ALLOWED_TEMPLATES = {"douyin", "knowledge", "product", "festival"}
ALLOWED_VOICES = {"xiaoxiao", "xiaoyi", "yunjian", "yunxi", "yunxia", "yunyang"}
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


# ===== 路由 =====
@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/api/templates")
def api_templates():
    return {"templates": list_templates()}


# --- 用户系统 ---
@app.post("/api/user/register")
def api_register(req: RegisterRequest):
    return register(req.username, req.password)


@app.post("/api/user/login")
def api_login(req: LoginRequest):
    result = login(req.username, req.password)
    if result.get("success"):
        result["token"] = generate_token(req.username)
    return result


@app.get("/api/user/me")
def api_me(user: str = Depends(get_current_user)):
    info = check_credits(user)
    info["username"] = user
    return info


@app.post("/api/user/upgrade")
def api_upgrade(req: UpgradeRequest, user: str = Depends(get_current_user)):
    return upgrade_plan(user, req.plan)


# --- 视频处理 ---
@app.post("/api/video/process")
async def api_process_video(
    request: Request,
    file: UploadFile = File(...),
    template: str = Form("douyin"),
    voice: str = Form("xiaoxiao"),
    user: str = Depends(get_optional_user),
):
    # 频率限制
    check_rate_limit(request)

    # 输入校验
    if template not in ALLOWED_TEMPLATES:
        raise HTTPException(status_code=400, detail="无效的模板")
    if voice not in ALLOWED_VOICES:
        raise HTTPException(status_code=400, detail="无效的声音")

    # 文件类型校验
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的文件格式")

    # 额度检查
    if user != "guest":
        credit_info = check_credits(user)
        if not credit_info.get("can_process"):
            raise HTTPException(status_code=402, detail="额度用完，请升级")

    # 安全文件名
    safe_name = safe_filename(file.filename)
    upload_path = UPLOAD_DIR / safe_name

    # 分块读取（防止内存爆）
    MAX_SIZE = 500 * 1024 * 1024
    content = bytearray()
    while chunk := await file.read(8192):
        content.extend(chunk)
        if len(content) > MAX_SIZE:
            os.remove(upload_path) if upload_path.exists() else None
            raise HTTPException(status_code=413, detail="文件太大，最大 500MB")

    upload_path.write_bytes(content)

    try:
        result = process_video(str(upload_path), template, str(OUTPUT_DIR), voice)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # 免费用户加水印
        if user != "guest":
            credit_info = check_credits(user)
            if credit_info.get("plan") == "free":
                from core.watermark import add_watermark
                wm_path = result["output_path"].replace("_final.mp4", "_wm.mp4")
                add_watermark(result["output_path"], wm_path)
                result["output_path"] = wm_path
            use_credit(user)

        return {"success": True, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise HTTPException(status_code=500, detail="处理失败，请稍后重试")
    finally:
        if upload_path.exists():
            os.remove(upload_path)


@app.post("/api/video/text")
def api_text_to_video(
    request: Request,
    req: TextVideoRequest,
    user: str = Depends(get_optional_user),
):
    check_rate_limit(request)

    if req.template not in ALLOWED_TEMPLATES:
        raise HTTPException(status_code=400, detail="无效的模板")
    if req.voice not in ALLOWED_VOICES:
        raise HTTPException(status_code=400, detail="无效的声音")

    if user != "guest":
        credit_info = check_credits(user)
        if not credit_info.get("can_process"):
            raise HTTPException(status_code=402, detail="额度用完，请升级")

    try:
        result = process_text_to_video(req.text, req.template, str(OUTPUT_DIR), req.voice)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        if user != "guest":
            credit_info = check_credits(user)
            if credit_info.get("plan") == "free":
                from core.watermark import add_watermark
                wm_path = result["output_path"].replace("final.mp4", "final_wm.mp4")
                add_watermark(result["output_path"], wm_path)
                result["output_path"] = wm_path
            use_credit(user)

        return {"success": True, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理失败: {e}")
        raise HTTPException(status_code=500, detail="处理失败，请稍后重试")


@app.get("/api/download/{task_id}")
def api_download(task_id: str):
    task_id = safe_task_id(task_id)
    task_dir = OUTPUT_DIR / task_id

    # 路径安全校验
    if not task_dir.resolve().is_relative_to(OUTPUT_DIR.resolve()):
        raise HTTPException(status_code=403, detail="禁止访问")

    if not task_dir.exists():
        raise HTTPException(status_code=404, detail="任务不存在")

    for f in task_dir.iterdir():
        if "final" in f.name and f.name.endswith(".mp4"):
            return FileResponse(str(f), media_type="video/mp4", filename=f.name)

    raise HTTPException(status_code=404, detail="成品不存在")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
