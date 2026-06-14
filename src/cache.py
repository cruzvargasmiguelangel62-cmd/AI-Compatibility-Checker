# -*- coding: utf-8 -*-
"""
cache.py
--------
Persistent cache for hardware/software snapshots.

Saves the result of detect_system() to disk so the GUI starts instantly
on subsequent launches. Automatically refreshes in the background when the
cache is stale, and invalidates it when the machine configuration changes
(new GPU driver, different RAM, OS update, etc.).

Usage
-----
    from .cache import get_snapshot, invalidate

    # Returns immediately from disk; refreshes in background if stale.
    snapshot = get_snapshot()

    # Force a fresh scan (e.g. user clicks "Re-scan hardware").
    snapshot = get_snapshot(force_refresh=True)

    # Wipe the cache (e.g. on uninstall / settings reset).
    invalidate()
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import threading
import time
from dataclasses import asdict, dataclass
from typing import Callable, Optional

from . import config

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# How long a cache entry is considered "fresh" (seconds). Default: 6 hours.
CACHE_TTL_SECONDS: int = int(os.environ.get("AI_CHECKER_CACHE_TTL", 6 * 3600))

# Cache schema version — bump this whenever the snapshot shape changes.
CACHE_VERSION: str = "2"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _cache_path() -> str:
    return os.path.join(config.CURRENT_DIR, "data", "hw_cache.json")


# ---------------------------------------------------------------------------
# Machine fingerprint
# ---------------------------------------------------------------------------


def _machine_fingerprint() -> str:
    """
    A short hash of stable machine traits.

    If the fingerprint changes between runs (e.g. user swapped a GPU,
    upgraded RAM, or updated their OS), the cache is automatically invalidated.
    """
    traits = "|".join([
        platform.node(),           # hostname
        platform.machine(),        # x86_64 / arm64 / …
        platform.system(),         # Windows / Darwin / Linux
        platform.release(),        # kernel / OS version
        str(_ram_hint()),          # installed RAM in GB (rounded)
    ])
    return hashlib.sha256(traits.encode()).hexdigest()[:16]


def _ram_hint() -> int:
    """Quick RAM estimate (no psutil) for fingerprinting only."""
    system = platform.system()
    try:
        if system == "Darwin":
            import subprocess
            out = subprocess.check_output(
                config.DETECTOR_COMMANDS["macos_memsize"], timeout=2, text=True
            ).strip()
            return round(int(out) / (1024 ** 3))
        if system == "Linux":
            with open(config.DETECTOR_PATHS["linux_meminfo"], encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal:"):
                        return round(int(line.split()[1]) / (1024 ** 2))
        if system == "Windows":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            mem = ctypes.c_ulonglong(0)
            kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem))
            return round(mem.value / (1024 ** 2))
    except Exception:
        pass
    return 0


# ---------------------------------------------------------------------------
# Cache envelope
# ---------------------------------------------------------------------------


@dataclass
class CacheEnvelope:
    version: str
    fingerprint: str
    saved_at: float          # Unix timestamp
    snapshot: dict           # raw dict from SystemSnapshot.to_dict()
    ttl_seconds: int = CACHE_TTL_SECONDS

    @property
    def age_seconds(self) -> float:
        return time.time() - self.saved_at

    @property
    def is_stale(self) -> bool:
        return self.age_seconds > self.ttl_seconds

    @property
    def is_expired(self) -> bool:
        """Truly expired = stale + beyond grace period (2× TTL)."""
        return self.age_seconds > self.ttl_seconds * 2

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEnvelope":
        return cls(
            version=data["version"],
            fingerprint=data["fingerprint"],
            saved_at=float(data["saved_at"]),
            snapshot=data["snapshot"],
            ttl_seconds=int(data.get("ttl_seconds", CACHE_TTL_SECONDS)),
        )


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------


def _read_envelope() -> Optional[CacheEnvelope]:
    path = _cache_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        envelope = CacheEnvelope.from_dict(data)

        # Reject mismatched schema versions immediately
        if envelope.version != CACHE_VERSION:
            log.debug("Cache version mismatch (%s vs %s) — discarding.", envelope.version, CACHE_VERSION)
            return None

        # Reject if the machine has changed since the cache was written
        current_fp = _machine_fingerprint()
        if envelope.fingerprint != current_fp:
            log.debug("Machine fingerprint changed — discarding cache.")
            return None

        return envelope
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        log.warning("Corrupt cache file (%s) — discarding: %s", path, exc)
        return None
    except OSError as exc:
        log.warning("Could not read cache: %s", exc)
        return None


def _write_envelope(snapshot_dict: dict) -> None:
    path = _cache_path()
    envelope = CacheEnvelope(
        version=CACHE_VERSION,
        fingerprint=_machine_fingerprint(),
        saved_at=time.time(),
        snapshot=snapshot_dict,
    )
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(envelope.to_dict(), fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)   # atomic on all platforms
        log.debug("Cache written to %s", path)
    except OSError as exc:
        log.warning("Could not write cache: %s", exc)


# ---------------------------------------------------------------------------
# Background refresh
# ---------------------------------------------------------------------------

_refresh_lock = threading.Lock()
_refresh_thread: Optional[threading.Thread] = None


def _run_detection(force_fresh: bool = False) -> dict:
    """Import lazily to avoid circular imports and slow startup."""
    from .detector import clear_detection_caches, detect_system
    if force_fresh:
        clear_detection_caches()
    return detect_system().to_dict()


def _background_refresh(on_done: Optional[Callable[[dict], None]] = None) -> None:
    """Refresh the cache in a daemon thread, then call *on_done* if provided."""
    global _refresh_thread

    with _refresh_lock:
        if _refresh_thread and _refresh_thread.is_alive():
            log.debug("Background refresh already running — skipping.")
            return

        def _worker() -> None:
            log.debug("Background hardware refresh started.")
            try:
                snapshot = _run_detection(force_fresh=True)
                _write_envelope(snapshot)
                log.debug("Background hardware refresh complete.")
                if on_done:
                    on_done(snapshot)
            except Exception as exc:
                log.error("Background hardware refresh failed: %s", exc)

        _refresh_thread = threading.Thread(target=_worker, daemon=True, name="hw-cache-refresh")
        _refresh_thread.start()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_snapshot(
    force_refresh: bool = False,
    on_background_done: Optional[Callable[[dict], None]] = None,
) -> dict:
    """
    Return the hardware/software snapshot as a plain dict.

    Behaviour
    ---------
    - **Fresh cache**: returned instantly from disk.
    - **Stale cache**: returned from disk immediately; background thread
      refreshes and calls *on_background_done(new_snapshot)* when done.
      Pass a GUI callback here to update the UI without blocking it.
    - **Missing / expired / fingerprint mismatch**: blocks briefly while
      running a fresh detection synchronously, then saves to cache.
    - **force_refresh=True**: always runs a fresh detection (synchronous).

    Parameters
    ----------
    force_refresh:
        Skip the cache entirely and run a fresh hardware scan.
    on_background_done:
        Optional callable invoked with the new snapshot dict after a
        background refresh completes. Useful for updating the GUI.
        Called from a daemon thread — use your GUI's thread-safe mechanism
        (e.g. ``wx.CallAfter``, ``root.after``, ``QMetaObject.invokeMethod``).
    """
    if force_refresh:
        log.debug("Force refresh requested.")
        snapshot = _run_detection(force_fresh=True)
        _write_envelope(snapshot)
        return snapshot

    envelope = _read_envelope()

    if envelope is None:
        # No usable cache — block and scan now
        log.debug("No usable cache — running synchronous detection.")
        snapshot = _run_detection(force_fresh=True)
        _write_envelope(snapshot)
        return snapshot

    if envelope.is_stale:
        # Return stale data immediately; refresh in background
        log.debug("Cache is stale (%.0fs old) — serving stale, refreshing in background.", envelope.age_seconds)
        _background_refresh(on_done=on_background_done)

    return envelope.snapshot


def get_cached_snapshot() -> Optional[dict]:
    """Return the cached snapshot only, without triggering a fresh scan."""
    envelope = _read_envelope()
    if envelope is None:
        return None
    return envelope.snapshot


def invalidate() -> None:
    """Delete the on-disk cache (e.g. on settings reset or uninstall)."""
    path = _cache_path()
    try:
        if os.path.exists(path):
            os.remove(path)
            log.debug("Cache invalidated.")
    except OSError as exc:
        log.warning("Could not invalidate cache: %s", exc)


def cache_info() -> Optional[dict]:
    """
    Return metadata about the current cache entry, or None if absent.

    Useful for displaying "Last scanned X minutes ago" in the GUI.

    Returns a dict with keys:
        saved_at (float)  — Unix timestamp of the last scan
        age_seconds (float)
        is_stale (bool)
        fingerprint (str)
    """
    envelope = _read_envelope()
    if envelope is None:
        return None
    return {
        "saved_at": envelope.saved_at,
        "age_seconds": envelope.age_seconds,
        "is_stale": envelope.is_stale,
        "fingerprint": envelope.fingerprint,
    }
