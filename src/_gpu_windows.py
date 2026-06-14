"""
_gpu_windows.py
---------------
Windows GPU detection via DXGI (primary) and the Registry Display Class (fallback).

Flow:
    get_windows_gpus()
        ├── _get_dxgi_gpus()         primary: DXGI COM enumeration
        └── _get_registry_gpus()     fallback: HKLM Display Class keys
    then enriched with nvidia-smi data via _merge_nvidia_into()
"""

from __future__ import annotations

import ctypes
import logging
import struct

from ._models import GpuInfo
from ._gpu_common import (
    _get_nvidia_smi_gpus,
    _infer_gpu_vendor,
    _is_unified,
    _merge_nvidia_into,
    _normalize_gpu_name,
)
from . import config

log = logging.getLogger(__name__)

# Windows vendor IDs (PCI SIG)
_VENDOR_NVIDIA = 0x10DE
_VENDOR_AMD_1  = 0x1002
_VENDOR_AMD_2  = 0x1022
_VENDOR_INTEL  = 0x8086
_VENDOR_MSBASIC = 0x1414  # Microsoft Basic Display Adapter — always skip


# ---------------------------------------------------------------------------
# DXGI adapter enumeration
# ---------------------------------------------------------------------------


def _get_dxgi_gpus() -> list[GpuInfo]:
    """Enumerate GPU adapters through the DXGI COM interface."""
    from ctypes import wintypes

    gpus: list[GpuInfo] = []
    try:
        class DXGI_ADAPTER_DESC(ctypes.Structure):
            _fields_ = [
                ("Description",           wintypes.WCHAR * 128),
                ("VendorId",              ctypes.c_uint),
                ("DeviceId",              ctypes.c_uint),
                ("SubSysId",              ctypes.c_uint),
                ("Revision",              ctypes.c_uint),
                ("DedicatedVideoMemory",  ctypes.c_size_t),
                ("DedicatedSystemMemory", ctypes.c_size_t),
                ("SharedSystemMemory",    ctypes.c_size_t),
                ("AdapterLuid",           ctypes.c_int64),
            ]

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        IID_IDXGIFactory = GUID(
            0x7B7166EC, 0x21C7, 0x44AE,
            (ctypes.c_ubyte * 8)(0x90, 0x1A, 0x31, 0xA0, 0xA4, 0x0A, 0x87, 0xD4),
        )

        dxgi = ctypes.windll.dxgi  # type: ignore[attr-defined]
        factory = ctypes.c_void_p()
        if dxgi.CreateDXGIFactory(ctypes.byref(IID_IDXGIFactory), ctypes.byref(factory)) < 0:
            return []

        vtbl      = ctypes.cast(factory, ctypes.POINTER(ctypes.c_void_p))
        vtbl_addr = ctypes.cast(vtbl[0],  ctypes.POINTER(ctypes.c_void_p))

        EnumAdapters = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)
        )(vtbl_addr[7])
        GetDesc = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(DXGI_ADAPTER_DESC)
        )
        Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)

        idx = 0
        while True:
            adapter = ctypes.c_void_p()
            if EnumAdapters(factory, idx, ctypes.byref(adapter)) < 0:
                break

            a_vtbl      = ctypes.cast(adapter,    ctypes.POINTER(ctypes.c_void_p))
            a_vtbl_addr = ctypes.cast(a_vtbl[0],  ctypes.POINTER(ctypes.c_void_p))
            get_desc    = GetDesc(a_vtbl_addr[7])
            release_a   = Release(a_vtbl_addr[2])

            desc = DXGI_ADAPTER_DESC()
            if get_desc(adapter, ctypes.byref(desc)) >= 0:
                vendor_id = desc.VendorId
                name      = desc.Description.strip()
                vram_gb   = round(desc.DedicatedVideoMemory / (1024.0 ** 3), 1)

                if vendor_id == _VENDOR_NVIDIA:
                    vendor = "NVIDIA"
                elif vendor_id in (_VENDOR_AMD_1, _VENDOR_AMD_2):
                    vendor = "AMD"
                elif vendor_id == _VENDOR_INTEL:
                    vendor = "Intel"
                else:
                    vendor = "Other"

                if vendor_id != _VENDOR_MSBASIC and name:
                    gpus.append(GpuInfo(
                        name=name,
                        vram=vram_gb,
                        vendor=vendor,
                        unified=_is_unified(vendor, vram_gb, name),
                        data_source="DXGI",
                    ))

            release_a(adapter)
            idx += 1

        Release(vtbl_addr[2])(factory)

    except Exception as exc:  # noqa: BLE001
        log.debug("DXGI enumeration failed: %s", exc)

    return gpus


# ---------------------------------------------------------------------------
# Registry Display Class fallback
# ---------------------------------------------------------------------------


def _get_registry_gpus() -> list[GpuInfo]:
    """Read GPU info from the Windows Registry Display Class subkeys."""
    gpus: list[GpuInfo] = []
    try:
        import winreg

        class_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, class_path)
        num_subkeys = winreg.QueryInfoKey(root)[0]

        for i in range(num_subkeys):
            subkey_name = winreg.EnumKey(root, i)
            if not subkey_name.isdigit():
                continue
            try:
                sub = winreg.OpenKey(root, subkey_name)
                driver_desc, _ = winreg.QueryValueEx(sub, "DriverDesc")
                if not driver_desc:
                    winreg.CloseKey(sub)
                    continue

                # Read VRAM
                vram_bytes = 0
                try:
                    raw, _ = winreg.QueryValueEx(sub, "HardwareInformation.MemorySize")
                    if isinstance(raw, bytes):
                        fmt = "<I" if len(raw) == 4 else "<Q"
                        vram_bytes = struct.unpack(fmt, raw)[0]
                    else:
                        vram_bytes = int(raw)
                except Exception:
                    pass

                # Read driver version
                driver_ver = ""
                try:
                    driver_ver, _ = winreg.QueryValueEx(sub, "DriverVersion")
                except Exception:
                    pass

                winreg.CloseKey(sub)

                vendor  = _infer_gpu_vendor(driver_desc)
                vram_gb = round(vram_bytes / (1024.0 ** 3), 1)
                gpus.append(GpuInfo(
                    name=driver_desc,
                    vram=vram_gb,
                    vendor=vendor,
                    unified=_is_unified(vendor, vram_gb, driver_desc),
                    driver_version=driver_ver or None,
                    data_source="Registry Display Class",
                ))

            except Exception:
                pass  # skip malformed or access-denied subkeys

        winreg.CloseKey(root)

    except Exception as exc:
        log.debug("Registry GPU query failed: %s", exc)

    return gpus


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def get_windows_gpus() -> list[GpuInfo]:
    """
    Return a list of GPUs detected on Windows.

    Tries DXGI first; falls back to Registry if DXGI yields nothing.
    Enriches NVIDIA entries with precise VRAM and driver from nvidia-smi.
    """
    gpus = _get_dxgi_gpus() or _get_registry_gpus()
    nvidia_smi = _get_nvidia_smi_gpus()
    return _merge_nvidia_into(gpus, nvidia_smi)
