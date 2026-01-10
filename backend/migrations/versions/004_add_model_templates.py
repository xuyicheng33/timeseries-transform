"""add model_templates table

Revision ID: 004_add_model_templates
Revises: 003_add_experiments
Create Date: 2026-01-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_model_templates'
down_revision: Union[str, None] = '003_add_experiments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建模型模板表
    op.create_table(
        'model_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('version', sa.String(50), default='1.0'),
        sa.Column('category', sa.String(50), default='deep_learning'),
        sa.Column('hyperparameters', sa.JSON(), default=dict),
        sa.Column('training_config', sa.JSON(), default=dict),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('task_types', sa.JSON(), default=list),
        sa.Column('recommended_features', sa.Text(), default=''),
        sa.Column('is_system', sa.Boolean(), default=False),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_templates_id'), 'model_templates', ['id'], unique=False)
    op.create_index(op.f('ix_model_templates_name'), 'model_templates', ['name'], unique=False)
    op.create_index(op.f('ix_model_templates_user_id'), 'model_templates', ['user_id'], unique=False)
    
    # 为 configurations 表添加 model_template_id 列
    op.add_column('configurations', sa.Column('model_template_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_configurations_model_template_id',
        'configurations', 'model_templates',
        ['model_template_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_configurations_model_template_id'), 'configurations', ['model_template_id'], unique=False)
    
    # 为 results 表添加 model_template_id 列
    op.add_column('results', sa.Column('model_template_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_results_model_template_id',
        'results', 'model_templates',
        ['model_template_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_results_model_template_id'), 'results', ['model_template_id'], unique=False)


def downgrade() -> None:
    # 移除 results 表的 model_template_id 列
    op.drop_index(op.f('ix_results_model_template_id'), table_name='results')
    op.drop_constraint('fk_results_model_template_id', 'results', type_='foreignkey')
    op.drop_column('results', 'model_template_id')
    
    # 移除 configurations 表的 model_template_id 列
    op.drop_index(op.f('ix_configurations_model_template_id'), table_name='configurations')
    op.drop_constraint('fk_configurations_model_template_id', 'configurations', type_='foreignkey')
    op.drop_column('configurations', 'model_template_id')
    
    # 删除模型模板表
    op.drop_index(op.f('ix_model_templates_user_id'), table_name='model_templates')
    op.drop_index(op.f('ix_model_templates_name'), table_name='model_templates')
    op.drop_index(op.f('ix_model_templates_id'), table_name='model_templates')
    op.drop_table('model_templates')

