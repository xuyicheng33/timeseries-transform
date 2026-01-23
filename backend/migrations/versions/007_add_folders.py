"""add folders and dataset.folder_id

Revision ID: 007_add_folders
Revises: 006_add_sort_order_and_config_user
Create Date: 2026-01-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_add_folders"
down_revision: Union[str, None] = "006_add_sort_order_and_config_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_folders_id"), "folders", ["id"], unique=False)
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"], unique=False)
    op.create_index("ix_folders_sort_order", "folders", ["sort_order"], unique=False)
    op.create_index("ix_folders_user_id", "folders", ["user_id"], unique=False)
    op.create_index(
        "uq_folders_root_name",
        "folders",
        ["name"],
        unique=True,
        sqlite_where=sa.text("parent_id IS NULL"),
        postgresql_where=sa.text("parent_id IS NULL"),
    )

    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("folder_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_datasets_folder_id", ["folder_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_datasets_folder_id",
            "folders",
            ["folder_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("datasets", schema=None) as batch_op:
        batch_op.drop_constraint("fk_datasets_folder_id", type_="foreignkey")
        batch_op.drop_index("ix_datasets_folder_id")
        batch_op.drop_column("folder_id")

    op.drop_index("uq_folders_root_name", table_name="folders")
    op.drop_index("ix_folders_user_id", table_name="folders")
    op.drop_index("ix_folders_sort_order", table_name="folders")
    op.drop_index("ix_folders_parent_id", table_name="folders")
    op.drop_index(op.f("ix_folders_id"), table_name="folders")
    op.drop_table("folders")

