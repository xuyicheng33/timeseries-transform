@echo off
REM 代码质量检查脚本（更新版）
REM 包含格式化和静态检查

echo.
echo ========================================
echo 代码质量检查
echo ========================================

cd /d "%~dp0"

echo.
echo [1/4] 后端 - Ruff 检查...
cd backend
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo 警告: 虚拟环境不存在，使用全局 Python
)

ruff check app tests
if %errorlevel% neq 0 (
    echo ❌ Ruff 检查失败
    cd ..
    exit /b 1
)

echo.
echo [2/4] 后端 - Black 格式检查...
black --check app tests
if %errorlevel% neq 0 (
    echo ❌ Black 格式检查失败
    echo 💡 运行 'black app tests' 自动修复
    cd ..
    exit /b 1
)

echo.
echo [3/4] 前端 - ESLint 检查...
cd ..\frontend
call npm run lint
if %errorlevel% neq 0 (
    echo ❌ ESLint 检查失败
    cd ..
    exit /b 1
)

echo.
echo [4/4] 前端 - Prettier 格式检查...
call npm run format:check
if %errorlevel% neq 0 (
    echo ❌ Prettier 格式检查失败
    echo 💡 运行 'npm run format' 自动修复
    cd ..
    exit /b 1
)

echo.
echo ✅ 所有检查通过！
cd ..
exit /b 0
