import logging
import os
from pathlib import Path

from semver import Version

__author__ = "HeiGIT"
__version__: Version = Version.parse("0.1.0")

project_root_dir = Path(__file__).parent.parent
project_config_dir: Path = project_root_dir / "config"
project_data_dir: Path = project_root_dir / "data"


class AnsiColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        start_style = {
            "DEBUG": "\033[90m",
            "INFO": "\033[0m",
            "WARNING": "\033[93m",
            "ERROR": "\033[31m",
            "CRITICAL": "\033[91m\033[91m",
        }.get(record.levelname, "\033[0m")
        return f"{start_style}{super().format(record)}\033[0m"


log_level = os.environ.get("XMIN_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger()
logger.handlers.clear()

logger.setLevel(log_level)

console_handler = logging.StreamHandler()
console_handler.setFormatter(AnsiColorFormatter("%(levelname)s: %(message)s"))
logger.addHandler(console_handler)

logging.getLogger("pyogrio").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
