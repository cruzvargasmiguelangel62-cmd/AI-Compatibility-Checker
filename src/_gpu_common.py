"""
_gpu_common.py
--------------
Shared GPU utilities: vendor inference, Intel Arc discrete detection,
name normalization, nvidia-smi querying, sorting, and nvidia merge logic.

Used by _gpu_windows.py, _gpu_linux.py, and _gpu_macos.py.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from . import config
from ._models import GpuInfo
from ._utils import _run_command, _safe_int, _which

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vendor / name helpers
# ---------------------------------------------------------------------------


def _infer_gpu_vendor(name: str) -> str:
    """Infer GPU vendor from the adapter name string."""
    name_upper = (name or "").upper()
    if "NVIDIA" in name_upper:
        return "NVIDIA"
    if any(k in name_upper for k in ("AMD", "RADEON", "ATI")):
        return "AMD"
    if any(k in name_upper for k in ("INTEL", "ARC")):
        return "Intel"
    if "APPLE" in name_upper:
        return "Apple"
    return "Other"


def _is_intel_discrete(vendor: str, vram_gb: float) -> bool:
    """
    Return True if this Intel GPU is discrete (Arc series), False if integrated.

    Intel Arc GPUs ship with ≥1 GB dedicated VRAM.  Integrated HD/UHD/Xe
    graphics report 0 B or shared-only memory and must stay unified=True.
    """
    return vendor == "Intel" and vram_gb >= 1.0


# AMD iGPU name keywords (APU integrated graphics — share system RAM)
_AMD_IGPU_KEYWORDS = (
    "vega",      # Ryzen 2000/3000 APUs (Vega 3/8/10/11)
    "680m",      # Ryzen 6000 RDNA2 iGPU
    "780m",      # Ryzen 7040 RDNA3 iGPU
    "890m",      # Ryzen AI 300 RDNA3.5 iGPU
    "radeon graphics",  # Generic APU label
    "mobile graphics",  # Some OEM naming
    "gfx",       # "Radeon Vega Mobile Gfx"
)


def _is_amd_igpu(name: str) -> bool:
    """Return True if the AMD GPU is integrated (APU) based on its name."""
    name_lower = (name or "").lower()
    return any(kw in name_lower for kw in _AMD_IGPU_KEYWORDS)


def _is_unified(vendor: str, vram_gb: float = 0.0, name: str = "") -> bool:
    """Return whether a GPU uses unified (shared) memory with the CPU."""
    if vendor == "Apple":
        return True
    if vendor == "Intel":
        return not _is_intel_discrete(vendor, vram_gb)
    if vendor == "AMD":
        return _is_amd_igpu(name)
    return False


def _normalize_gpu_name(name: str) -> str:
    """Strip non-alphanumeric chars for fuzzy name matching."""
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


# ---------------------------------------------------------------------------
# nvidia-smi
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_nvidia_smi_gpus() -> list[GpuInfo]:
    """Query nvidia-smi for precise VRAM and driver versions (cached)."""
    if not _which("nvidia-smi"):
        return []

    output = _run_command(config.DETECTOR_COMMANDS["nvidia_smi_gpu_query"])
    gpus: list[GpuInfo] = []
    for line in output.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        name, vram_mib_str, driver = parts[0], parts[1], parts[2]
        gpus.append(GpuInfo(
            name=name,
            vram=round(_safe_int(vram_mib_str) / 1024.0, 1),
            vendor="NVIDIA",
            unified=False,
            driver_version=driver,
            data_source="nvidia-smi",
        ))
    return gpus


# ---------------------------------------------------------------------------
# Merge + sort
# ---------------------------------------------------------------------------


def _merge_nvidia_into(gpus: list[GpuInfo], nvidia_pool: list[GpuInfo]) -> list[GpuInfo]:
    """
    Enrich *gpus* with precise VRAM/driver data from nvidia-smi.

    For each GPU in *gpus* that belongs to NVIDIA, look up its match in
    *nvidia_pool* by name substring, consume it from the pool, and copy
    ``vram``, ``driver_version``, and ``data_source``.  Any unmatched
    nvidia-smi entries are appended at the end (e.g. compute-only devices).

    Returns a new list — *gpus* is not modified in-place.
    """
    pool = list(nvidia_pool)  # working copy so callers keep the original
    merged: list[GpuInfo] = []

    for gpu in gpus:
        if gpu.vendor == "NVIDIA" and pool:
            key = _normalize_gpu_name(gpu.name)
            match = next(
                (g for g in pool if key in _normalize_gpu_name(g.name)
                 or _normalize_gpu_name(g.name) in key),
                pool[0],  # fallback to first available when names differ
            )
            pool.remove(match)
            gpu.vram = match.vram
            gpu.driver_version = match.driver_version
            gpu.data_source = match.data_source
        merged.append(gpu)

    # Append any unmatched NVIDIA entries (multi-GPU / compute nodes)
    merged.extend(pool)
    return merged


def _sort_gpus(gpus: list[GpuInfo]) -> list[GpuInfo]:
    """
    Sort GPUs so discrete NVIDIA/AMD cards come first, then by VRAM descending.

    Apple/Intel unified GPUs are ranked last since they share system memory.
    """
    def _key(gpu: GpuInfo) -> tuple:
        is_discrete = 1 if gpu.vendor in {"NVIDIA", "AMD"} and not gpu.unified else 0
        return (is_discrete, gpu.vram, gpu.memory_pool_gb)

    return sorted(gpus, key=_key, reverse=True)
