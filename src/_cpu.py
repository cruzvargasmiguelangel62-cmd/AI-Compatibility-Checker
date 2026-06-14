"""
_cpu.py
-------
CPU name and AVX2 support detection.

Key improvement: `_exec_shellcode()` abstracts the VirtualAlloc / mmap allocation
pattern that was previously duplicated across `_cpuid` and `_xgetbv`.
"""

from __future__ import annotations

import ctypes
import logging
import platform
from functools import lru_cache
from typing import Callable, Optional

from . import config
from ._utils import _read_text_file, _run_command

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level shellcode execution (de-duplicated)
# ---------------------------------------------------------------------------


def _exec_shellcode_windows(shellcode: bytes, proto: type) -> Optional[object]:
    """Allocate executable memory on Windows, execute shellcode, free memory."""
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
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
        return proto(mem)
    finally:
        kernel32.VirtualFree(mem, 0, 0x8000)


def _exec_shellcode_posix(shellcode: bytes, proto: type) -> Optional[object]:
    """Allocate executable memory via mmap on POSIX, execute shellcode, unmap."""
    import mmap as mmap_module  # local import — not available on Windows

    prot = mmap_module.PROT_READ | mmap_module.PROT_WRITE | mmap_module.PROT_EXEC  # type: ignore[attr-defined]
    mem = mmap_module.mmap(-1, len(shellcode), prot=prot)  # type: ignore[attr-defined]
    try:
        mem.write(shellcode)
        address = ctypes.addressof(ctypes.c_char.from_buffer(mem))
        return proto(address)
    finally:
        mem.close()


def _exec_shellcode(shellcode: bytes, proto: type) -> Optional[object]:
    """
    Platform-aware shellcode execution helper.

    Allocates a writable+executable memory page, copies *shellcode* into it,
    wraps it with ctypes *proto*, and returns the callable.  Frees memory in
    all cases.  Returns ``None`` on any failure.
    """
    system = platform.system()
    try:
        if system == "Windows":
            return _exec_shellcode_windows(shellcode, proto)
        return _exec_shellcode_posix(shellcode, proto)
    except Exception as exc:  # noqa: BLE001
        log.debug("shellcode exec failed (%s): %s", system, exc)
        return None


# ---------------------------------------------------------------------------
# CPUID / XGETBV
# ---------------------------------------------------------------------------


def _cpuid(leaf: int, subleaf: int = 0) -> Optional[tuple[int, ...]]:
    """Execute the CPUID instruction and return (eax, ebx, ecx, edx)."""
    arch = platform.machine().lower()
    if arch not in config.DETECTOR_ARCHITECTURES["x86_64"]:
        return None

    output = (ctypes.c_uint32 * 4)()

    # Shellcode differs by ABI (Windows vs POSIX calling convention)
    if platform.system() == "Windows":
        shellcode = bytes([
            0x53, 0x8B, 0xC1, 0x8B, 0xCA, 0x0F, 0xA2,
            0x41, 0x89, 0x00, 0x41, 0x89, 0x58, 0x04,
            0x41, 0x89, 0x48, 0x08, 0x41, 0x89, 0x50, 0x0C,
            0x5B, 0xC3,
        ])
    else:
        shellcode = bytes([
            0x53, 0x89, 0xF8, 0x89, 0xF1, 0x0F, 0xA2,
            0x89, 0x02, 0x89, 0x5A, 0x04, 0x89, 0x4A, 0x08,
            0x89, 0x52, 0x0C, 0x5B, 0xC3,
        ])

    proto = ctypes.CFUNCTYPE(None, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))
    func = _exec_shellcode(shellcode, proto)
    if func is None:
        return None

    try:
        func(leaf, subleaf, output)
    except Exception as exc:  # noqa: BLE001
        log.debug("CPUID call failed: %s", exc)
        return None

    return tuple(int(r) for r in output)


