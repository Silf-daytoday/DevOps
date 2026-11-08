"""Ограничение комментария защищает также прямые SQL-вставки."""

from alembic import op

revision = "003_comment_limit"
down_revision = "002_grade_comment"
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint(
        "ck_grades_comment_length", "grades", "comment IS NULL OR char_length(comment) <= 500"
    )


def downgrade():
    op.drop_constraint("ck_grades_comment_length", "grades", type_="check")
