"""设置 admin 用户为管理员

Revision ID: 005_set_admin_user
Revises: 004_add_model_templates
Create Date: 2024-01-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_set_admin_user'
down_revision: Union[str, None] = '004_add_model_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """将 username 为 'admin' 的用户设置为管理员"""
    # 使用原生 SQL 更新，兼容 SQLite 和 PostgreSQL
    op.execute(
        "UPDATE users SET is_admin = 1 WHERE username = 'admin'"
    )


def downgrade() -> None:
    """撤销管理员设置"""
    op.execute(
        "UPDATE users SET is_admin = 0 WHERE username = 'admin'"
    )

