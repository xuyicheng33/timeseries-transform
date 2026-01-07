"""initial tables - datasets, configurations, results

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-08

初始迁移：创建基础表结构
- datasets: 数据集表
- configurations: 配置表
- results: 结果表
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库 - 创建初始表"""
    
    # 创建 datasets 表
    op.create_table(
        'datasets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('filepath', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), default=0),
        sa.Column('row_count', sa.Integer(), default=0),
        sa.Column('column_count', sa.Integer(), default=0),
        sa.Column('columns', sa.JSON(), default=list),
        sa.Column('encoding', sa.String(length=50), default='utf-8'),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_datasets_id'), 'datasets', ['id'], unique=False)

    # 创建 configurations 表
    op.create_table(
        'configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('channels', sa.JSON(), default=list),
        sa.Column('normalization', sa.String(length=50), default='none'),
        sa.Column('anomaly_enabled', sa.Boolean(), default=False),
        sa.Column('anomaly_type', sa.String(length=50), default=''),
        sa.Column('injection_algorithm', sa.String(length=50), default=''),
        sa.Column('sequence_logic', sa.String(length=50), default=''),
        sa.Column('window_size', sa.Integer(), default=100),
        sa.Column('stride', sa.Integer(), default=1),
        sa.Column('target_type', sa.String(length=50), default='next'),
        sa.Column('target_k', sa.Integer(), default=1),
        sa.Column('generated_filename', sa.String(length=500), default=''),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_configurations_id'), 'configurations', ['id'], unique=False)
    op.create_index(op.f('ix_configurations_dataset_id'), 'configurations', ['dataset_id'], unique=False)

    # 创建 results 表
    op.create_table(
        'results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('configuration_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('filepath', sa.String(length=500), nullable=False),
        sa.Column('algo_name', sa.String(length=100), nullable=False),
        sa.Column('algo_version', sa.String(length=50), default=''),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('row_count', sa.Integer(), default=0),
        sa.Column('metrics', sa.JSON(), default=dict),
        sa.Column('code_filepath', sa.String(length=500), default=''),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['configuration_id'], ['configurations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_results_id'), 'results', ['id'], unique=False)
    op.create_index(op.f('ix_results_dataset_id'), 'results', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_results_configuration_id'), 'results', ['configuration_id'], unique=False)


def downgrade() -> None:
    """降级数据库 - 删除所有表"""
    op.drop_index(op.f('ix_results_configuration_id'), table_name='results')
    op.drop_index(op.f('ix_results_dataset_id'), table_name='results')
    op.drop_index(op.f('ix_results_id'), table_name='results')
    op.drop_table('results')
    
    op.drop_index(op.f('ix_configurations_dataset_id'), table_name='configurations')
    op.drop_index(op.f('ix_configurations_id'), table_name='configurations')
    op.drop_table('configurations')
    
    op.drop_index(op.f('ix_datasets_id'), table_name='datasets')
    op.drop_table('datasets')

