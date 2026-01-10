"""add experiments table

Revision ID: 003_add_experiments
Revises: 002_add_users
Create Date: 2026-01-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_experiments'
down_revision: Union[str, None] = '002_add_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建实验组表
    op.create_table(
        'experiments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('objective', sa.Text(), default=''),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('tags', sa.JSON(), default=list),
        sa.Column('conclusion', sa.Text(), default=''),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('dataset_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_experiments_id'), 'experiments', ['id'], unique=False)
    op.create_index(op.f('ix_experiments_user_id'), 'experiments', ['user_id'], unique=False)
    op.create_index(op.f('ix_experiments_dataset_id'), 'experiments', ['dataset_id'], unique=False)
    
    # 创建实验组-结果关联表
    op.create_table(
        'experiment_results',
        sa.Column('experiment_id', sa.Integer(), nullable=False),
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['experiment_id'], ['experiments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['result_id'], ['results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('experiment_id', 'result_id')
    )


def downgrade() -> None:
    op.drop_table('experiment_results')
    op.drop_index(op.f('ix_experiments_dataset_id'), table_name='experiments')
    op.drop_index(op.f('ix_experiments_user_id'), table_name='experiments')
    op.drop_index(op.f('ix_experiments_id'), table_name='experiments')
    op.drop_table('experiments')

