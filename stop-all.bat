@echo off
chcp 65001 >nul
echo ========================================
echo   时序预测平台 - 停止所有服务
echo ========================================
echo.

echo 正在停止后端服务...
:: 停止 uvicorn (Python)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo 正在停止前端服务...
:: 停止 vite (Node)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo ========================================
echo   所有服务已停止
echo ========================================
echo.
pause

