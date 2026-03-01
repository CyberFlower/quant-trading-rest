import datetime
import os
from pathlib import Path

from .util import find_project_root


class LogLevel(enumerate):
    INFO, DEBUG, ERROR = range(3)


class LogWriter:
    _instance = None
    _mode = "quant"  # 기본값
    _company = None  # 기본값
    _category = "trading"  # 기본값 => output/log/trading/YYYYMMDD
    _project_root = find_project_root(Path(__file__).resolve())

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LogWriter, cls).__new__(cls)
        cls._apply_settings(*args, **kwargs)
        return cls._instance

    @classmethod
    def _apply_settings(cls, *args, **kwargs):
        if "mode" in kwargs and kwargs["mode"] is not None:
            cls._mode = kwargs["mode"]
        elif len(args) > 0 and args[0] is not None:
            cls._mode = args[0]

        if "company" in kwargs:
            cls._company = kwargs["company"]
        elif len(args) > 1:
            cls._company = args[1]

        if "category" in kwargs:
            cls._category = cls._normalize_category(kwargs["category"])
        elif len(args) > 2:
            cls._category = cls._normalize_category(args[2])

    @staticmethod
    def _normalize_category(category):
        if category is None:
            return "trading"
        normalized = str(category).strip().strip("/").strip("\\")
        if normalized == "":
            return "trading"
        return normalized.lower()

    def __init__(self, mode=None, company=None, category=None):
        if not hasattr(self, "_active_signature"):
            self._active_signature = None
        self._refresh_paths()

    def _refresh_paths(self):
        today = datetime.datetime.now().strftime("%Y%m%d")
        base_dir = LogWriter._project_root / "output" / "log"
        signature = (today, LogWriter._category, LogWriter._company, LogWriter._mode)
        if self._active_signature == signature:
            return

        log_dir = base_dir / LogWriter._category / today

        if LogWriter._company is None:
            log_dir = log_dir / LogWriter._mode
        else:
            log_dir = log_dir / LogWriter._company / LogWriter._mode

        os.makedirs(log_dir, exist_ok=True)
        self.info_file = str(log_dir / "info.txt")
        self.debug_file = str(log_dir / "debug.txt")
        self.error_file = str(log_dir / "error.txt")
        self._active_signature = signature

    def write_log(self, message, level=LogLevel.DEBUG):
        if level == LogLevel.INFO:
            file = self.info_file
        elif level == LogLevel.DEBUG:
            file = self.debug_file
        elif level == LogLevel.ERROR:
            file = self.error_file
        else:
            raise ValueError("Invalid log level: {}".format(level))

        with open(file, "a") as log_file:
            log_file.write(
                "[{}] {}\n".format(
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message
                )
            )


if __name__ == "__main__":
    logger = LogWriter(mode="isa", category="trading")
    LogWriter().write_log("This is an info message.", LogLevel.INFO)
    LogWriter().write_log("This is a debug message.", LogLevel.DEBUG)
    LogWriter().write_log("This is an error message.", LogLevel.ERROR)
