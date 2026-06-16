@echo off
chcp 65001 >nul
echo ============================================
echo    🚀 一键启动 + 获取外网地址
echo ============================================
echo.

echo [1/2] 启动服务...
start /B python -m streamlit run webui.py --server.port 8503 --server.headless true --server.address 0.0.0.0

timeout /t 5 >nul

echo [2/2] 获取外网访问地址...
echo.
echo ============================================
echo    请打开这个网站获取免费隧道地址：
echo    https://localhost.run
echo    或
echo    https://serveo.net
echo.
echo    复制生成的地址发给朋友即可！
echo ============================================
echo.

:: 尝试自动打开 localhost.run
start https://localhost.run

pause
