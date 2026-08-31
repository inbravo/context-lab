"""
logging_config.py — Shared logging setup for the Hospitality Group demo.

Log file : ../logs/hospitality.log  (RotatingFileHandler, 5 MB × 3 backups)
File     : DEBUG and above  (every detail)
Console  : INFO and above   (key events only — not noisy during normal runs)

All loggers are named under the "hosp" hierarchy so they can be tuned or
silenced together without touching the root logger or uvicorn's logging.

Usage in any module:
    import logging_config, logging
    logging_config.setup()
    log = logging.getLogger("hosp.<module>")
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# ─────────────────────────────────────────────────────

import logging
import logging.handlers
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "logs" / "hospitality.log"

_configured = False


def setup() -> None:
    """Configure the 'hosp' logger hierarchy. Safe to call multiple times."""
    global _configured
    if _configured:
        return
    _configured = True

    LOG_FILE.parent.mkdir(exist_ok=True)

    root = logging.getLogger("hosp")
    if root.handlers:
        return
    root.setLevel(logging.DEBUG)

    file_fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)-28s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter("%(levelname)-8s  %(name)s  %(message)s")

    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_fmt)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(console_fmt)

    root.addHandler(fh)
    root.addHandler(ch)
