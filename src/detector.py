"""
detector.py
-----------
Public façade for the AI hardware/software compatibility detector.

Detects hardware and software configuration of the current machine.

Usage as library:
    from src.detector import detect_system, get_hardware, get_software

Usage as CLI:
    python -m src.detector
    python -m src.detector --hardware
    python -m src.detector --software --pretty
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from functools import lru_cache
from typing import Optional

# ---------------------------------------------------------------------------
# Re-export public API from sub-modules (API is unchanged for all callers)
# ---------------------------------------------------------------------------

from ._models import (  # noqa: F401 — re-exported
    GpuInfo,
    HardwareSnapshot,
    PythonInfo,
    CudaInfo,
    RocmInfo,
    CompilerInfo,
    SoftwareSnapshot,
    SystemSnapshot,
)
from ._cpu import check_avx2_support, get_cpu_name
from ._gpu_common import _get_nvidia_smi_gpus, _sort_gpus
from ._software import get_software

__all__ = [
    "detect_system",
    "get_hardware",
    "get_software",
    "clear_detection_caches",
    "SystemSnapshot",
    # data models
    "GpuInfo",
    "HardwareSnapshot",
    "PythonInfo",
    "CudaInfo",
    "RocmInfo",
    "CompilerInfo",
    "SoftwareSnapshot",
]

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RAM / OS helpers (kept here — no platform sub-module needed for these)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_installed_ram() -> Optional[float]:
    """Return total installed RAM in GB, or None if unavailable."""
    system = platform.system()

    if system == "Windows":
        try:
            import ctypes
            mem = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem))
            return round(mem.value / (1024.0 * 1024.0), 1)
        except Exception:
            try:
                import psutil
                return round(psutil.virtual_memory().total / (1024.0 ** 3), 1)
            except Exception:
                return None

    if system == "Darwin":
        from ._utils import _run_command, _safe_int
        from . import config
        out = _run_command(config.DETECTOR_COMMANDS["macos_memsize"])
        if out:
            raw = _safe_int(out)
            return round(raw / (1024.0 ** 3), 1) if raw else None
        return None

    if system == "Linux":
        from ._utils import _read_text_file
        from . import config
        for line in _read_text_file(config.DETECTOR_PATHS["linux_meminfo"]).splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2:
                    return round(float(parts[1]) / (1024.0 ** 2), 1)

    return None


@lru_cache(maxsize=1)
def get_os_pretty_name() -> str:
    """Return a human-readable OS version string."""
    from . import config
    from ._utils import _run_command, _read_text_file

    system = platform.system()
    try:
        if system == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            product_name,    _ = winreg.QueryValueEx(key, "ProductName")
            display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            current_build,   _ = winreg.QueryValueEx(key, "CurrentBuild")
            winreg.CloseKey(key)

            # Windows 11 falsely reports "Windows 10" in ProductName for
            # backward compatibility.  Build >= 22000 is officially Windows 11.
            try:
                if int(current_build) >= 22000 and "Windows 10" in product_name:
                    product_name = product_name.replace("Windows 10", "Windows 11")
            except (ValueError, TypeError):
                pass

            if display_version:
                return f"{product_name} (versión {display_version}, compilación {current_build})"
            return f"{product_name} (compilación {current_build})"

        if system == "Darwin":
            version = _run_command(config.DETECTOR_COMMANDS["macos_product_version"])
            build   = _run_command(config.DETECTOR_COMMANDS["macos_build_version"])
            if version and build:
                return f"macOS {version} ({build})"
            return f"macOS {version}" if version else f"macOS {platform.release()}"

        if system == "Linux":
            for line in _read_text_file(config.DETECTOR_PATHS["linux_os_release"]).splitlines():
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')

    except Exception as exc:
        log.debug("get_os_pretty_name: %s", exc)

    return f"{system} {platform.release()}"


def get_free_disk_space_gb(path: str = ".") -> float:
    """Return free disk space in GB for the partition containing *path*."""
    for candidate in (path, os.path.expanduser("~")):
        try:
            _, _, free = shutil.disk_usage(candidate)
            return round(free / (1024.0 ** 3), 1)
        except Exception:
            continue
    return 0.0


# ---------------------------------------------------------------------------
# Top-level builders
# ---------------------------------------------------------------------------


def get_hardware() -> HardwareSnapshot:
    """
    Collect hardware information.

    GPU detection, CPU name lookup, and AVX2 check run concurrently via a
    ``ThreadPoolExecutor``.  Results are cached inside each sub-probe.
    """
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError("psutil is required: pip install psutil") from exc

    system = platform.system()
    arch   = platform.machine()
    vm     = psutil.virtual_memory()

    total_ram_gb    = round(vm.total / (1024.0 ** 3), 1)
    installed_ram_gb = get_installed_ram() or total_ram_gb
    is_apple_silicon = system == "Darwin" and arch == "arm64"

    # Dispatch GPU detection and CPU probes in parallel
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures: dict = {
            "avx2": pool.submit(check_avx2_support),
            "cpu":  pool.submit(get_cpu_name),
        }
        if system == "Windows":
            from ._gpu_windows import get_windows_gpus
            futures["gpus"] = pool.submit(get_windows_gpus)
        elif system == "Darwin":
            from ._gpu_macos import get_macos_gpus
            futures["gpus"] = pool.submit(get_macos_gpus, total_ram_gb)
        elif system == "Linux":
            from ._gpu_linux import get_linux_gpus
            futures["gpus"] = pool.submit(get_linux_gpus)

        results = {k: f.result() for k, f in futures.items()}

    gpus = _sort_gpus(results.get("gpus") or [])
    if not gpus:
        gpus = [GpuInfo(name="Unknown GPU Device", data_source="fallback")]

    return HardwareSnapshot(
        os=system,
        os_pretty=get_os_pretty_name(),
        os_release=platform.release(),
        arch=arch,
        cpu_name=results.get("cpu", get_cpu_name()),
        cores=psutil.cpu_count(logical=False) or 0,
        threads=psutil.cpu_count(logical=True) or 0,
        has_avx2=results.get("avx2", False),
        ram=total_ram_gb,
        ram_installed=installed_ram_gb,
        is_apple_silicon=is_apple_silicon,
        free_disk=get_free_disk_space_gb(),
        gpus=gpus,
    )


def detect_system() -> SystemSnapshot:
    """
    Detect the full system configuration.

    Returns a :class:`SystemSnapshot` with ``.hardware`` and ``.software``
    populated concurrently.  Use ``.to_dict()`` or ``.to_json()`` for
    serialization.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        hw_future = pool.submit(get_hardware)
        sw_future = pool.submit(get_software)
        hw = hw_future.result()
        sw = sw_future.result()

    return SystemSnapshot(hardware=hw, software=sw)


def clear_detection_caches() -> None:
    """Clear all memoized probe results so the next call re-reads the system."""
    from ._cpu import check_avx2_support, get_cpu_name
    from ._gpu_common import _get_nvidia_smi_gpus
    from ._utils import _which

    for cached_fn in (
        _which,
        get_cpu_name,
        check_avx2_support,
        _get_nvidia_smi_gpus,
        get_installed_ram,
        get_os_pretty_name,
    ):
        cached_fn.cache_clear()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect hardware and software configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--hardware", action="store_true", help="Show only hardware info")
    group.add_argument("--software", action="store_true", help="Show only software info")
    parser.add_argument("--pretty",  action="store_true", help="Pretty-print JSON (default)")
    parser.add_argument("--compact", action="store_true", help="Compact single-line JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_cli_parser()
    args   = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    indent = None if args.compact else 2

    if args.hardware:
        data = asdict(get_hardware())
    elif args.software:
        data = asdict(get_software())
    else:
        data = detect_system().to_dict()

    print(json.dumps(data, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
