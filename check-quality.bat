@echo off
REM 代码质量检查脚本 (Windows)
REM 用于本地开发和 CI 环境

echo.
echo ============================================================
echo           时间序列平台 - 代码质量检查
echo ============================================================
echo.

cd /d "%~dp0"

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未安装或不在 PATH 中
    exit /b 1
)

REM 运行检查脚本
python scripts/check_quality.py %*

exit /b %errorlevel%

