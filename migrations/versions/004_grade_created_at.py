"""Время новых записей; дата старых оценок остаётся неизвестной."""

import sqlalchemy as sa
from alembic import op

revision = "004_grade_created_at"
down_revision = "003_comment_limit"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("grades", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("grades", "created_at", server_default=sa.text("CURRENT_TIMESTAMP"))


def downgrade():
    op.drop_column("grades", "created_at")
