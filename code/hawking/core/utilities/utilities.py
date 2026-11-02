import sys
import json
from pathlib import Path

PLATFORM = sys.platform


def get_root_path() -> Path:
    """Find the installation root containing the configuration directory."""

    ## TODO: This should likely walk the tree to find a root __init__ in the code dir, then that folder's parent is the
    ## root? The current bandaided implementation is too brittle.
    for path in Path(__file__).resolve().parents:
        if (path / "configuration" / "config.json").is_file() or (path / "config.json").is_file():
            return path
    raise FileNotFoundError("Unable to locate the Hawking installation root (configuration/config.json).")


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
