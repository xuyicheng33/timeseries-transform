from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float
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
    encoding = Column(String(50), default="utf-8")  # 修复：存储检测到的编码
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Configuration(Base):
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_id = Column(Integer, nullable=False)
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


class Result(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_id = Column(Integer, nullable=False)
    configuration_id = Column(Integer, nullable=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), default="")
    description = Column(Text, default="")
    row_count = Column(Integer, default=0)
    metrics = Column(JSON, default=dict)
    code_filepath = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
