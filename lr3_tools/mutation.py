"""Два контролируемых мутанта в отдельном временном каталоге."""

import os
import shutil

# Дочерний pytest получает список аргументов и не использует shell.
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

from lr3_tools.common import ROOT


def main():
    source = (ROOT / "domain.py").read_text(encoding="utf-8")
    mutants = {
        "grade-six-allowed": ("value not in (2, 3, 4, 5)", "value not in (2, 3, 4, 5, 6)"),
        "missing-plan-allowed": ("if not plan_exists:", "if False:"),
    }
    for name, (old, new) in mutants.items():
        if source.count(old) != 1:
            raise RuntimeError(f"Мутационная точка {name} изменилась; обновите проверку")
        with tempfile.TemporaryDirectory(prefix="lr3-mutant-") as folder:
            target = Path(folder)
            (target / "domain.py").write_text(source.replace(old, new), encoding="utf-8")
            (target / "tests").mkdir()
            shutil.copy2(ROOT / "tests/unit/test_domain.py", target / "tests/test_domain.py")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(target)
            env["PYTEST_ADDOPTS"] = ""
            # Абсолютный Python текущего venv, argv, shell=False;
            # запускаются только unit-тесты из временной копии, без БД.
            result = subprocess.run(  # nosec B603
                [
                    str(Path(sys.executable).absolute()),
                    "-m",
                    "pytest",
                    "-q",
                    "tests",
                    "--import-mode=importlib",
                ],
                cwd=target,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            expected_test = (
                "test_forbidden_grades[6]" if name == "grade-six-allowed" else "test_missing_plan"
            )
            if result.returncode != 1 or expected_test not in result.stdout:
                raise RuntimeError(f"Мутант {name} НЕ обнаружен: {result.stdout} {result.stderr}")
            print(f"MUTATION KILLED: {name}")
    print("MUTATION OK: оба изменения обнаружены, рабочий код не изменялся")


if __name__ == "__main__":
    main()
