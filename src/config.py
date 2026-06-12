import os
import sys

def load_env(file_path):
    env_vars = {}
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    val = parts[1].strip().strip('"').strip("'")
                    env_vars[key] = val
    return env_vars

# Determine paths
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # One level up from src/config.py
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CURRENT_DIR = get_base_dir()
ENV_PATH = os.path.join(CURRENT_DIR, ".env")

# Load variables
_env = load_env(ENV_PATH)

# UI Settings
APP_THEME = _env.get("APP_THEME", "dark")
APP_COLOR_THEME = _env.get("APP_COLOR_THEME", "blue")
APP_SCALING = _env.get("APP_SCALING", "auto")

# Helper to parse floats safely
def _get_float(key, default):
    try:
        return float(_env.get(key, default))
    except (ValueError, TypeError):
        return float(default)

# Apple Silicon Unified Memory Thresholds (in GB)
MAC_RAM_BUFFER_GREAT = _get_float("MAC_RAM_BUFFER_GREAT", 4.0)
MAC_RAM_BUFFER_WELL = _get_float("MAC_RAM_BUFFER_WELL", 2.0)

# Windows / Linux Dedicated GPU Thresholds
WIN_VRAM_BUFFER_GREAT = _get_float("WIN_VRAM_BUFFER_GREAT", 1.0)
WIN_VRAM_MULTIPLIER_WELL = _get_float("WIN_VRAM_MULTIPLIER_WELL", 0.7)
WIN_RAM_BUFFER_GPU_WELL = _get_float("WIN_RAM_BUFFER_GPU_WELL", 4.0)

# CPU-Only / Fallback Memory Thresholds
CPU_RAM_BUFFER_DECENT = _get_float("CPU_RAM_BUFFER_DECENT", 6.0)
CPU_RAM_BUFFER_TIGHT = _get_float("CPU_RAM_BUFFER_TIGHT", 2.0)

# OS-Specific RAM Adjustments (in GB)
OS_RAM_PENALTY_WINDOWS = _get_float("OS_RAM_PENALTY_WINDOWS", 1.5)
OS_RAM_PENALTY_LINUX = _get_float("OS_RAM_PENALTY_LINUX", -1.5)

# Online Mode Settings
ONLINE_MODELS_URL = _env.get("ONLINE_MODELS_URL", "https://raw.githubusercontent.com/cruzvargasmiguelangel62-cmd/AI-Compatibility-Checker/main/models_online.json")
