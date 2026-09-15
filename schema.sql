-- Схема данных. Вариант 8: Учёт успеваемости студентов
-- groups (1) -> students (N): у группы много студентов
-- groups (1) + disciplines (1) -> study_plans (N): что изучают
-- students (1) + disciplines (1) -> grades (N): кто что сдал

CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,   -- напр. 'ИМ-31'
    year INTEGER NOT NULL        -- год набора, напр. 2026
);
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fio TEXT NOT NULL,
    group_id INTEGER NOT NULL REFERENCES groups(id),
    student_no TEXT UNIQUE NOT NULL  -- номер зачётки
);
CREATE TABLE IF NOT EXISTS disciplines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    credits INTEGER NOT NULL DEFAULT 3
);
CREATE TABLE IF NOT EXISTS study_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES groups(id),
    discipline_id INTEGER NOT NULL REFERENCES disciplines(id),
    semester INTEGER NOT NULL,
    UNIQUE(group_id, discipline_id, semester)
);
CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    discipline_id INTEGER NOT NULL REFERENCES disciplines(id),
    semester INTEGER NOT NULL,
    value INTEGER NOT NULL CHECK(value BETWEEN 2 AND 5),
    UNIQUE(student_id, discipline_id, semester)
);
