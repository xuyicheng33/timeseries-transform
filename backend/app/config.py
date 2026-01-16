import os
import secrets
from pathlib import Path
from typing import Optional
from pydantic import PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Demo"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./timeseries.db"
    
    # JWT Authentication
    # 生产环境必须通过环境变量设置！
    # 默认值仅用于开发环境，每次启动随机生成
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 内部缓存：进程内只生成一次的 JWT 密钥（使用 PrivateAttr 避免被当成 settings 字段）
    _cached_jwt_secret: Optional[str] = PrivateAttr(default=None)
    
    # Data Isolation
    ENABLE_DATA_ISOLATION: bool = False  # False = 团队共享模式, True = 用户隔离模式
    
    # File Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATASETS_DIR: Path = UPLOAD_DIR / "datasets"
    RESULTS_DIR: Path = UPLOAD_DIR / "results"
    CACHE_DIR: Path = UPLOAD_DIR / "cache"
    
    # File Upload Limits
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: set = {".csv"}
    
    # Data Preview
    PREVIEW_ROWS: int = 100
    
    # Large File Protection
    MAX_ROWS_FOR_FULL_ANALYSIS: int = 500000  # 超过此行数使用采样分析
    SAMPLE_SIZE_FOR_LARGE_FILES: int = 100000  # 大文件采样行数
    
    # Downsampling
    DEFAULT_MAX_POINTS: int = 2000
    DOWNSAMPLE_THRESHOLD: int = 5000
    
    # Cache Settings
    CACHE_MAX_AGE_DAYS: int = 7  # 缓存最大保留天数
    CACHE_MAX_SIZE_MB: int = 1024  # 缓存最大大小 (MB)
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # pydantic-settings v2 推荐写法
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    def get_jwt_secret_key(self) -> str:
        """
        获取 JWT 密钥（带进程内缓存）
        
        重要：此方法确保在同一进程内只生成一次密钥，
        避免 DEBUG 模式下多次调用导致 Token 校验不一致。
        
        外部代码应通过 app.services.auth 模块获取密钥，
        而不是直接调用此方法，以确保一致性。
        
        - 如果设置了环境变量，使用环境变量的值
        - 如果是开发模式且未设置，生成随机密钥（进程内缓存）
        - 如果是生产模式且未设置，抛出异常
        """
        # 如果已配置环境变量，直接返回
        if self.JWT_SECRET_KEY:
            return self.JWT_SECRET_KEY
        
        # 检查进程内缓存
        if self._cached_jwt_secret is not None:
            return self._cached_jwt_secret
        
        if self.DEBUG:
            # 开发模式：生成随机密钥并缓存（警告用户）
            import warnings
            self._cached_jwt_secret = secrets.token_urlsafe(32)
            warnings.warn(
                "\n" + "=" * 60 + "\n"
                "警告：JWT_SECRET_KEY 未设置，使用随机生成的密钥。\n"
                "这仅适用于开发环境，每次重启后 Token 将失效。\n"
                "生产环境请设置 JWT_SECRET_KEY 环境变量！\n"
                "=" * 60,
                UserWarning
            )
            return self._cached_jwt_secret
        else:
            # 生产模式：必须设置
            raise RuntimeError(
                "生产环境必须设置 JWT_SECRET_KEY 环境变量！\n"
                "可以使用以下命令生成：python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )


# 创建全局设置实例
settings = Settings()

# 注意：目录创建已移至 lifespan 初始化，避免 import 时的副作用


def init_directories() -> None:
    """
    初始化必要的目录
    应在应用启动时调用（lifespan），而不是 import 时
    """
    for dir_path in [settings.DATASETS_DIR, settings.RESULTS_DIR, settings.CACHE_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
