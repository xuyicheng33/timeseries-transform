from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    dataset = relationship("Dataset", back_populates="configurations")


class Result(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_id = Column(Integer, ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False, index=True)
    configuration_id = Column(Integer, ForeignKey('configurations.id', ondelete='SET NULL'), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    # 重命名：避免 Pydantic model_ 命名空间警告
    algo_name = Column(String(100), nullable=False)
    algo_version = Column(String(50), default="")
    description = Column(Text, default="")
    row_count = Column(Integer, default=0)
    metrics = Column(JSON, default=dict)
    code_filepath = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    dataset = relationship("Dataset", back_populates="results")
    configuration = relationship("Configuration")
