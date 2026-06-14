"""
_utils.py
---------
Internal utility helpers shared across detector sub-modules.

Do not import from outside ``src`` — use ``src.detector`` for the public API.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from functools import lru_cache
from typing import Optional

from . import config

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def _bytes_to_gb(value) -> float:
    """Convert a byte value to GB, rounded to 1 decimal place."""
    try:
        return round(float(value) / (1024.0 ** 3), 1)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value, default: int = 0) -> int:
    """Parse an integer safely, returning *default* on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def _run_command(command: list[str]) -> str:
    """Run a subprocess command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=config.COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            log.debug("Command %s exited with code %d", command, result.returncode)
            return ""
        return (result.stdout or "").strip()
    except FileNotFoundError:
        log.debug("Command not found: %s", command[0])
        return ""
    except subprocess.TimeoutExpired:
        log.debug("Command timed out: %s", command)
        return ""
    except Exception as exc:  # noqa: BLE001
        log.debug("Command %s raised %s", command, exc)
        return ""


def _run_powershell(script: str) -> str:
    """Run a PowerShell one-liner and return its stdout."""
    return _run_command([*config.DETECTOR_COMMANDS["powershell"], script])


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def _read_text_file(path: str) -> str:
    """Read a text file, returning empty string if unavailable."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read().strip()
    except OSError as exc:
        log.debug("Could not read %s: %s", path, exc)
        return ""


# ---------------------------------------------------------------------------
# String / version helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _which(command: str) -> bool:
    """Return True if *command* is available in PATH (cached)."""
    return shutil.which(command) is not None


def _parse_first_version(text: str) -> Optional[str]:
    """Extract the first SemVer-style version string from *text*."""
    if not text:
        return None
    match = re.search(config.DETECTOR_REGEX["version"], text)
    return match.group(1) if match else None
