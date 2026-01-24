"""add folder parent/name uniqueness

Revision ID: 009_add_folder_parent_name_unique
Revises: 008_add_folder_description
Create Date: 2026-01-24

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "009_add_folder_parent_name_unique"
down_revision: Union[str, None] = "008_add_folder_description"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_folders_parent_id_name",
        "folders",
        ["parent_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_folders_parent_id_name",
        "folders",
        type_="unique",
    )

