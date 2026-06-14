"""
_gpu_linux.py
-------------
Linux GPU detection via lspci (primary) and sysfs DRM (fallback).

Flow:
    get_linux_gpus()
        ├── _get_linux_pci_gpus()         primary: parse lspci output
        ├── _get_linux_sysfs_gpus()       fallback: read /sys/class/drm
        ├── _get_linux_amd_vram_by_slot() read AMD VRAM from sysfs mem_info
        └── _merge_nvidia_into()          enrich NVIDIA entries from nvidia-smi
"""

from __future__ import annotations

import logging
import os
import re

from . import config
from ._models import GpuInfo
from ._gpu_common import (
    _get_nvidia_smi_gpus,
    _infer_gpu_vendor,
    _is_unified,
    _merge_nvidia_into,
)
from ._utils import _bytes_to_gb, _read_text_file, _run_command

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# lspci parser
# ---------------------------------------------------------------------------


def _get_linux_pci_gpus() -> list[GpuInfo]:
    """Parse `lspci` output to find display / 3D controllers."""
    output = _run_command(config.DETECTOR_COMMANDS["linux_lspci"])
    if not output:
        return []

    pattern = re.compile(config.DETECTOR_REGEX["linux_display_controller"], re.IGNORECASE)
    gpus: list[GpuInfo] = []

    for line in output.splitlines():
        if not pattern.search(line):
            continue

        parts      = line.split(maxsplit=1)
        pci_bus_id = parts[0] if parts else None
        name       = line.split(": ", 1)[1].strip() if ": " in line else line.strip()
        vendor     = _infer_gpu_vendor(name)

        # Intel Arc GPUs contain "Arc" in the PCI name — treat as discrete
        gpus.append(GpuInfo(
            name=name,
            vendor=vendor,
            unified=_is_unified(vendor, vram_gb=0.0 if "arc" not in name.lower() else 4.0),
            data_source="lspci",
            pci_bus_id=pci_bus_id,
        ))

    return gpus


# ---------------------------------------------------------------------------
# sysfs DRM fallback
# ---------------------------------------------------------------------------


def _get_linux_sysfs_gpus() -> list[GpuInfo]:
    """Read GPU info from /sys/class/drm/card*/device when lspci is unavailable."""
    drm_root = config.DETECTOR_PATHS["linux_drm_root"]
    if not os.path.isdir(drm_root):
        return []

    gpus: list[GpuInfo] = []
    for entry in os.listdir(drm_root):
        if not entry.startswith("card") or "-" in entry:
            continue

        device_root = os.path.join(drm_root, entry, "device")
        if not os.path.isdir(device_root):
            continue

        # Parse uevent key=value pairs
        uevent = {}
        for line in _read_text_file(
            os.path.join(device_root, config.DETECTOR_PATHS["linux_uevent_file"])
        ).splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                uevent[k] = v

        vendor_hex = _read_text_file(
            os.path.join(device_root, config.DETECTOR_PATHS["linux_vendor_file"])
        ).lower()
        pci_bus_id = uevent.get("PCI_SLOT_NAME")

        if vendor_hex == config.DETECTOR_VENDOR_IDS["nvidia"]:
            vendor = "NVIDIA"
        elif vendor_hex == config.DETECTOR_VENDOR_IDS["amd"]:
            vendor = "AMD"
        elif vendor_hex == config.DETECTOR_VENDOR_IDS["intel"]:
            vendor = "Intel"
        else:
            vendor = "Other"

        model_name = (
            uevent.get("ID_MODEL_FROM_DATABASE")
            or uevent.get("ID_PCI_CLASS_FROM_DATABASE")
            or f"{vendor} GPU"
        )
        is_arc = "arc" in model_name.lower()

        gpus.append(GpuInfo(
            name=model_name,
            vendor=vendor,
            unified=_is_unified(vendor, vram_gb=4.0 if is_arc else 0.0),
            data_source="sysfs",
            pci_bus_id=pci_bus_id,
        ))

    return gpus


# ---------------------------------------------------------------------------
# AMD VRAM from sysfs
# ---------------------------------------------------------------------------


def _get_linux_amd_vram_by_slot() -> dict[str, float]:
    """Return a mapping of PCI slot → VRAM GB for AMD GPUs via mem_info_vram_total."""
    drm_root = config.DETECTOR_PATHS["linux_drm_root"]
    if not os.path.isdir(drm_root):
        return {}

    vram_by_slot: dict[str, float] = {}
    for entry in os.listdir(drm_root):
        if not entry.startswith("card") or "-" in entry:
            continue

        device_root = os.path.join(drm_root, entry, "device")
        vendor_hex  = _read_text_file(
            os.path.join(device_root, config.DETECTOR_PATHS["linux_vendor_file"])
        ).lower()
        if vendor_hex != config.DETECTOR_VENDOR_IDS["amd"]:
            continue

        pci_bus_id = ""
        for line in _read_text_file(
            os.path.join(device_root, config.DETECTOR_PATHS["linux_uevent_file"])
        ).splitlines():
            if line.startswith("PCI_SLOT_NAME="):
                pci_bus_id = line.split("=", 1)[1].strip()
                break

        raw = _read_text_file(
            os.path.join(device_root, config.DETECTOR_PATHS["linux_mem_info_vram_total"])
        )
        if not raw or not pci_bus_id:
            continue
        try:
            vram_by_slot[pci_bus_id] = _bytes_to_gb(int(raw))
        except ValueError:
            continue

    return vram_by_slot


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def get_linux_gpus() -> list[GpuInfo]:
    """
    Return a list of GPUs detected on Linux.

    Uses lspci when available; falls back to sysfs DRM enumeration.
    AMD VRAM is read from mem_info_vram_total; NVIDIA entries are enriched
    with nvidia-smi data.
    """
    nvidia_gpus = _get_nvidia_smi_gpus()

    pci_gpus = _get_linux_pci_gpus() or _get_linux_sysfs_gpus()
    if not pci_gpus:
        return list(nvidia_gpus)

    # Attach AMD VRAM sizes from sysfs
    amd_vram = _get_linux_amd_vram_by_slot()
    for gpu in pci_gpus:
        if gpu.vendor == "AMD" and gpu.pci_bus_id in amd_vram:
            gpu.vram = amd_vram[gpu.pci_bus_id]

    return _merge_nvidia_into(pci_gpus, nvidia_gpus)
