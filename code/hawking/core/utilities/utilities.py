import sys
import json
from pathlib import Path

import hawking

PLATFORM = sys.platform


def get_root_path() -> Path:
    """Find the installation root from the marked Hawking package."""

    if not getattr(hawking, "HAWKING_ROOT", False):
        raise RuntimeError("The Hawking package root marker is missing.")

    package_directory = Path(hawking.__file__).resolve().parent
    return package_directory.parent.parent


def load_json(path: Path) -> dict:
    with open(path) as fd:
        return json.load(fd)


def save_json(path: Path, data: dict):
    with open(path, "w") as fd:
        json.dump(data, fd)


def is_linux():
    return "linux" in PLATFORM


def is_windows():
    return "win" in PLATFORM


def get_weekday_name_from_day_of_week(day_of_week: int) -> str:
    ## Basically the inverse of: https://docs.python.org/3/library/datetime.html#datetime.date.weekday

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return day_names[day_of_week]
