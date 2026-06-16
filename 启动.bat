@echo off
chcp 65001 >nul
title 视频工厂

echo ============================================
echo    🎬 视频工厂 - 一键出片
echo ============================================
echo.

cd /d "%~dp0"

echo 正在启动服务...
echo.

start "" http://localhost:8503

python -m streamlit run webui.py --server.port 8503 --server.headless true --browser.gatherUsageStats false
