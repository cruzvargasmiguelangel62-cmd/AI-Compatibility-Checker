"""
system_detect.py
----------------
Detects hardware and software configuration of the current machine.

Usage as library:
    from system_detect import detect_system, get_hardware, get_software

Usage as CLI:
    python system_detect.py
    python system_detect.py --hardware
    python system_detect.py --software
    python system_detect.py --pretty
"""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import Optional

from . import config

__all__ = ["detect_system", "get_hardware", "get_software", "clear_detection_caches", "SystemSnapshot"]

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMMAND_TIMEOUT_SECONDS = config.COMMAND_TIMEOUT_SECONDS

# ---------------------------------------------------------------------------
# Public data models
# ---------------------------------------------------------------------------


@dataclass
class GpuInfo:
    name: str
    vram: float = 0.0
    vendor: str = "Other"
    unified: bool = False
    memory_pool_gb: float = 0.0
    driver_version: Optional[str] = None
    data_source: str = "unknown"
    pci_bus_id: Optional[str] = None


@dataclass
class HardwareSnapshot:
    os: str = ""
    os_pretty: str = ""
    os_release: str = ""
    arch: str = ""
    cpu_name: str = ""
    cores: int = 0
    threads: int = 0
    has_avx2: bool = False
    ram: float = 0.0
    ram_installed: float = 0.0
    is_apple_silicon: bool = False
    gpus: list[GpuInfo] = field(default_factory=list)


@dataclass
class PythonInfo:
    version: str = ""
    arch: str = ""
    implementation: str = ""
    env_type: str = ""
    executable: str = ""


@dataclass
class CudaInfo:
    available: bool = False
    driver_version: Optional[str] = None
    cuda_version_supported: Optional[str] = None
    nvcc_toolkit_version: Optional[str] = None
    gpu_count: int = 0


@dataclass
class RocmInfo:
    available: bool = False
    version: Optional[str] = None
    hip_version: Optional[str] = None
    device_count: int = 0


@dataclass
class CompilerInfo:
    gcc: bool = False
    gpp: bool = False
    clang: bool = False
    clangpp: bool = False
    cmake: bool = False
    msvc: bool = False


@dataclass
class SoftwareSnapshot:
    python: PythonInfo = field(default_factory=PythonInfo)
    cuda: CudaInfo = field(default_factory=CudaInfo)
    rocm: RocmInfo = field(default_factory=RocmInfo)
    compilers: CompilerInfo = field(default_factory=CompilerInfo)


