from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)


# SQLite 外键支持：每次连接时开启 PRAGMA foreign_keys=ON
# 仅在使用 SQLite 时生效
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """SQLite 连接时开启外键约束"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """
    初始化数据库
    
    注意：生产环境应使用 Alembic 迁移，而不是 create_all
    
    使用方法：
        cd backend
        alembic upgrade head
    
    如果是全新数据库，create_all 会创建所有表。
    如果是已有数据库，请使用 alembic 进行迁移。
    """
    from app.models import User, Dataset, Configuration, Result  # 确保模型已注册
    
    # 检查是否需要运行迁移
    async with engine.begin() as conn:
        # 尝试检查 alembic_version 表是否存在
        try:
            if "sqlite" in settings.DATABASE_URL:
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                ))
            else:
                result = await conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
                ))
            has_alembic = result.scalar()
            
            if has_alembic:
                # 已有迁移记录，跳过 create_all
                # 用户应该使用 alembic upgrade head
                return
        except Exception:
            pass
        
        # 检查是否有任何表存在（旧数据库）
        try:
            if "sqlite" in settings.DATABASE_URL:
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='datasets'"
                ))
            else:
                result = await conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'datasets')"
                ))
            has_tables = result.scalar()
            
            if has_tables:
                # 旧数据库存在，提示用户运行迁移
                import warnings
                warnings.warn(
                    "\n" + "=" * 60 + "\n"
                    "检测到旧数据库，请运行 Alembic 迁移：\n"
                    "  cd backend\n"
                    "  alembic stamp 001_initial  # 标记当前状态\n"
                    "  alembic upgrade head       # 执行迁移\n"
                    "=" * 60,
                    UserWarning
                )
                return
        except Exception:
            pass
        
        # 全新数据库，使用 create_all 创建表
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
