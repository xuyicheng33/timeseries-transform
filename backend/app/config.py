import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Time Series Analysis Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./timeseries.db"
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Data Isolation
    ENABLE_DATA_ISOLATION: bool = False  # False = 团队共享模式
    
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
    
    # Downsampling
    DEFAULT_MAX_POINTS: int = 2000
    DOWNSAMPLE_THRESHOLD: int = 5000
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # pydantic-settings v2 推荐写法
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

for dir_path in [settings.DATASETS_DIR, settings.RESULTS_DIR, settings.CACHE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
