"""
_software.py
------------
Software / runtime detection: Python environment, CUDA, ROCm, and compilers.

All four probes run in parallel via ThreadPoolExecutor inside `get_software()`.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from . import config
from ._models import CompilerInfo, CudaInfo, PythonInfo, RocmInfo, SoftwareSnapshot
from ._utils import _parse_first_version, _run_command, _which

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------


def _detect_python_runtime() -> PythonInfo:
    """Detect Python version, architecture, environment type, and executable."""
    if os.environ.get("CONDA_DEFAULT_ENV"):
        env_type = "conda"
    elif sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        env_type = "virtualenv"
    else:
        env_type = "system"

    return PythonInfo(
        version=platform.python_version(),
        arch=platform.architecture()[0],
        implementation=platform.python_implementation(),
        env_type=env_type,
        executable=sys.executable,
    )


def _detect_cuda_runtime() -> CudaInfo:
    """Detect NVIDIA CUDA availability, driver version, and NVCC toolkit."""
    info = CudaInfo()

    if _which("nvidia-smi"):
        drivers = [
            line.strip()
            for line in _run_command(config.DETECTOR_COMMANDS["nvidia_smi_driver_query"]).splitlines()
            if line.strip()
        ]
        summary    = _run_command(config.DETECTOR_COMMANDS["nvidia_smi_summary"])
        cuda_match = re.search(config.DETECTOR_REGEX["cuda_version"], summary)

        info.available             = bool(drivers)
        info.gpu_count             = len(drivers)
        info.driver_version        = drivers[0] if drivers else None
        info.cuda_version_supported = cuda_match.group(1) if cuda_match else None

    if _which("nvcc"):
        nvcc_out = _run_command(config.DETECTOR_COMMANDS["nvcc_version"])
        match    = re.search(config.DETECTOR_REGEX["nvcc_release"], nvcc_out)
        info.nvcc_toolkit_version = match.group(1) if match else _parse_first_version(nvcc_out)
        info.available = True  # nvcc presence implies CUDA toolkit installed

    return info


def _detect_rocm_runtime() -> RocmInfo:
    """Detect AMD ROCm/HIP availability, version, and device count."""
    info = RocmInfo()
    version_candidates: list[str] = []

    if _which("rocminfo"):
        out = _run_command(config.DETECTOR_COMMANDS["rocminfo"])
        if out:
            info.available  = True
            info.device_count = out.lower().count("marketing name")
            if v := _parse_first_version(out):
                version_candidates.append(v)

    if _which("hipcc"):
        out = _run_command(config.DETECTOR_COMMANDS["hipcc_version"])
        if v := _parse_first_version(out):
            info.hip_version = v
            version_candidates.append(v)
            info.available = True

    if _which("rocm-smi"):
        out = _run_command(config.DETECTOR_COMMANDS["rocm_smi_driver"])
        if v := _parse_first_version(out):
            version_candidates.append(v)
            info.available = True

    info.version = next((v for v in version_candidates if v), None)
    return info


def _detect_compilers() -> CompilerInfo:
    """Detect available C/C++ compilers and CMake."""
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
# Public entry point
# ---------------------------------------------------------------------------


def get_software() -> SoftwareSnapshot:
    """
    Collect software/runtime information in parallel.

    Runs Python, CUDA, ROCm, and compiler probes concurrently via a
    4-worker ``ThreadPoolExecutor``.
    """
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            "python":    pool.submit(_detect_python_runtime),
            "cuda":      pool.submit(_detect_cuda_runtime),
            "rocm":      pool.submit(_detect_rocm_runtime),
            "compilers": pool.submit(_detect_compilers),
        }
        results = {k: f.result() for k, f in futures.items()}

    return SoftwareSnapshot(**results)
