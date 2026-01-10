from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    """获取当前 UTC 时间（timezone-aware）"""
    return datetime.now(timezone.utc)


# 实验组-结果关联表（多对多）
experiment_results = Table(
    'experiment_results',
    Base.metadata,
    Column('experiment_id', Integer, ForeignKey('experiments.id', ondelete='CASCADE'), primary_key=True),
    Column('result_id', Integer, ForeignKey('results.id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), default="")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    last_login = Column(DateTime, nullable=True)
    
    # 关系
    datasets = relationship("Dataset", back_populates="user")
    results = relationship("Result", back_populates="user")
    experiments = relationship("Experiment", back_populates="user")


class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    columns = Column(JSON, default=list)
    encoding = Column(String(50), default="utf-8")
    description = Column(Text, default="")
    # 用户关联（用于数据隔离）
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    is_public = Column(Boolean, default=False)  # 是否公开（默认私有）
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # 关系
    user = relationship("User", back_populates="datasets")
    configurations = relationship("Configuration", back_populates="dataset", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="dataset", cascade="all, delete-orphan")


class Configuration(Base):
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False, index=True)
    channels = Column(JSON, default=list)
    normalization = Column(String(50), default="none")
    anomaly_enabled = Column(Boolean, default=False)
    anomaly_type = Column(String(50), default="")
    injection_algorithm = Column(String(50), default="")
    sequence_logic = Column(String(50), default="")
    window_size = Column(Integer, default=100)
    stride = Column(Integer, default=1)
    target_type = Column(String(50), default="next")
    target_k = Column(Integer, default=1)
    generated_filename = Column(String(500), default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # 关系
    dataset = relationship("Dataset", back_populates="configurations")


class Result(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False, index=True)
    configuration_id = Column(Integer, ForeignKey('configurations.id', ondelete='SET NULL'), nullable=True, index=True)
    # 用户关联（用于数据隔离）
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    # 算法信息
    algo_name = Column(String(100), nullable=False)
    algo_version = Column(String(50), default="")
    description = Column(Text, default="")
    row_count = Column(Integer, default=0)
    metrics = Column(JSON, default=dict)
    code_filepath = Column(String(500), default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # 关系
    user = relationship("User", back_populates="results")
    dataset = relationship("Dataset", back_populates="results")
    configuration = relationship("Configuration")
    experiments = relationship("Experiment", secondary=experiment_results, back_populates="results")


class Experiment(Base):
    """实验组模型"""
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    # 实验目标/假设
    objective = Column(Text, default="")
    # 实验状态: draft, running, completed, archived
    status = Column(String(50), default="draft")
    # 标签（JSON 数组）
    tags = Column(JSON, default=list)
    # 实验结论/备注
    conclusion = Column(Text, default="")
    # 用户关联
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    # 关联的数据集（可选，用于快速筛选）
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='SET NULL'), nullable=True, index=True)
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # 关系
    user = relationship("User", back_populates="experiments")
    dataset = relationship("Dataset")
    results = relationship("Result", secondary=experiment_results, back_populates="experiments")
