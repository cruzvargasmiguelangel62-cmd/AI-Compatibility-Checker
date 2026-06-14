# -*- coding: utf-8 -*-
"""
models.py
---------
Loads the AI model database and evaluates hardware compatibility for each model.

Public API:
    evaluate_compatibility(specs)  -> tuple[list[RatedModel], bool]
    load_models_data()             -> tuple[list[dict], bool]
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from . import config

__all__ = ["evaluate_compatibility", "load_models_data", "RatedModel"]

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Debug logging (kept for backwards-compat; prefer stdlib logging in new code)
# ---------------------------------------------------------------------------

_DEBUG = config.MODELS_DEBUG_LOGS


def _log(message: str) -> None:
    if _DEBUG:
        log.debug(message)


# ---------------------------------------------------------------------------
# Tier metadata
# ---------------------------------------------------------------------------

TIER_COLORS: dict[str, str] = dict(config.MODEL_STATUS_COLORS)
TIER_LABELS: dict[str, str] = dict(config.MODEL_STATUS_LABELS)

# Ordered from best to worst — used for fallback selection
_TIER_ORDER = ["RUNS_GREAT", "RUNS_WELL", "DECENT_SLOW", "TIGHT_FIT", "TOO_HEAVY"]


# ---------------------------------------------------------------------------
# Public data model
# ---------------------------------------------------------------------------


@dataclass
class RatedModel:
    """A model entry from the database, enriched with compatibility results."""

    # --- Fields copied from the database record ---
    id: str
    name: str
    category: str
    vram_q4: float
    ram_q4: float

    # --- Compatibility evaluation output ---
    status: str = "TOO_HEAVY"
    color: str = field(default_factory=lambda: TIER_COLORS["TOO_HEAVY"])
    status_label: str = field(default_factory=lambda: TIER_LABELS["TOO_HEAVY"])
    details: str = ""
    os_tip: str = ""
    recommended: bool = False

    # --- Passthrough: any extra fields from the DB record ---
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return a flat dict compatible with the original API shape."""
        base = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "vram_q4": self.vram_q4,
            "ram_q4": self.ram_q4,
            "status": self.status,
            "color": self.color,
            "status_label": self.status_label,
            "details": self.details,
            "os_tip": self.os_tip,
            "recommended": self.recommended,
        }
        base.update(self.extra)
        return base


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _get_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # One level up from src/models.py
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_path(filename: str) -> str:
    return os.path.join(_get_base_dir(), "data", filename)


# ---------------------------------------------------------------------------
# Model database loading
# ---------------------------------------------------------------------------


def _fetch_remote(url: str, timeout: Optional[int] = None) -> Optional[list[dict]]:
    """Fetch model list from *url*. Returns the list on success, None otherwise."""
    request_timeout = timeout or config.ONLINE_MODELS_TIMEOUT_SECONDS
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=request_timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, list) and data:
            return data
        _log(f"Remote response from {url} was empty or not a list.")
    except Exception as exc:
        _log(f"Error fetching online models from {url}: {exc}. Falling back to offline database.")
    return None


