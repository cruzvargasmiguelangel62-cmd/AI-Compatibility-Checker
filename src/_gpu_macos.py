"""
_gpu_macos.py
-------------
macOS GPU detection via `system_profiler SPDisplaysDataType -json`.
"""

from __future__ import annotations

import json
import logging
import platform
import re

from . import config
from ._models import GpuInfo
from ._gpu_common import _infer_gpu_vendor
from ._utils import _run_command

log = logging.getLogger(__name__)


def _parse_macos_vram_gb(entry: dict) -> float:
    """Extract VRAM from a system_profiler display entry (GB or MB)."""
    for key in ("spdisplays_vram", "spdisplays_vram_shared", "spdisplays_vram_dynamic"):
        value = entry.get(key)
        if not value:
            continue
        match = re.search(config.DETECTOR_REGEX["vram_amount"], str(value), re.IGNORECASE)
        if not match:
            continue
        amount = float(match.group(1))
        unit   = match.group(2).upper()
        return round(amount if unit == "GB" else amount / 1024.0, 1)
    return 0.0


def get_macos_gpus(total_ram_gb: float) -> list[GpuInfo]:
    """
    Return a list of GPUs detected on macOS.

    For Apple Silicon Macs the GPU uses unified memory, so *total_ram_gb*
    is stored as the effective memory pool.
    """
    raw = _run_command(config.DETECTOR_COMMANDS["macos_display_profiler"])
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("Could not parse SPDisplaysDataType JSON: %s", exc)
        return []

    is_arm = platform.machine() == "arm64"
    gpus: list[GpuInfo] = []

    for entry in data.get("SPDisplaysDataType", []):
        name = (
            entry.get("sppci_model")
            or entry.get("_name")
            or entry.get("spdisplays_device-id")
            or "Apple GPU"
        )
        vendor = _infer_gpu_vendor(name)
        if vendor == "Other" and is_arm:
            vendor = "Apple"

        unified = vendor == "Apple" or "shared" in json.dumps(entry).lower()
        gpus.append(GpuInfo(
            name=name,
            vram=_parse_macos_vram_gb(entry),
            vendor=vendor,
            unified=unified,
            memory_pool_gb=total_ram_gb if unified else 0.0,
            data_source="system_profiler",
        ))

    return gpus
