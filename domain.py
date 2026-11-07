"""Правила предметной области, не зависящие от Flask и PostgreSQL."""

import re

MAX_COMMENT_LENGTH = 500


def as_integer(value):
    """Принять целое число или его строковую запись без усечения дробей."""
    if type(value) is int:
        return value
    if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
        return int(value)
    raise ValueError("Ожидается целое число")


def grade_value_error(value):
    if type(value) is not int or value not in (2, 3, 4, 5):
        return "Оценка должна быть от 2 до 5"
    return None


def grade_context_error(student_exists, plan_exists):
    if not student_exists:
        return "Такого студента нет"
    if not plan_exists:
        return (
            "Нельзя ставить оценку: этой дисциплины НЕТ в учебном плане "
            "группы студента на этот семестр"
        )
    return None


def normalize_comment(value):
    """Пустой комментарий хранится как NULL; длина считается до обрезки пробелов."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Комментарий должен быть строкой")
    if len(value) > MAX_COMMENT_LENGTH:
        raise ValueError("Комментарий — не более 500 символов")
    return value.strip() or None