def _xgetbv() -> Optional[int]:
    """Execute XGETBV(0) to read XCR0 and return its value."""
    arch = platform.machine().lower()
    if arch not in config.DETECTOR_ARCHITECTURES["x86_64"]:
        return None

    # Same shellcode for both ABIs — no arguments, returns rax
    shellcode = bytes([
        0x31, 0xC9, 0x0F, 0x01, 0xD0,
        0x48, 0xC1, 0xE2, 0x20, 0x48, 0x09, 0xD0, 0xC3,
    ])
    proto = ctypes.CFUNCTYPE(ctypes.c_uint64)
    func = _exec_shellcode(shellcode, proto)
    if func is None:
        return None

    try:
        return int(func())
    except Exception as exc:  # noqa: BLE001
        log.debug("XGETBV call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public CPU probes
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_cpu_name() -> str:
    """Return a human-readable CPU name for the current machine."""
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
        for cmd in (config.DETECTOR_COMMANDS["macos_cpu_brand"], config.DETECTOR_COMMANDS["macos_hw_model"]):
            result = _run_command(cmd)
            if result:
                return result

    elif system == "Linux":
        for line in _read_text_file(config.DETECTOR_PATHS["linux_cpuinfo"]).splitlines():
            if "model name" in line:
                return line.split(":", 1)[1].strip()
        for line in _run_command(["lscpu"]).splitlines():
            if line.lower().startswith("model name:"):
                return line.split(":", 1)[1].strip()

    return platform.processor() or "Unknown CPU"


@lru_cache(maxsize=1)
def _check_avx2_windows_registry() -> Optional[bool]:
    """
    Fallback AVX2 detection on Windows via the Registry FeatureSet bitfield.

    HKLM\\HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0 → FeatureSet
      Bit 28 (0x10000000) = AVX supported by OS (OSXSAVE + AVX)
    We also cross-check with CPUID Family/Model to confirm AVX2 CPU support,
    since FeatureSet bit 28 covers AVX but not AVX2 specifically.
    """
    # AMD Zen+ and later (Family 23, Model >= 8) all have AVX2.
    # Intel Haswell+ (Family 6, Model >= 60) all have AVX2.
    # This table covers the common cases where shellcode fails.
    _AVX2_BY_FAMILY_MODEL: dict[int, int] = {
        6:  60,   # Intel: Haswell+ (Core i3/5/7 4th gen+)
        23: 1,    # AMD: Zen/Zen+ (Ryzen 1000/2000/3000)
        25: 0,    # AMD: Zen 3 (Ryzen 5000)
        26: 0,    # AMD: Zen 5 (Ryzen 9000)
    }
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        feature_set, _ = winreg.QueryValueEx(key, "FeatureSet")
        identifier, _  = winreg.QueryValueEx(key, "Identifier")
        winreg.CloseKey(key)

        # Bit 28 = AVX exposed by OS
        os_has_avx = bool(feature_set & (1 << 28))
        if not os_has_avx:
            return False

        # Parse "AMD/Intel64 Family 23 Model 24 Stepping 1"
        import re
        m = re.search(r"Family\s+(\d+)\s+Model\s+(\d+)", str(identifier))
        if m:
            family, model = int(m.group(1)), int(m.group(2))
            min_model = _AVX2_BY_FAMILY_MODEL.get(family)
            if min_model is not None:
                return model >= min_model

        # Unknown CPU family — trust FeatureSet AVX bit as best guess
        return os_has_avx

    except Exception as exc:
        log.debug("AVX2 registry fallback failed: %s", exc)
        return None


@lru_cache(maxsize=1)
def check_avx2_support() -> bool:
    """Return True if the CPU and OS both expose AVX2 (YMM registers enabled)."""
    system = platform.system()
    arch = platform.machine().lower()

    if arch in config.DETECTOR_ARCHITECTURES["arm64"]:
        return False  # ARM does not have AVX2

    if system == "Linux":
        flags_line = next(
            (l for l in _read_text_file(config.DETECTOR_PATHS["linux_cpuinfo"]).splitlines()
             if l.startswith("flags")),
            "",
        )
        if flags_line:
            return "avx2" in flags_line.split()

    if system == "Darwin":
        out = _run_command(config.DETECTOR_COMMANDS["macos_avx2_features"])
        if out:
            return "AVX2" in out.upper()

    # Primary: execute CPUID + XGETBV shellcode
    regs1 = _cpuid(1, 0)
    regs7 = _cpuid(7, 0)
    if regs1 and regs7:
        ecx1, ebx7 = regs1[2], regs7[1]
        has_avx      = bool(ecx1 & (1 << 28))
        has_osxsave  = bool(ecx1 & (1 << 27))
        has_avx2_cpu = bool(ebx7 & (1 << 5))
        if has_avx and has_osxsave and has_avx2_cpu:
            xcr0 = _xgetbv()
            return xcr0 is not None and (xcr0 & 0x6) == 0x6

    # Fallback for Windows: Registry FeatureSet + CPU Family table
    if system == "Windows":
        result = _check_avx2_windows_registry()
        if result is not None:
            return result

    return False