def _save_local(data: list[dict], path: str) -> None:
    """Persist *data* to *path*, silently skipping on failure."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        _log("Offline database updated successfully from online source.")
    except Exception as exc:
        _log(f"Failed to update offline database locally: {exc}")


def _load_json_file(path: str) -> Optional[list[dict]]:
    """Load a JSON list from *path*. Returns None on any error."""
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return data
    except Exception as exc:
        _log(f"Error loading {path}: {exc}")
    return None


@lru_cache(maxsize=1)
def load_models_data() -> tuple[list[dict], bool]:
    """
    Return ``(models_list, is_online)``.

    Strategy:
    1. Try ``data/models.json`` first (local cache / previously synced copy).
    2. Fall back to ``data/models_online.json`` (shipped with the package).
    3. Only if no local source exists, try to download the remote JSON.
       Cache it locally on success.
    4. Return an empty list if all sources fail.
    """
    primary_path = _data_path("models.json")
    fallback_path = _data_path("models_online.json")

    for path in (primary_path, fallback_path):
        local = _load_json_file(path)
        if local is not None:
            return local, False

    remote = _fetch_remote(config.ONLINE_MODELS_URL)
    if remote is not None:
        _save_local(remote, primary_path)
        return remote, True

    _log("All model data sources failed. Returning empty list.")
    return [], False


# ---------------------------------------------------------------------------
# OS / GPU tip generation
# ---------------------------------------------------------------------------


def _build_os_tip(
    category: str,
    system_os: str,
    gpu_vendor: str,
    is_apple_silicon: bool,
    has_discrete_gpu: bool,
) -> str:
    if category == config.MODEL_TEXT["image_category"]:
        if gpu_vendor == "NVIDIA":
            if system_os in ("Windows", "Linux"):
                return config.MODEL_TEXT["os_tip_image_nvidia"]
        elif gpu_vendor == "AMD":
            if system_os == "Windows":
                return config.MODEL_TEXT["os_tip_image_amd_windows"]
            if system_os == "Linux":
                return config.MODEL_TEXT["os_tip_image_amd_linux"]
        elif system_os == "Darwin" and is_apple_silicon:
            return config.MODEL_TEXT["os_tip_image_apple"]

    elif category == config.MODEL_TEXT["llm_category"]:
        if gpu_vendor == "AMD" and system_os == "Windows":
            return config.MODEL_TEXT["os_tip_llm_amd_windows"]
        if gpu_vendor == "NVIDIA" and system_os == "Linux":
            return config.MODEL_TEXT["os_tip_llm_nvidia_linux"]
        if system_os == "Windows" and not has_discrete_gpu:
            return config.MODEL_TEXT["os_tip_llm_windows_cpu"]
        if system_os == "Darwin" and is_apple_silicon:
            return config.MODEL_TEXT["os_tip_llm_apple"]

    return ""


# ---------------------------------------------------------------------------
# Per-model compatibility evaluation
# ---------------------------------------------------------------------------


def _evaluate_apple_silicon(
    vram_needed: float,
    total_ram: float,
) -> tuple[str, str]:
    """Return (status, details) for Apple Silicon unified-memory systems."""
    if total_ram >= vram_needed + config.MAC_RAM_BUFFER_GREAT:
        return (
            "RUNS_GREAT",
            config.MODEL_TEXT["apple_details_great"].format(vram_needed=vram_needed, total_ram=total_ram),
        )
    if total_ram >= vram_needed + config.MAC_RAM_BUFFER_WELL:
        return (
            "RUNS_WELL",
            config.MODEL_TEXT["apple_details_well"],
        )
    if total_ram >= vram_needed:
        return (
            "TIGHT_FIT",
            config.MODEL_TEXT["apple_details_tight"],
        )
    return (
        "TOO_HEAVY",
        config.MODEL_TEXT["apple_details_heavy"].format(vram_needed=vram_needed, total_ram=total_ram),
    )


def _evaluate_discrete_gpu(
    vram_needed: float,
    ram_needed_adjusted: float,
    max_vram: float,
    total_ram: float,
    gpu_vendor: str,
) -> tuple[str, str]:
    """Return (status, details) when a discrete GPU is present."""
    if max_vram >= vram_needed + config.WIN_VRAM_BUFFER_GREAT:
        return (
            "RUNS_GREAT",
            config.MODEL_TEXT["gpu_details_great"].format(vendor=gpu_vendor, vram_needed=vram_needed),
        )
    if (
        max_vram >= vram_needed * config.WIN_VRAM_MULTIPLIER_WELL
        and total_ram >= ram_needed_adjusted + config.WIN_RAM_BUFFER_GPU_WELL
    ):
        return (
            "RUNS_WELL",
            config.MODEL_TEXT["gpu_details_well"].format(max_vram=max_vram),
        )
    if total_ram >= ram_needed_adjusted + config.CPU_RAM_BUFFER_DECENT:
        return (
            "DECENT_SLOW",
            config.MODEL_TEXT["gpu_details_cpu_slow"],
        )
    if total_ram >= ram_needed_adjusted + config.CPU_RAM_BUFFER_TIGHT:
        return (
            "TIGHT_FIT",
            config.MODEL_TEXT["gpu_details_tight"],
        )
    return (
        "TOO_HEAVY",
        config.MODEL_TEXT["gpu_details_heavy"].format(adjusted_ram_needed=round(ram_needed_adjusted, 1)),
    )


def _evaluate_cpu_only(
    ram_needed_adjusted: float,
    total_ram: float,
    system_os: str,
) -> tuple[str, str]:
    """Return (status, details) for CPU-only inference."""
    if total_ram >= ram_needed_adjusted + config.CPU_RAM_BUFFER_DECENT:
        return (
            "DECENT_SLOW",
            config.MODEL_TEXT["cpu_details_decent"],
        )
    if total_ram >= ram_needed_adjusted + config.CPU_RAM_BUFFER_TIGHT:
        return (
            "TIGHT_FIT",
            config.MODEL_TEXT["cpu_details_tight"].format(system_os=system_os),
        )
    return (
        "TOO_HEAVY",
        config.MODEL_TEXT["cpu_details_heavy"].format(adjusted_ram_needed=round(ram_needed_adjusted, 1)),
    )


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


QUANT_MULTIPLIERS = {
    "Q2_K": 0.64,
    "Q4_K_M": 1.0,
    "Q8_0": 1.55,
    "FP16": 3.63,
}


def _parse_params_billion(params_str: str) -> float:
    try:
        match = re.search(r"([0-9.]+)\s*(?:Billion|B)", params_str, re.IGNORECASE)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return 8.0


def evaluate_compatibility(
    specs: dict,
    quantization: str = "Q4_K_M",
    context_size: int = 8,
) -> tuple[list[RatedModel], bool]:
    """
    Evaluate every model in the database against the given hardware *specs*.

    *specs* may be a flat dict (legacy) or nested ``{"hardware": {...}}``.

    Returns ``(rated_models, is_online)`` where *rated_models* is sorted by
    the original database order, with ``recommended`` flags set on the top picks.
    """
    hw = specs.get("hardware", specs)

    total_ram: float = hw["ram"]
    is_apple_silicon: bool = hw["is_apple_silicon"]
    system_os: str = hw["os"]  # 'Windows', 'Linux', 'Darwin'

    # Identify the best GPU
    gpus: list[dict] = hw.get("gpus") or []
    best_gpu = max(gpus, key=lambda g: g.get("vram", 0.0), default=None)
    max_vram: float = best_gpu["vram"] if best_gpu else 0.0
    gpu_name: str = best_gpu["name"] if best_gpu else config.MODEL_TEXT["cpu_only_name"]
    gpu_vendor: str = best_gpu.get("vendor", "Other") if best_gpu else "Other"
    has_discrete_gpu: bool = (
        gpu_vendor in {"NVIDIA", "AMD", "Apple"} and max_vram > 1.0
    )

    # OS RAM overhead
    os_penalty_map = {
        "Windows": config.OS_RAM_PENALTY_WINDOWS,
        "Linux":   config.OS_RAM_PENALTY_LINUX,
    }
    os_ram_penalty: float = os_penalty_map.get(system_os, 0.0)

    # Disk space check
    home_dir = os.path.expanduser("~")
    ollama_dir = os.path.join(home_dir, ".ollama", "models")
    disk_check_path = ollama_dir if os.path.exists(ollama_dir) else home_dir

    from .detector import get_free_disk_space_gb
    free_disk = get_free_disk_space_gb(disk_check_path)

    models_db, is_online = load_models_data()
    rated: list[RatedModel] = []
    quant_mult = QUANT_MULTIPLIERS.get(quantization, 1.0)

    for record in models_db:
        # Calculate quantization multiplier
        base_vram: float = record["vram_q4"]
        base_ram: float  = record["ram_q4"]
        category: str = record.get("category", "")

        # Calculate KV cache overhead
        if category == config.MODEL_TEXT["llm_category"]:
            params_b = _parse_params_billion(record.get("params", ""))
            context_delta_k = max(0, context_size - 8)
            kv_cache_overhead = (context_delta_k / 8.0) * (params_b * 0.08)
        else:
            kv_cache_overhead = 0.0

        vram_needed = base_vram * quant_mult + kv_cache_overhead
        ram_needed  = base_ram * quant_mult + kv_cache_overhead
        adjusted_ram = ram_needed + os_ram_penalty

        # -- Evaluate status --
        if is_apple_silicon:
            status, details = _evaluate_apple_silicon(vram_needed, total_ram)
        elif has_discrete_gpu:
            status, details = _evaluate_discrete_gpu(
                vram_needed, adjusted_ram, max_vram, total_ram, gpu_vendor
            )
        else:
            status, details = _evaluate_cpu_only(adjusted_ram, total_ram, system_os)

        # -- Disk space check --
        disk_needed = vram_needed
        has_disk_space = free_disk >= disk_needed
        if not has_disk_space:
            details += f" (⚠️ Falta disco: se requieren {disk_needed:.1f} GB pero solo quedan {free_disk:.1f} GB libres)"

        # -- Build OS/GPU tip --
        os_tip = _build_os_tip(
            category, system_os, gpu_vendor, is_apple_silicon, has_discrete_gpu
        )

        # -- Collect extra DB fields not in the dataclass --
        known_keys = {"id", "name", "category", "vram_q4", "ram_q4"}
        extra = {k: v for k, v in record.items() if k not in known_keys}

        rated.append(RatedModel(
            id=record["id"],
            name=record["name"],
            category=category,
            vram_q4=round(vram_needed, 1),
            ram_q4=round(ram_needed, 1),
            status=status,
            color=TIER_COLORS[status],
            status_label=TIER_LABELS[status],
            details=details,
            os_tip=os_tip,
            extra=extra,
        ))

    # -- Select recommendations --
    _mark_recommended(rated)
    return rated, is_online


def _models_by_category(
    rated: list[RatedModel], category: str
) -> list[RatedModel]:
    return [m for m in rated if m.category == category]


def _best_tier_models(
    pool: list[RatedModel], good_tiers: tuple[str, ...], fallback_tiers: tuple[str, ...]
) -> list[RatedModel]:
    """Return pool members at the best available tier, trying good tiers first."""
    for tiers in (good_tiers, fallback_tiers):
        subset = [m for m in pool if m.status in tiers]
        if subset:
            return subset
    return []


def _mark_recommended(rated: list[RatedModel]) -> None:
    """Set ``recommended=True`` on the top 2 LLMs and top 2 image models."""
    llms  = _models_by_category(rated, config.MODEL_TEXT["llm_category"])
    imgs  = _models_by_category(rated, config.MODEL_TEXT["image_category"])

    good_tiers     = ("RUNS_GREAT", "RUNS_WELL")
    fallback_tiers = ("DECENT_SLOW", "TIGHT_FIT")

    best_llms = _best_tier_models(llms, good_tiers, fallback_tiers)
    best_imgs = _best_tier_models(imgs, good_tiers, fallback_tiers)

    # Larger models first (higher quality)
    best_llms.sort(key=lambda m: m.vram_q4, reverse=True)
    best_imgs.sort(key=lambda m: m.vram_q4, reverse=True)

    recommended_ids: set[str] = set()
    for m in best_llms[:2]:
        recommended_ids.add(m.id)
    for m in best_imgs[:2]:
        recommended_ids.add(m.id)

    for m in rated:
        m.recommended = m.id in recommended_ids
