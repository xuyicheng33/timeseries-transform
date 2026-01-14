"""添加 Dataset.sort_order 和 Configuration.user_id 字段

Revision ID: 006_add_sort_order_and_config_user
Revises: 005_set_admin_user
Create Date: 2025-01-15

功能说明：
1. Dataset.sort_order: 数据集排序权重，越小越靠前，管理员可调整
2. Configuration.user_id: 配置创建者ID，用于权限控制（本人或管理员可编辑删除）

迁移策略：
- sort_order 按 id 填充递增值，避免全 0 导致排序不稳定
- user_id 默认为 NULL，历史数据仅管理员可修改
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_sort_order_and_config_user'
down_revision: Union[str, None] = '005_set_admin_user'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加新字段"""
    # 1. 添加 Dataset.sort_order 字段
    op.add_column('datasets', sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'))
    op.create_index('ix_datasets_sort_order', 'datasets', ['sort_order'])
    
    # 按 id 填充 sort_order，保证初始排序稳定
    op.execute("UPDATE datasets SET sort_order = id")
    
    # 2. 添加 Configuration.user_id 字段
    op.add_column('configurations', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index('ix_configurations_user_id', 'configurations', ['user_id'])
    
    # 添加外键约束（SQLite 不支持 ALTER TABLE ADD CONSTRAINT，但 alembic 会处理）
    # 注意：SQLite 的外键约束需要在创建表时定义，这里仅作为文档说明
    # 实际外键关系通过 ORM 层面的 relationship 维护
    
    # 3. 将所有数据集设为公开（统一由管理员管理）
    op.execute("UPDATE datasets SET is_public = 1")


def downgrade() -> None:
    """回滚：删除新字段"""
    # 删除 Configuration.user_id
    op.drop_index('ix_configurations_user_id', table_name='configurations')
    op.drop_column('configurations', 'user_id')
    
    # 删除 Dataset.sort_order
    op.drop_index('ix_datasets_sort_order', table_name='datasets')
    op.drop_column('datasets', 'sort_order')