@dataclass
class SystemSnapshot:
    hardware: HardwareSnapshot = field(default_factory=HardwareSnapshot)
    software: SoftwareSnapshot = field(default_factory=SoftwareSnapshot)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _bytes_to_gb(value) -> float:
    try:
        return round(float(value) / (1024.0 ** 3), 1)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _run_command(command: list[str]) -> str:
    """Run a subprocess command, returning stdout or empty string on failure."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
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
    return _run_command([*config.DETECTOR_COMMANDS["powershell"], script])


@lru_cache(maxsize=None)
def _which(command: str) -> bool:
    return shutil.which(command) is not None


def _parse_first_version(text: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(config.DETECTOR_REGEX["version"], text)
    return match.group(1) if match else None


def _infer_gpu_vendor(name: str) -> str:
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


def _normalize_gpu_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def _read_text_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read().strip()
    except OSError as exc:
        log.debug("Could not read %s: %s", path, exc)
        return ""


# ---------------------------------------------------------------------------
# CPUID / AVX2 detection
# ---------------------------------------------------------------------------


def _cpuid(leaf: int, subleaf: int = 0) -> Optional[tuple[int, ...]]:
    arch = platform.machine().lower()
    if arch not in config.DETECTOR_ARCHITECTURES["x86_64"]:
        return None

    output = (ctypes.c_uint32 * 4)()
    system = platform.system()

    try:
        if system == "Windows":
            shellcode = bytes([
                0x53, 0x8B, 0xC1, 0x8B, 0xCA, 0x0F, 0xA2,
                0x41, 0x89, 0x00, 0x41, 0x89, 0x58, 0x04,
                0x41, 0x89, 0x48, 0x08, 0x41, 0x89, 0x50, 0x0C,
                0x5B, 0xC3,
            ])
            kernel32 = ctypes.windll.kernel32
            kernel32.VirtualAlloc.restype = ctypes.c_void_p
            kernel32.VirtualAlloc.argtypes = [
                ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong,
            ]
            kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong]
            mem = kernel32.VirtualAlloc(None, len(shellcode), 0x3000, 0x40)
            if not mem:
                return None
            try:
                ctypes.memmove(mem, shellcode, len(shellcode))
                func = ctypes.CFUNCTYPE(
                    None, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)
                )(mem)
                func(leaf, subleaf, output)
            finally:
                kernel32.VirtualFree(mem, 0, 0x8000)
        else:
            import mmap as mmap_module
            shellcode = bytes([
                0x53, 0x89, 0xF8, 0x89, 0xF1, 0x0F, 0xA2,
                0x89, 0x02, 0x89, 0x5A, 0x04, 0x89, 0x4A, 0x08,
                0x89, 0x52, 0x0C, 0x5B, 0xC3,
            ])
            prot = mmap_module.PROT_READ | mmap_module.PROT_WRITE | mmap_module.PROT_EXEC  # type: ignore
            mem = mmap_module.mmap(-1, len(shellcode), prot=prot)  # type: ignore
            try:
                mem.write(shellcode)
                address = ctypes.addressof(ctypes.c_char.from_buffer(mem))
                func = ctypes.CFUNCTYPE(
                    None, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)
                )(address)
                func(leaf, subleaf, output)
            finally:
                mem.close()
    except Exception as exc:  # noqa: BLE001
        log.debug("CPUID failed: %s", exc)
        return None

    return tuple(int(r) for r in output)


def _xgetbv() -> Optional[int]:
    arch = platform.machine().lower()
    if arch not in config.DETECTOR_ARCHITECTURES["x86_64"]:
        return None

    shellcode = bytes([
        0x31, 0xC9, 0x0F, 0x01, 0xD0,
        0x48, 0xC1, 0xE2, 0x20, 0x48, 0x09, 0xD0, 0xC3,
    ])
    system = platform.system()

    try:
        if system == "Windows":
            kernel32 = ctypes.windll.kernel32
            kernel32.VirtualAlloc.restype = ctypes.c_void_p
            kernel32.VirtualAlloc.argtypes = [
                ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong,
            ]
            kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong]
            mem = kernel32.VirtualAlloc(None, len(shellcode), 0x3000, 0x40)
            if not mem:
                return None
            try:
                ctypes.memmove(mem, shellcode, len(shellcode))
                func = ctypes.CFUNCTYPE(ctypes.c_uint64)(mem)
                return int(func())
            finally:
                kernel32.VirtualFree(mem, 0, 0x8000)
        else:
            import mmap as mmap_module
            prot = mmap_module.PROT_READ | mmap_module.PROT_WRITE | mmap_module.PROT_EXEC  # type: ignore
            mem = mmap_module.mmap(-1, len(shellcode), prot=prot)  # type: ignore
            try:
                mem.write(shellcode)
                address = ctypes.addressof(ctypes.c_char.from_buffer(mem))
                func = ctypes.CFUNCTYPE(ctypes.c_uint64)(address)
                return int(func())
            finally:
                mem.close()
    except Exception as exc:  # noqa: BLE001
        log.debug("XGETBV failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# CPU detection
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_cpu_name() -> str:
    """Return a human-readable CPU name."""
    system = platform.system()
    if system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if name:
                return name.strip()
        except Exception:
            pass
    elif system == "Darwin":
        for sysctl_command in (
            config.DETECTOR_COMMANDS["macos_cpu_brand"],
            config.DETECTOR_COMMANDS["macos_hw_model"],
        ):
            result = _run_command(sysctl_command)
            if result:
                return result
    elif system == "Linux":
        cpuinfo = _read_text_file(config.DETECTOR_PATHS["linux_cpuinfo"])
        for line in cpuinfo.splitlines():
            if "model name" in line:
                return line.split(":", 1)[1].strip()
        lscpu = _run_command(["lscpu"])
        for line in lscpu.splitlines():
            if line.lower().startswith("model name:"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "Unknown CPU"


@lru_cache(maxsize=1)
def check_avx2_support() -> bool:
    """Return True if the CPU and OS both support AVX2."""
    system = platform.system()
    arch = platform.machine().lower()

    if arch in config.DETECTOR_ARCHITECTURES["arm64"]:
        return False

    if system == "Linux":
        flags_line = next(
            (l for l in _read_text_file(config.DETECTOR_PATHS["linux_cpuinfo"]).splitlines() if l.startswith("flags")),
            "",
        )
        if flags_line:
            return "avx2" in flags_line.split()

    if system == "Darwin":
        out = _run_command(config.DETECTOR_COMMANDS["macos_avx2_features"])
        if out:
            return "AVX2" in out.upper()

    regs1 = _cpuid(1, 0)
    regs7 = _cpuid(7, 0)
    if not regs1 or not regs7:
        return False

    ecx1, ebx7 = regs1[2], regs7[1]
    has_avx = bool(ecx1 & (1 << 28))
    has_osxsave = bool(ecx1 & (1 << 27))
    has_avx2 = bool(ebx7 & (1 << 5))
    if not (has_avx and has_osxsave and has_avx2):
        return False

    xcr0 = _xgetbv()
    return xcr0 is not None and (xcr0 & 0x6) == 0x6


# ---------------------------------------------------------------------------
# GPU detection
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_nvidia_smi_gpus() -> list[GpuInfo]:
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


def _get_dxgi_gpus() -> list[GpuInfo]:
    import ctypes
    from ctypes import wintypes
    
    gpus: list[GpuInfo] = []
    try:
        class DXGI_ADAPTER_DESC(ctypes.Structure):
            _fields_ = [
                ("Description", wintypes.WCHAR * 128),
                ("VendorId", ctypes.c_uint),
                ("DeviceId", ctypes.c_uint),
                ("SubSysId", ctypes.c_uint),
                ("Revision", ctypes.c_uint),
                ("DedicatedVideoMemory", ctypes.c_size_t),
                ("DedicatedSystemMemory", ctypes.c_size_t),
                ("SharedSystemMemory", ctypes.c_size_t),
                ("AdapterLuid", ctypes.c_int64),
            ]

        dxgi = ctypes.windll.dxgi
        
        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8)
            ]
        
        IID_IDXGIFactory = GUID(
            0x7b7166ec, 0x21c7, 0x44ae,
            (ctypes.c_ubyte * 8)(0x90, 0x1a, 0x31, 0xa0, 0xa4, 0x0a, 0x87, 0xd4)
        )
        
        factory = ctypes.c_void_p()
        hr = dxgi.CreateDXGIFactory(ctypes.byref(IID_IDXGIFactory), ctypes.byref(factory))
        if hr < 0:
            return []
            
        vtable = ctypes.cast(factory, ctypes.POINTER(ctypes.c_void_p))
        vtable_addr = ctypes.cast(vtable[0], ctypes.POINTER(ctypes.c_void_p))
        
        enum_adapters_proto = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p)
        )
        enum_adapters = enum_adapters_proto(vtable_addr[7])
        
        get_desc_proto = ctypes.WINFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.POINTER(DXGI_ADAPTER_DESC)
        )
        
        release_proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
        
        adapter_idx = 0
        while True:
            adapter = ctypes.c_void_p()
            hr = enum_adapters(factory, adapter_idx, ctypes.byref(adapter))
            if hr < 0:
                break
                
            adapter_vtable = ctypes.cast(adapter, ctypes.POINTER(ctypes.c_void_p))
            adapter_vtable_addr = ctypes.cast(adapter_vtable[0], ctypes.POINTER(ctypes.c_void_p))
            get_desc = get_desc_proto(adapter_vtable_addr[7])
            
            desc = DXGI_ADAPTER_DESC()
            hr_desc = get_desc(adapter, ctypes.byref(desc))
            
            release_adapter = release_proto(adapter_vtable_addr[2])
            release_adapter(adapter)
            
            if hr_desc >= 0:
                name = desc.Description.strip()
                vram_bytes = desc.DedicatedVideoMemory
                vram_gb = round(vram_bytes / (1024.0 ** 3), 1)
                
                vendor_id = desc.VendorId
                vendor = "Other"
                if vendor_id == 0x10de:
                    vendor = "NVIDIA"
                elif vendor_id in (0x1002, 0x1022):
                    vendor = "AMD"
                elif vendor_id == 0x8086:
                    vendor = "Intel"
                
                if vendor_id != 0x1414 and name:
                    gpus.append(GpuInfo(
                        name=name,
                        vram=vram_gb,
                        vendor=vendor,
                        unified=(vendor == "Intel"),
                        data_source="DXGI",
                    ))
            
            adapter_idx += 1
            
        release_factory = release_proto(vtable_addr[2])
        release_factory(factory)
    except Exception as e:
        log.debug("DXGI enum failed: %s", e)
        
    return gpus


def _get_registry_gpus() -> list[GpuInfo]:
    gpus: list[GpuInfo] = []
    try:
        import winreg
        import struct
        class_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, class_path)
        info = winreg.QueryInfoKey(key)
        num_subkeys = info[0]
        for i in range(num_subkeys):
            subkey_name = winreg.EnumKey(key, i)
            if not subkey_name.isdigit():
                continue
            try:
                subkey = winreg.OpenKey(key, subkey_name)
                driver_desc, _ = winreg.QueryValueEx(subkey, "DriverDesc")
                if not driver_desc:
                    winreg.CloseKey(subkey)
                    continue
                    
                vram_bytes = 0
                try:
                    vram_raw, _ = winreg.QueryValueEx(subkey, "HardwareInformation.MemorySize")
                    if isinstance(vram_raw, bytes):
                        if len(vram_raw) == 4:
                            vram_bytes = struct.unpack("<I", vram_raw)[0]
                        elif len(vram_raw) == 8:
                            vram_bytes = struct.unpack("<Q", vram_raw)[0]
                    else:
                        vram_bytes = int(vram_raw)
                except Exception:
                    pass
                    
                driver_ver = ""
                try:
                    driver_ver, _ = winreg.QueryValueEx(subkey, "DriverVersion")
                except Exception:
                    pass
                    
                vendor = _infer_gpu_vendor(driver_desc)
                vram_gb = round(vram_bytes / (1024.0 ** 3), 1)
                
                gpus.append(GpuInfo(
                    name=driver_desc,
                    vram=vram_gb,
                    vendor=vendor,
                    unified=(vendor == "Intel"),
                    driver_version=driver_ver,
                    data_source="Registry Display Class",
                ))
                winreg.CloseKey(subkey)
            except Exception:
                pass
        winreg.CloseKey(key)
    except Exception as exc:
        log.debug("Registry GPU query failed: %s", exc)
    return gpus


def _get_windows_gpus() -> list[GpuInfo]:
    gpus = _get_dxgi_gpus()
    if not gpus:
        gpus = _get_registry_gpus()
        
    nvidia_gpus = _get_nvidia_smi_gpus()
    nvidia_by_name = {_normalize_gpu_name(g.name): g for g in nvidia_gpus}
    
    for gpu in gpus:
        key = _normalize_gpu_name(gpu.name)
        if key in nvidia_by_name:
            nv = nvidia_by_name[key]
            gpu.vram = nv.vram
            gpu.driver_version = nv.driver_version
            gpu.data_source = nv.data_source
        elif gpu.vendor == "NVIDIA" and nvidia_gpus:
            nv = next(
                (
                    candidate
                    for candidate in nvidia_gpus
                    if key in _normalize_gpu_name(candidate.name)
                    or _normalize_gpu_name(candidate.name) in key
                ),
                None,
            )
            if nv is not None:
                gpu.vram = nv.vram
                gpu.driver_version = nv.driver_version
                gpu.data_source = nv.data_source
                
    # Append NVIDIA GPUs not in DXGI/Registry (e.g. secondary compute-only devices)
    seen = {_normalize_gpu_name(g.name) for g in gpus}
    for g in nvidia_gpus:
        if _normalize_gpu_name(g.name) not in seen:
            gpus.append(g)
            
    return gpus


def _parse_macos_vram_gb(entry: dict) -> float:
    for key in ("spdisplays_vram", "spdisplays_vram_shared", "spdisplays_vram_dynamic"):
        value = entry.get(key)
        if not value:
            continue
        match = re.search(config.DETECTOR_REGEX["vram_amount"], str(value), re.IGNORECASE)
        if not match:
            continue
        amount = float(match.group(1))
        unit = match.group(2).upper()
        return round(amount if unit == "GB" else amount / 1024.0, 1)
    return 0.0


def _get_macos_gpus(total_ram_gb: float) -> list[GpuInfo]:
    raw = _run_command(config.DETECTOR_COMMANDS["macos_display_profiler"])
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("Could not parse SPDisplaysDataType JSON: %s", exc)
        return []

    gpus: list[GpuInfo] = []
    for entry in data.get("SPDisplaysDataType", []):
        name = (
            entry.get("sppci_model")
            or entry.get("_name")
            or entry.get("spdisplays_device-id")
            or "Apple GPU"
        )
        vendor = _infer_gpu_vendor(name)
        if vendor == "Other" and platform.machine() == "arm64":
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


def _get_linux_pci_gpus() -> list[GpuInfo]:
    output = _run_command(config.DETECTOR_COMMANDS["linux_lspci"])
    if not output:
        return []

    pattern = re.compile(
        config.DETECTOR_REGEX["linux_display_controller"], re.IGNORECASE
    )
    gpus: list[GpuInfo] = []
    for line in output.splitlines():
        if not pattern.search(line):
            continue
        raw_parts = line.split(maxsplit=1)
        pci_bus_id = raw_parts[0] if raw_parts else None
        parts = line.split(": ", 1)
        name = parts[1].strip() if len(parts) > 1 else line.strip()
        vendor = _infer_gpu_vendor(name)
        gpus.append(GpuInfo(
            name=name,
            vendor=vendor,
            unified=(vendor == "Intel"),
            data_source="lspci",
            pci_bus_id=pci_bus_id,
        ))
    return gpus


def _get_linux_sysfs_gpus() -> list[GpuInfo]:
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

        uevent_lines = _read_text_file(os.path.join(device_root, config.DETECTOR_PATHS["linux_uevent_file"])).splitlines()
        uevent = {}
        for line in uevent_lines:
            if "=" in line:
                key, value = line.split("=", 1)
                uevent[key] = value

        vendor_hex = _read_text_file(os.path.join(device_root, config.DETECTOR_PATHS["linux_vendor_file"])).lower()
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
        gpus.append(
            GpuInfo(
                name=model_name,
                vendor=vendor,
                unified=(vendor == "Intel"),
                data_source="sysfs",
                pci_bus_id=pci_bus_id,
            )
        )
    return gpus


def _get_linux_amd_vram_by_slot() -> dict[str, float]:
    drm_root = config.DETECTOR_PATHS["linux_drm_root"]
    if not os.path.isdir(drm_root):
        return {}

    vram_by_slot: dict[str, float] = {}
    for entry in os.listdir(drm_root):
        if not entry.startswith("card") or "-" in entry:
            continue
        device_root = os.path.join(drm_root, entry, "device")
        vendor_hex = _read_text_file(os.path.join(device_root, config.DETECTOR_PATHS["linux_vendor_file"])).lower()
        if vendor_hex != config.DETECTOR_VENDOR_IDS["amd"]:
            continue

        pci_bus_id = ""
        for line in _read_text_file(os.path.join(device_root, config.DETECTOR_PATHS["linux_uevent_file"])).splitlines():
            if line.startswith("PCI_SLOT_NAME="):
                pci_bus_id = line.split("=", 1)[1].strip()
                break

        mem_path = os.path.join(device_root, config.DETECTOR_PATHS["linux_mem_info_vram_total"])
        raw = _read_text_file(mem_path)
        if not raw or not pci_bus_id:
            continue
        try:
            vram_by_slot[pci_bus_id] = _bytes_to_gb(int(raw))
        except ValueError:
            continue
    return vram_by_slot


def _get_linux_gpus() -> list[GpuInfo]:
    nvidia_gpus = _get_nvidia_smi_gpus()
    pci_gpus = _get_linux_pci_gpus()
    if not pci_gpus:
        pci_gpus = _get_linux_sysfs_gpus()

    if not pci_gpus:
        return list(nvidia_gpus)

    amd_vram_by_slot = _get_linux_amd_vram_by_slot()
    nvidia_pool = list(nvidia_gpus)
    merged: list[GpuInfo] = []

    for gpu in pci_gpus:
        if gpu.vendor == "NVIDIA" and nvidia_pool:
            # Match by substring; fall back to first available
            match = next(
                (g for g in nvidia_pool if g.name.lower() in gpu.name.lower()),
                nvidia_pool[0],
            )
            nvidia_pool.remove(match)
            gpu.vram = match.vram
            gpu.driver_version = match.driver_version
            gpu.data_source = match.data_source

        if gpu.vendor == "AMD" and gpu.pci_bus_id in amd_vram_by_slot:
            gpu.vram = amd_vram_by_slot[gpu.pci_bus_id]

        merged.append(gpu)

    # Append any unmatched NVIDIA devices (e.g. multi-GPU systems)
    merged.extend(nvidia_pool)
    return merged


def _sort_gpus(gpus: list[GpuInfo]) -> list[GpuInfo]:
    def key(gpu: GpuInfo) -> tuple:
        discrete = 1 if gpu.vendor in {"NVIDIA", "AMD"} and not gpu.unified else 0
        return (discrete, gpu.vram, gpu.memory_pool_gb)

    return sorted(gpus, key=key, reverse=True)


# ---------------------------------------------------------------------------
# RAM / OS helpers
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
                vm = psutil.virtual_memory()
                return round(vm.total / (1024.0 ** 3), 1)
            except Exception:
                return None
    if system == "Darwin":
        out = _run_command(config.DETECTOR_COMMANDS["macos_memsize"])
        return _bytes_to_gb(_safe_int(out)) if out else None
    if system == "Linux":
        for line in _read_text_file(config.DETECTOR_PATHS["linux_meminfo"]).splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2:
                    return round(float(parts[1]) / (1024.0 ** 2), 1)
    return None


@lru_cache(maxsize=1)
def get_os_pretty_name() -> str:
    system = platform.system()
    try:
        if system == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                product_name, _ = winreg.QueryValueEx(key, "ProductName")
                display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
                current_build, _ = winreg.QueryValueEx(key, "CurrentBuild")
                winreg.CloseKey(key)
                if display_version:
                    return f"{product_name} (versión {display_version}, compilación {current_build})"
                return f"{product_name} (compilación {current_build})"
            except Exception:
                return f"Windows {platform.release()}"
        if system == "Darwin":
            version = _run_command(config.DETECTOR_COMMANDS["macos_product_version"])
            build = _run_command(config.DETECTOR_COMMANDS["macos_build_version"])
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


def get_free_disk_space_gb(path: str) -> float:
    """Return free disk space in GB for the partition containing path."""
    try:
        total, used, free = shutil.disk_usage(path)
        return round(free / (1024.0 ** 3), 1)
    except Exception:
        try:
            total, used, free = shutil.disk_usage(os.path.expanduser("~"))
            return round(free / (1024.0 ** 3), 1)
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Software detection
# ---------------------------------------------------------------------------


def _detect_python_runtime() -> PythonInfo:
    env_type = "system"
    if os.environ.get("CONDA_DEFAULT_ENV"):
        env_type = "conda"
    elif sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        env_type = "virtualenv"
    return PythonInfo(
        version=platform.python_version(),
        arch=platform.architecture()[0],
        implementation=platform.python_implementation(),
        env_type=env_type,
        executable=sys.executable,
    )


def _detect_cuda_runtime() -> CudaInfo:
    info = CudaInfo()
    if _which("nvidia-smi"):
        drivers = [
            line.strip()
            for line in _run_command(
                config.DETECTOR_COMMANDS["nvidia_smi_driver_query"]
            ).splitlines()
            if line.strip()
        ]
        summary = _run_command(config.DETECTOR_COMMANDS["nvidia_smi_summary"])
        cuda_match = re.search(config.DETECTOR_REGEX["cuda_version"], summary)
        info.available = bool(drivers)
        info.gpu_count = len(drivers)
        info.driver_version = drivers[0] if drivers else None
        info.cuda_version_supported = cuda_match.group(1) if cuda_match else None

    if _which("nvcc"):
        nvcc_out = _run_command(config.DETECTOR_COMMANDS["nvcc_version"])
        match = re.search(config.DETECTOR_REGEX["nvcc_release"], nvcc_out)
        info.nvcc_toolkit_version = match.group(1) if match else _parse_first_version(nvcc_out)
        info.available = True

    return info


def _detect_rocm_runtime() -> RocmInfo:
    info = RocmInfo()
    version_candidates: list[str] = []

    if _which("rocminfo"):
        out = _run_command(config.DETECTOR_COMMANDS["rocminfo"])
        if out:
            info.available = True
            info.device_count = out.lower().count("marketing name")
            v = _parse_first_version(out)
            if v:
                version_candidates.append(v)

    if _which("hipcc"):
        out = _run_command(config.DETECTOR_COMMANDS["hipcc_version"])
        v = _parse_first_version(out)
        if v:
            info.hip_version = v
            version_candidates.append(v)
            info.available = True

    if _which("rocm-smi"):
        out = _run_command(config.DETECTOR_COMMANDS["rocm_smi_driver"])
        v = _parse_first_version(out)
        if v:
            version_candidates.append(v)
            info.available = True

    info.version = next((v for v in version_candidates if v), None)
    return info


def _detect_compilers() -> CompilerInfo:
    info = CompilerInfo(
        gcc=_which("gcc"),
        gpp=_which("g++"),
        clang=_which("clang"),
        clangpp=_which("clang++"),
        cmake=_which("cmake"),
    )
    if platform.system() == "Windows":
        info.msvc = bool(_run_command(config.DETECTOR_COMMANDS["windows_compiler_lookup"]))
    return info


# ---------------------------------------------------------------------------
# Top-level builders — run hardware sub-tasks in parallel
# ---------------------------------------------------------------------------


def get_hardware() -> HardwareSnapshot:
    """Collect hardware information using cached helper probes where available."""
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError("psutil is required: pip install psutil") from exc

    system = platform.system()
    arch = platform.machine()
    vm = psutil.virtual_memory()
    total_ram_gb = round(vm.total / (1024.0 ** 3), 1)
    installed_ram_gb = get_installed_ram() or total_ram_gb
    is_apple_silicon = system == "Darwin" and arch == "arm64"

    # Dispatch GPU detection and AVX2 check in parallel
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            "avx2": pool.submit(check_avx2_support),
            "cpu": pool.submit(get_cpu_name),
        }
        if system == "Windows":
            futures["gpus"] = pool.submit(_get_windows_gpus)
        elif system == "Darwin":
            futures["gpus"] = pool.submit(_get_macos_gpus, total_ram_gb)
        elif system == "Linux":
            futures["gpus"] = pool.submit(_get_linux_gpus)

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
        gpus=gpus,
    )


def get_software() -> SoftwareSnapshot:
    """Collect software/runtime information."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            "python": pool.submit(_detect_python_runtime),
            "cuda": pool.submit(_detect_cuda_runtime),
            "rocm": pool.submit(_detect_rocm_runtime),
            "compilers": pool.submit(_detect_compilers),
        }
        results = {k: f.result() for k, f in futures.items()}

    return SoftwareSnapshot(**results)


def detect_system() -> SystemSnapshot:
    """
    Detect the full system configuration.

    Returns a :class:`SystemSnapshot` with `.hardware` and `.software` attributes.
    Use `.to_dict()` or `.to_json()` for serialization.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        hw_future = pool.submit(get_hardware)
        sw_future = pool.submit(get_software)
        hw = hw_future.result()
        sw = sw_future.result()

    return SystemSnapshot(hardware=hw, software=sw)


def clear_detection_caches() -> None:
    """Clear memoized probe helpers so a forced rescan reads the system again."""
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
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON (default)")
    parser.add_argument("--compact", action="store_true", help="Compact single-line JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)

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
