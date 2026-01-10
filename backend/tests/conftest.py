"""
测试配置和 Fixtures

提供测试所需的数据库、客户端、认证等基础设施
"""
import os
import sys
import asyncio
import tempfile
import shutil
from typing import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# 确保可以导入 app 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, get_db
from app.main import app
from app.models import User, Dataset, Configuration, Result
from app.services.auth import get_password_hash


# ============ 测试数据库配置 ============

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 测试专用上传目录（隔离生产数据）
TEST_UPLOAD_DIR = Path(__file__).parent.parent / "uploads_test"


@pytest.fixture(scope="session", autouse=True)
def setup_test_upload_dir():
    """设置测试上传目录（session 级别，自动清理）"""
    # 创建测试目录
    TEST_UPLOAD_DIR.mkdir(exist_ok=True)
    (TEST_UPLOAD_DIR / "datasets").mkdir(exist_ok=True)
    (TEST_UPLOAD_DIR / "results").mkdir(exist_ok=True)
    (TEST_UPLOAD_DIR / "cache").mkdir(exist_ok=True)
    
    # 设置环境变量让应用使用测试目录
    original_upload_dir = os.environ.get("UPLOAD_DIR")
    os.environ["UPLOAD_DIR"] = str(TEST_UPLOAD_DIR)
    
    yield
    
    # 清理测试目录
    if TEST_UPLOAD_DIR.exists():
        shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
    
    # 恢复环境变量
    if original_upload_dir:
        os.environ["UPLOAD_DIR"] = original_upload_dir
    elif "UPLOAD_DIR" in os.environ:
        del os.environ["UPLOAD_DIR"]


@pytest.fixture(scope="function")
def clean_test_uploads():
    """每个测试函数后清理上传的文件"""
    yield
    # 清理测试上传目录中的文件（保留目录结构）
    for subdir in ["datasets", "results", "cache"]:
        dir_path = TEST_UPLOAD_DIR / subdir
        if dir_path.exists():
            for item in dir_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环（session 级别共享）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """创建测试数据库引擎（每个测试函数独立）"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """创建测试 HTTP 客户端"""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # 覆盖数据库依赖
    async def override_get_db():
        async with async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # 清理依赖覆盖
    app.dependency_overrides.clear()


# ============ 测试数据 Fixtures ============

@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_admin=False
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(test_session: AsyncSession) -> User:
    """创建管理员用户"""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_admin=True
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """获取认证头（普通用户）"""
    response = await client.post("/api/auth/login", data={
        "username": "testuser",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(client: AsyncClient, admin_user: User) -> dict:
    """获取认证头（管理员）"""
    response = await client.post("/api/auth/login", data={
        "username": "admin",
        "password": "adminpassword123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_dataset(test_session: AsyncSession, test_user: User) -> Dataset:
    """创建测试数据集"""
    dataset = Dataset(
        name="Test Dataset",
        filename="test_data.csv",
        filepath="/tmp/test_data.csv",
        file_size=1024,
        row_count=100,
        column_count=5,
        columns=["col1", "col2", "col3", "col4", "col5"],
        description="Test dataset for unit tests",
        user_id=test_user.id,
        is_public=False
    )
    test_session.add(dataset)
    await test_session.commit()
    await test_session.refresh(dataset)
    return dataset


@pytest_asyncio.fixture
async def test_configuration(test_session: AsyncSession, test_dataset: Dataset) -> Configuration:
    """创建测试配置"""
    config = Configuration(
        name="Test Configuration",
        dataset_id=test_dataset.id,
        channels=["col1", "col2"],
        normalization="minmax",
        anomaly_enabled=False,
        window_size=100,
        stride=10,
        target_type="next",
        target_k=1,
        generated_filename="test_config.npz"
    )
    test_session.add(config)
    await test_session.commit()
    await test_session.refresh(config)
    return config


@pytest_asyncio.fixture
async def test_result(test_session: AsyncSession, test_dataset: Dataset, test_configuration: Configuration, test_user: User) -> Result:
    """创建测试结果"""
    result = Result(
        name="Test Result",
        dataset_id=test_dataset.id,
        configuration_id=test_configuration.id,
        user_id=test_user.id,
        filename="test_result.csv",
        filepath="/tmp/test_result.csv",
        algo_name="TestModel",
        algo_version="1.0.0",
        description="Test result for unit tests",
        row_count=100,
        metrics={
            "mse": 0.001,
            "rmse": 0.0316,
            "mae": 0.025,
            "r2": 0.95,
            "mape": 2.5
        }
    )
    test_session.add(result)
    await test_session.commit()
    await test_session.refresh(result)
    return result


# ============ 临时文件 Fixtures ============

@pytest.fixture
def temp_csv_file() -> Generator[str, None, None]:
    """创建临时 CSV 文件"""
    import pandas as pd
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        df = pd.DataFrame({
            'col1': range(100),
            'col2': [i * 0.1 for i in range(100)],
            'col3': ['a', 'b', 'c', 'd', 'e'] * 20
        })
        df.to_csv(f.name, index=False)
        yield f.name
    
    # 清理
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def temp_result_csv() -> Generator[str, None, None]:
    """创建临时结果 CSV 文件"""
    import pandas as pd
    import numpy as np
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        true_values = np.sin(np.linspace(0, 10, 100))
        pred_values = true_values + np.random.normal(0, 0.1, 100)
        
        df = pd.DataFrame({
            'true_value': true_values,
            'predicted_value': pred_values
        })
        df.to_csv(f.name, index=False)
        yield f.name
    
    # 清理
    if os.path.exists(f.name):
        os.unlink(f.name)

