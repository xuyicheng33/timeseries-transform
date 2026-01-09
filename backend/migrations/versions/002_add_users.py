"""add users table and user_id fields

Revision ID: 002_add_users
Revises: 001_initial
Create Date: 2025-01-08

添加用户认证相关表和字段：
- users: 用户表
- datasets.user_id: 数据集所属用户（可选，用于数据隔离）
- datasets.is_public: 是否公开（团队共享）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_users'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库 - 添加用户表"""
    
    # 创建 users 表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), default=''),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 为 datasets 表添加 user_id 和 is_public 字段
    # 使用批量模式（SQLite 兼容）
    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('is_public', sa.Boolean(), server_default='0', nullable=False))
        batch_op.create_foreign_key(
            'fk_datasets_user_id', 
            'users', 
            ['user_id'], 
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('ix_datasets_user_id', ['user_id'], unique=False)

    # 为 results 表添加 user_id 字段
    with op.batch_alter_table('results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_results_user_id',
            'users',
            ['user_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index('ix_results_user_id', ['user_id'], unique=False)


def downgrade() -> None:
    """降级数据库 - 删除用户表和相关字段"""
    
    # 从 results 表删除 user_id 字段
    with op.batch_alter_table('results', schema=None) as batch_op:
        batch_op.drop_index('ix_results_user_id')
        batch_op.drop_constraint('fk_results_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')

    # 从 datasets 表删除 user_id 和 is_public 字段
    with op.batch_alter_table('datasets', schema=None) as batch_op:
        batch_op.drop_index('ix_datasets_user_id')
        batch_op.drop_constraint('fk_datasets_user_id', type_='foreignkey')
        batch_op.drop_column('is_public')
        batch_op.drop_column('user_id')

    # 删除 users 表
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')

