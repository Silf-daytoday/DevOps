"""Комментарий к оценке, существующие записи получают NULL."""

import sqlalchemy as sa
from alembic import op

revision = "002_grade_comment"
down_revision = "001_lr2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("grades", sa.Column("comment", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("grades", "comment")
