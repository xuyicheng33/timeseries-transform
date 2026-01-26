from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import (
    advanced_viz,
    auth,
    batch,
    comparison,
    configurations,
    datasets,
    experiments,
    exploration,
    folders,
    model_templates,
    quality,
    reports,
    results,
    visualization,
)
from app.config import init_directories, settings
from app.database import async_session_maker, close_db, init_db
from app.services.auth import init_jwt_secret
from app.services.executor import shutdown_executor


async def init_preset_model_templates():
    """
    启动时自动初始化预置模型模板
    仅在模板表为空或缺少系统模板时执行
    """
    from app.models import ModelTemplate
    from app.schemas import PRESET_MODEL_TEMPLATES

    async with async_session_maker() as db:
        try:
            # 检查是否已有系统模板
            result = await db.execute(select(ModelTemplate).where(ModelTemplate.is_system.is_(True)).limit(1))
            existing = result.scalar_one_or_none()

            if existing:
                # 已有系统模板，跳过初始化
                return

            # 初始化预置模板
            created_count = 0
            for template_data in PRESET_MODEL_TEMPLATES:
                # 检查是否已存在同名模板
                check_result = await db.execute(
                    select(ModelTemplate).where(
                        ModelTemplate.name == template_data["name"], ModelTemplate.is_system.is_(True)
                    )
                )
                if check_result.scalar_one_or_none():
                    continue

                template = ModelTemplate(
                    name=template_data["name"],
                    version=template_data.get("version", "1.0"),
                    category=template_data.get("category", "deep_learning"),
                    description=template_data.get("description", ""),
                    hyperparameters=template_data.get("hyperparameters", {}),
                    training_config=template_data.get("training_config", {}),
                    task_types=template_data.get("task_types", []),
                    recommended_features=template_data.get("recommended_features", ""),
                    is_system=True,
                    is_public=True,
                    user_id=None,
                )
                db.add(template)
                created_count += 1

            if created_count > 0:
                await db.commit()
                print(f"[启动] 已初始化 {created_count} 个预置模型模板")
        except Exception as e:
            print(f"[启动] 初始化预置模板失败: {e}")
            # 不阻止应用启动


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ===== 启动时初始化 =====
    # 1. 初始化目录（移到这里，避免 import 时的副作用）
    init_directories()

    # 2. 初始化数据库连接
    await init_db()

    # 3. 初始化 JWT 密钥（通过认证服务层，确保进程内一致性）
    # 这会触发密钥生成/验证，并缓存到认证服务模块
    init_jwt_secret()

    # 4. 自动初始化预置模型模板（本地/demo 环境）
    await init_preset_model_templates()

    yield

    # ===== 关闭时清理 =====
    # 1. 关闭数据库连接
    await close_db()

    # 2. 关闭共享线程池执行器
    shutdown_executor(wait=True, cancel_futures=False)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    # Docker 部署时通过 Nginx 代理 /api/*，所以 docs 也放在 /api/ 下
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)  # 认证路由
app.include_router(folders.router)
app.include_router(datasets.router)
app.include_router(configurations.router)
app.include_router(results.router)
app.include_router(visualization.router)
app.include_router(quality.router)  # 数据质量路由
app.include_router(exploration.router)  # 数据探索路由
app.include_router(batch.router)  # 批量操作路由
app.include_router(comparison.router)  # 配置对比分析路由
app.include_router(experiments.router)  # 实验组管理路由
app.include_router(model_templates.router)  # 模型模板路由
app.include_router(reports.router)  # 实验报告生成路由
app.include_router(advanced_viz.router)  # 高级可视化路由


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "healthy"}
