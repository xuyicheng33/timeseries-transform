@echo off
chcp 65001 >nul
echo ========================================
echo   时序预测平台 - 一键启动
echo ========================================
echo.

:: 先关闭可能正在运行的旧进程
echo 正在清理旧进程...
taskkill /f /im "node.exe" /fi "WINDOWTITLE eq 前端服务*" >nul 2>&1
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq 后端服务*" >nul 2>&1
timeout /t 1 /nobreak >nul

echo.
echo [1/2] 正在启动后端服务...
start "后端服务" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && echo 正在运行数据库迁移... && alembic upgrade head && echo. && echo 启动后端服务器... && uvicorn app.main:app --reload --port 8000"

echo 等待后端启动...
timeout /t 4 /nobreak >nul

echo [2/2] 正在启动前端服务...
start "前端服务" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   服务启动中，请稍候...
echo ========================================
echo.
echo   后端地址: http://127.0.0.1:8000
echo   API文档:  http://127.0.0.1:8000/docs
echo   前端地址: http://localhost:5173
echo.
echo   等待服务就绪...
timeout /t 5 /nobreak >nul

echo.
echo   正在打开浏览器...
start http://localhost:5173

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo   提示：
echo   - 关闭此窗口不会停止服务
echo   - 要停止服务，请关闭"后端服务"和"前端服务"窗口
echo   - 或运行 stop-all.bat
echo.
pause

