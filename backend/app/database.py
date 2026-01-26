from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)


# SQLite 外键支持：每次连接时开启 PRAGMA foreign_keys=ON
# 仅在使用 SQLite 时生效
if "sqlite" in settings.DATABASE_URL:

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """SQLite 连接时开启外键约束"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Backward-compatible alias used by app.main
async_session_maker = async_session


class Base(DeclarativeBase):
    pass


async def get_db():
    """
    获取数据库会话

    注意：调用方需要手动 commit，异常时自动 rollback
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    初始化数据库连接

    重要：此函数不再自动创建表！

    数据库表的创建和迁移应该通过 Alembic 完成：
        cd backend
        alembic upgrade head

    这样做的好处：
    1. 避免运行时自动建表导致的迁移问题
    2. 确保生产环境和开发环境的数据库结构一致
    3. 支持数据库结构的版本控制和回滚
    """
    # 确保模型已注册到 Base.metadata
    from app.models import Configuration, Dataset, Folder, Result, User  # noqa: F401

    # 仅验证数据库连接是否正常
    async with engine.begin() as conn:
        # 简单的连接测试
        await conn.execute(
            # 使用兼容所有数据库的 SQL
            __import__("sqlalchemy").text("SELECT 1")
        )


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
