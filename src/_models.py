"""
_models.py
----------
Public data models for hardware/software detection results.

All dataclasses are exported via ``src.detector`` — do not import this module directly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Optional

__all__ = [
    "GpuInfo",
    "HardwareSnapshot",
    "PythonInfo",
    "CudaInfo",
    "RocmInfo",
    "CompilerInfo",
    "SoftwareSnapshot",
    "SystemSnapshot",
]


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
    free_disk: float = 0.0
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
