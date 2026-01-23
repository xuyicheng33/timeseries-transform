"""
Alembic 环境配置文件
支持 SQLite 和 PostgreSQL
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 导入应用配置和模型
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import Base
from app.models import User, Folder, Dataset, Configuration, Result  # 确保所有模型都被导入

# Alembic Config 对象
config = context.config


def get_sync_database_url() -> str:
    """
    将异步数据库 URL 转换为同步 URL
    支持 SQLite 和 PostgreSQL
    """
    url = settings.DATABASE_URL
    
    # SQLite: sqlite+aiosqlite -> sqlite
    if "+aiosqlite" in url:
        return url.replace("+aiosqlite", "")
    
    # PostgreSQL: postgresql+asyncpg -> postgresql
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "")
    
    # 其他情况，尝试移除常见的异步驱动
    if "+aiomysql" in url:
        return url.replace("+aiomysql", "+pymysql")
    
    return url


# 设置数据库 URL（从应用配置读取）
sync_database_url = get_sync_database_url()
config.set_main_option("sqlalchemy.url", sync_database_url)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据（用于自动生成迁移）
target_metadata = Base.metadata

# 判断是否为 SQLite
is_sqlite = "sqlite" in sync_database_url


def run_migrations_offline() -> None:
    """
    离线模式运行迁移
    只生成 SQL 脚本，不实际执行
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite 特殊配置
        render_as_batch=is_sqlite,  # SQLite 不支持 ALTER，需要批量模式
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """执行迁移的核心逻辑"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # SQLite 特殊配置
        render_as_batch=is_sqlite,  # SQLite 不支持 ALTER，需要批量模式
        compare_type=True,  # 检测列类型变化
        compare_server_default=True,  # 检测默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    异步模式运行迁移
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    在线模式运行迁移
    直接连接数据库执行
    """
    from sqlalchemy import create_engine
    
    connectable = create_engine(
        sync_database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

