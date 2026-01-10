from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, init_directories
from app.database import init_db, close_db
from app.services.executor import shutdown_executor
from app.services.auth import init_jwt_secret
from app.api import datasets, configurations, results, visualization, auth, quality, exploration, batch, comparison, experiments, model_templates


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
    openapi_url="/api/openapi.json"
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


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "healthy"}
