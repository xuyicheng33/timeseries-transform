#!/usr/bin/env python3
"""
代码质量检查脚本

用于本地开发和 CI 环境，检查代码的基本质量：
1. Python 语法检查（compileall）
2. 前端构建检查（npm run build）

使用方式：
    python scripts/check_quality.py          # 检查所有
    python scripts/check_quality.py --backend   # 只检查后端
    python scripts/check_quality.py --frontend  # 只检查前端

退出码：
    0 - 所有检查通过
    1 - 检查失败
"""
import os
import sys
import subprocess
import argparse
import py_compile
from pathlib import Path


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


class Colors:
    """终端颜色"""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def check_python_syntax() -> bool:
    """
    检查 Python 语法
    使用 py_compile 逐个检查文件，提供更详细的错误信息
    """
    print_header("检查 Python 语法")
    
    errors = []
    checked_count = 0
    
    # 要检查的目录
    check_dirs = [
        BACKEND_DIR / "app",
        BACKEND_DIR / "migrations",
    ]
    
    for check_dir in check_dirs:
        if not check_dir.exists():
            print_warning(f"目录不存在: {check_dir}")
            continue
        
        for py_file in check_dir.rglob("*.py"):
            # 跳过 __pycache__ 目录
            if "__pycache__" in str(py_file):
                continue
            
            checked_count += 1
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                errors.append((py_file, str(e)))
    
    if errors:
        print_error(f"发现 {len(errors)} 个语法错误：")
        for file_path, error in errors:
            rel_path = file_path.relative_to(PROJECT_ROOT)
            print(f"\n  {Colors.RED}{rel_path}{Colors.RESET}")
            # 提取并格式化错误信息
            error_lines = str(error).split('\n')
            for line in error_lines:
                if line.strip():
                    print(f"    {line}")
        return False
    
    print_success(f"检查了 {checked_count} 个 Python 文件，无语法错误")
    return True


def check_python_imports() -> bool:
    """
    检查 Python 导入是否正确
    尝试导入主模块，检查是否有导入错误
    """
    print_header("检查 Python 导入")
    
    # 添加 backend 到 Python 路径
    sys.path.insert(0, str(BACKEND_DIR))
    
    modules_to_check = [
        "app.main",
        "app.config",
        "app.database",
        "app.models",
        "app.schemas",
        "app.services.auth",
        "app.services.utils",
        "app.services.permissions",
        "app.services.quality",
        "app.services.cleaning",
        "app.api.auth",
        "app.api.datasets",
        "app.api.configurations",
        "app.api.results",
        "app.api.visualization",
        "app.api.quality",
    ]
    
    errors = []
    for module_name in modules_to_check:
        try:
            __import__(module_name)
            print_success(f"导入成功: {module_name}")
        except Exception as e:
            errors.append((module_name, str(e)))
            print_error(f"导入失败: {module_name}")
            print(f"    {Colors.RED}{e}{Colors.RESET}")
    
    # 清理 sys.path
    sys.path.remove(str(BACKEND_DIR))
    
    if errors:
        print_error(f"\n{len(errors)} 个模块导入失败")
        return False
    
    print_success(f"\n所有 {len(modules_to_check)} 个模块导入成功")
    return True


def check_frontend_build() -> bool:
    """
    检查前端构建
    运行 npm run build 检查 TypeScript 编译和构建是否成功
    """
    print_header("检查前端构建")
    
    if not FRONTEND_DIR.exists():
        print_warning(f"前端目录不存在: {FRONTEND_DIR}")
        return True
    
    # 检查 node_modules 是否存在
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print_warning("node_modules 不存在，正在安装依赖...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            shell=True  # Windows 需要
        )
        if result.returncode != 0:
            print_error("npm install 失败")
            print(result.stderr)
            return False
        print_success("依赖安装成功")
    
    # 运行构建
    print("正在运行 npm run build...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        shell=True  # Windows 需要
    )
    
    if result.returncode != 0:
        print_error("前端构建失败")
        print(f"\n{Colors.RED}错误输出:{Colors.RESET}")
        # 输出 stderr 和 stdout（TypeScript 错误可能在 stdout）
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        return False
    
    print_success("前端构建成功")
    return True


def check_frontend_lint() -> bool:
    """
    检查前端 ESLint
    """
    print_header("检查前端 ESLint")
    
    if not FRONTEND_DIR.exists():
        print_warning(f"前端目录不存在: {FRONTEND_DIR}")
        return True
    
    # 检查 node_modules 是否存在
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print_warning("跳过 ESLint 检查（node_modules 不存在）")
        return True
    
    print("正在运行 npm run lint...")
    result = subprocess.run(
        ["npm", "run", "lint"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        shell=True
    )
    
    if result.returncode != 0:
        print_warning("ESLint 发现问题（非阻塞）")
        if result.stdout:
            print(result.stdout)
        # ESLint 警告不阻塞构建
        return True
    
    print_success("ESLint 检查通过")
    return True


def main():
    parser = argparse.ArgumentParser(description="代码质量检查脚本")
    parser.add_argument("--backend", action="store_true", help="只检查后端")
    parser.add_argument("--frontend", action="store_true", help="只检查前端")
    parser.add_argument("--skip-imports", action="store_true", help="跳过导入检查")
    parser.add_argument("--skip-build", action="store_true", help="跳过前端构建检查")
    args = parser.parse_args()
    
    # 如果没有指定，则检查所有
    check_all = not args.backend and not args.frontend
    
    results = []
    
    # 后端检查
    if check_all or args.backend:
        results.append(("Python 语法检查", check_python_syntax()))
        
        if not args.skip_imports:
            results.append(("Python 导入检查", check_python_imports()))
    
    # 前端检查
    if check_all or args.frontend:
        results.append(("前端 ESLint", check_frontend_lint()))
        
        if not args.skip_build:
            results.append(("前端构建检查", check_frontend_build()))
    
    # 汇总结果
    print_header("检查结果汇总")
    
    all_passed = True
    for name, passed in results:
        if passed:
            print_success(name)
        else:
            print_error(name)
            all_passed = False
    
    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有检查通过！{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 部分检查失败，请修复后重试{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

