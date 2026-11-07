import pytest

from domain import as_integer, grade_context_error, grade_value_error, normalize_comment


@pytest.mark.parametrize("value", [2, 3, 4, 5])
def test_allowed_grades(value):
    assert grade_value_error(value) is None


@pytest.mark.parametrize("value", [1, 6, 0, -1, 10, True, False, None, "5", 2.5])
def test_forbidden_grades(value):
    assert grade_value_error(value) is not None


def test_missing_student():
    assert "студента нет" in grade_context_error(False, False)


def test_missing_plan():
    assert "учебном плане" in grade_context_error(True, False)


def test_plan_allows_grade():
    assert grade_context_error(True, True) is None


@pytest.mark.parametrize("value,expected", [(2, 2), ("5", 5), (" 12 ", 12), ("-2", -2), ("+5", 5)])
def test_integer(value, expected):
    assert as_integer(value) == expected


@pytest.mark.parametrize("value", [True, False, 2.5, 2.0, "2.5", [], {}, None, "x", ""])
def test_invalid_integer(value):
    with pytest.raises(ValueError):
        as_integer(value)


@pytest.mark.parametrize(
    "value,expected",
    [(None, None), ("", None), ("  ", None), (" текст ", "текст"), ("я" * 500, "я" * 500)],
)
def test_comment(value, expected):
    assert normalize_comment(value) == expected


@pytest.mark.parametrize("value", ["я" * 501, " " * 501, 5, [], {}, True])
def test_invalid_comment(value):
    with pytest.raises(ValueError):
        normalize_comment(value)
