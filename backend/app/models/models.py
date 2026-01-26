from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    """获取当前 UTC 时间（timezone-aware）"""
    return datetime.now(UTC)


# 实验组-结果关联表（多对多）
experiment_results = Table(
    "experiment_results",
    Base.metadata,
    Column("experiment_id", Integer, ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True),
    Column("result_id", Integer, ForeignKey("results.id", ondelete="CASCADE"), primary_key=True),
)


class ModelTemplate(Base):
    """模型模板 - 预定义的模型配置"""

    __tablename__ = "model_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # 模型名称 (LSTM, Transformer, TCN...)
    version = Column(String(50), default="1.0")  # 版本号
    category = Column(String(50), default="deep_learning")  # 类别: deep_learning, traditional, ensemble

    # 模型超参数（JSON 格式，灵活存储不同模型的参数）
    hyperparameters = Column(JSON, default=dict)
    # 示例超参数结构:
    # {
    #   "hidden_size": 64,
    #   "num_layers": 2,
    #   "dropout": 0.1,
    #   "learning_rate": 0.001,
    #   "batch_size": 32,
    #   "epochs": 100
    # }

    # 训练配置
    training_config = Column(JSON, default=dict)
    # 示例:
    # {
    #   "optimizer": "adam",
    #   "loss_function": "mse",
    #   "early_stopping": true,
    #   "patience": 10
    # }

    # 适用场景描述
    description = Column(Text, default="")
    # 适用的任务类型: prediction, reconstruction, anomaly_detection
    task_types = Column(JSON, default=list)
    # 推荐的数据特征
    recommended_features = Column(Text, default="")

    # 是否为系统预置模板
    is_system = Column(Boolean, default=False)
    # 是否公开（用户创建的模板）
    is_public = Column(Boolean, default=False)

    # 用户关联（系统模板 user_id 为 NULL）
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # 使用统计
    usage_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    user = relationship("User", back_populates="model_templates")


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
    model_templates = relationship("ModelTemplate", back_populates="user")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    parent_id = Column(Integer, ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True)
    sort_order = Column(Integer, default=0, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    parent = relationship("Folder", remote_side=[id], backref="children")
    user = relationship("User")
    datasets = relationship("Dataset", back_populates="folder")


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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    is_public = Column(Boolean, default=True)  # 是否公开（默认公开，由管理员统一管理）
    # 排序权重，越小越靠前
    sort_order = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    user = relationship("User", back_populates="datasets")
    folder = relationship("Folder", back_populates="datasets")
    configurations = relationship("Configuration", back_populates="dataset", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="dataset", cascade="all, delete-orphan")


class Configuration(Base):
    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    # 可选关联模型模板
    model_template_id = Column(
        Integer, ForeignKey("model_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 用户关联（用于权限控制：本人或管理员可编辑删除）
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
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
    model_template = relationship("ModelTemplate")
    user = relationship("User")


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    configuration_id = Column(Integer, ForeignKey("configurations.id", ondelete="SET NULL"), nullable=True, index=True)
    # 可选关联模型模板（便于追溯使用了哪个模型配置）
    model_template_id = Column(
        Integer, ForeignKey("model_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 用户关联（用于数据隔离）
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
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
    model_template = relationship("ModelTemplate")
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # 关联的数据集（可选，用于快速筛选）
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    # 时间戳
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关系
    user = relationship("User", back_populates="experiments")
    dataset = relationship("Dataset")
    results = relationship("Result", secondary=experiment_results, back_populates="experiments")
