import json
import os
import sys


def load_env(file_path):
    env_vars = {}
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file_obj:
            for raw_line in file_obj:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CURRENT_DIR = get_base_dir()
ENV_PATH = os.path.join(CURRENT_DIR, ".env")
_env = load_env(ENV_PATH)


def _get_str(key, default):
    return _env.get(key, default)


def _get_float(key, default):
    try:
        return float(_env.get(key, default))
    except (ValueError, TypeError):
        return float(default)


def _get_int(key, default):
    try:
        return int(_env.get(key, default))
    except (ValueError, TypeError):
        return int(default)


def _get_bool(key, default):
    value = str(_env.get(key, str(default))).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _get_json(key, default):
    raw_value = _env.get(key)
    if not raw_value:
        return default
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return default


APP_THEME = _get_str("APP_THEME", "dark")
APP_COLOR_THEME = _get_str("APP_COLOR_THEME", "blue")
APP_SCALING = _get_str("APP_SCALING", "auto")
ONLINE_MODELS_URL = _get_str(
    "ONLINE_MODELS_URL",
    "https://raw.githubusercontent.com/cruzvargasmiguelangel62-cmd/AI-Compatibility-Checker/main/models_online.json",
)

ONLINE_MODELS_TIMEOUT_SECONDS = _get_int("ONLINE_MODELS_TIMEOUT_SECONDS", 3)
COMMAND_TIMEOUT_SECONDS = _get_int("COMMAND_TIMEOUT_SECONDS", 8)
MODELS_DEBUG_LOGS = _get_bool("AI_CHECKER_DEBUG_LOGS", False)

MAC_RAM_BUFFER_GREAT = _get_float("MAC_RAM_BUFFER_GREAT", 4.0)
MAC_RAM_BUFFER_WELL = _get_float("MAC_RAM_BUFFER_WELL", 2.0)
WIN_VRAM_BUFFER_GREAT = _get_float("WIN_VRAM_BUFFER_GREAT", 1.0)
WIN_VRAM_MULTIPLIER_WELL = _get_float("WIN_VRAM_MULTIPLIER_WELL", 0.7)
WIN_RAM_BUFFER_GPU_WELL = _get_float("WIN_RAM_BUFFER_GPU_WELL", 4.0)
CPU_RAM_BUFFER_DECENT = _get_float("CPU_RAM_BUFFER_DECENT", 6.0)
CPU_RAM_BUFFER_TIGHT = _get_float("CPU_RAM_BUFFER_TIGHT", 2.0)
OS_RAM_PENALTY_WINDOWS = _get_float("OS_RAM_PENALTY_WINDOWS", 1.5)
OS_RAM_PENALTY_LINUX = _get_float("OS_RAM_PENALTY_LINUX", -1.5)

# New settings for AI compatibility enhancements
DEFAULT_QUANTIZATION = _get_str("DEFAULT_QUANTIZATION", "Q4_K_M")
DEFAULT_CONTEXT_SIZE = _get_int("DEFAULT_CONTEXT_SIZE", 8)
OLLAMA_HOST = _get_str("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_LANGUAGE = _get_str("DEFAULT_LANGUAGE", "es")

DETECTOR_OS_KEYS = {
    "windows": "Windows",
    "linux": "Linux",
    "macos": "Darwin",
}

DETECTOR_ARCHITECTURES = {
    "x86_64": {"amd64", "x86_64"},
    "arm64": {"arm64", "aarch64"},
}

DETECTOR_VENDOR_IDS = {
    "nvidia": "0x10de",
    "amd": "0x1002",
    "intel": "0x8086",
}

DETECTOR_COMMANDS = {
    "powershell": ["powershell", "-NoProfile", "-Command"],
    "nvidia_smi_gpu_query": [
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ],
    "nvidia_smi_driver_query": [
        "nvidia-smi",
        "--query-gpu=driver_version",
        "--format=csv,noheader",
    ],
    "nvidia_smi_summary": ["nvidia-smi"],
    "nvcc_version": ["nvcc", "--version"],
    "rocminfo": ["rocminfo"],
    "hipcc_version": ["hipcc", "--version"],
    "rocm_smi_driver": ["rocm-smi", "--showdriverversion"],
    "linux_lspci": ["lspci", "-D", "-nn"],
    "macos_display_profiler": ["system_profiler", "SPDisplaysDataType", "-json"],
    "macos_cpu_brand": ["sysctl", "-n", "machdep.cpu.brand_string"],
    "macos_hw_model": ["sysctl", "-n", "hw.model"],
    "macos_avx2_features": ["sysctl", "-n", "machdep.cpu.leaf7_features"],
    "macos_memsize": ["sysctl", "-n", "hw.memsize"],
    "macos_product_version": ["sw_vers", "-productVersion"],
    "macos_build_version": ["sw_vers", "-buildVersion"],
    "windows_compiler_lookup": ["where", "cl"],
}

DETECTOR_PATHS = {
    "linux_cpuinfo": "/proc/cpuinfo",
    "linux_meminfo": "/proc/meminfo",
    "linux_os_release": "/etc/os-release",
    "linux_drm_root": "/sys/class/drm",
    "linux_mem_info_vram_total": "mem_info_vram_total",
    "linux_vendor_file": "vendor",
    "linux_uevent_file": "uevent",
}

DETECTOR_REGEX = {
    "version": r"(\d+(?:\.\d+){1,3})",
    "vram_amount": r"(\d+(?:\.\d+)?)\s*(GB|MB)",
    "cuda_version": r"CUDA Version:\s*([0-9.]+)",
    "nvcc_release": r"release\s+([0-9.]+)",
    "linux_display_controller": r"(VGA compatible controller|3D controller|Display controller)",
}

UI_BASE = {
    "window_title": _get_str("UI_WINDOW_TITLE", "AI Local Hardware Detector & Compatibility Engine"),
    "search_categories": _get_json(
        "UI_SEARCH_CATEGORIES",
        ["Todos", "Text (LLM)", "Image Generation"],
    ),
    "render_batch_size": _get_int("UI_RENDER_BATCH_SIZE", 3),
    "narrow_layout_breakpoint": _get_int("UI_NARROW_LAYOUT_BREAKPOINT", 1380),
    "sidebar_width": {
        "Windows": _get_int("UI_SIDEBAR_WIDTH_WINDOWS", 280),
        "Linux": _get_int("UI_SIDEBAR_WIDTH_LINUX", 420),
        "Darwin": _get_int("UI_SIDEBAR_WIDTH_MACOS", 400),
        "default": _get_int("UI_SIDEBAR_WIDTH_DEFAULT", 360),
    },
    "font_family": {
        "Windows": _get_str("UI_FONT_WINDOWS", "Segoe UI"),
        "Linux": _get_str("UI_FONT_LINUX", "DejaVu Sans"),
        "Darwin": _get_str("UI_FONT_MACOS", "SF Pro Text"),
        "default": _get_str("UI_FONT_DEFAULT", "Arial"),
    },
    "tk_scaling": {
        "Windows": _get_float("UI_TK_SCALING_WINDOWS", 0.98),
        "Linux": _get_float("UI_TK_SCALING_LINUX", 1.08),
        "Darwin": _get_float("UI_TK_SCALING_MACOS", 1.0),
        "default": _get_float("UI_TK_SCALING_DEFAULT", 1.0),
    },
    "widget_scaling": {
        "Windows": _get_float("UI_WIDGET_SCALING_WINDOWS", 0.94),
        "Linux": _get_float("UI_WIDGET_SCALING_LINUX", 1.12),
        "Darwin": _get_float("UI_WIDGET_SCALING_MACOS", 1.0),
        "default": _get_float("UI_WIDGET_SCALING_DEFAULT", 1.0),
    },
    "window_geometry": {
        "Windows": {
            "initial_width_max": _get_int("UI_WINDOW_INITIAL_WIDTH_MAX_WINDOWS", 920),
            "initial_width_min": _get_int("UI_WINDOW_INITIAL_WIDTH_MIN_WINDOWS", 720),
            "initial_width_ratio": _get_float("UI_WINDOW_INITIAL_WIDTH_RATIO_WINDOWS", 0.56),
            "initial_height_max": _get_int("UI_WINDOW_INITIAL_HEIGHT_MAX_WINDOWS", 680),
            "initial_height_min": _get_int("UI_WINDOW_INITIAL_HEIGHT_MIN_WINDOWS", 540),
            "initial_height_ratio": _get_float("UI_WINDOW_INITIAL_HEIGHT_RATIO_WINDOWS", 0.58),
            "min_width_floor": _get_int("UI_WINDOW_MIN_WIDTH_FLOOR_WINDOWS", 640),
            "min_width_ratio": _get_float("UI_WINDOW_MIN_WIDTH_RATIO_WINDOWS", 0.44),
            "min_height_floor": _get_int("UI_WINDOW_MIN_HEIGHT_FLOOR_WINDOWS", 500),
            "min_height_ratio": _get_float("UI_WINDOW_MIN_HEIGHT_RATIO_WINDOWS", 0.5),
        },
        "default": {
            "initial_width_max": _get_int("UI_WINDOW_INITIAL_WIDTH_MAX_DEFAULT", 1440),
            "initial_width_min": _get_int("UI_WINDOW_INITIAL_WIDTH_MIN_DEFAULT", 1040),
            "initial_width_ratio": _get_float("UI_WINDOW_INITIAL_WIDTH_RATIO_DEFAULT", 0.86),
            "initial_height_max": _get_int("UI_WINDOW_INITIAL_HEIGHT_MAX_DEFAULT", 920),
            "initial_height_min": _get_int("UI_WINDOW_INITIAL_HEIGHT_MIN_DEFAULT", 680),
            "initial_height_ratio": _get_float("UI_WINDOW_INITIAL_HEIGHT_RATIO_DEFAULT", 0.84),
            "min_width_floor": _get_int("UI_WINDOW_MIN_WIDTH_FLOOR_DEFAULT", 900),
            "min_width_ratio": _get_float("UI_WINDOW_MIN_WIDTH_RATIO_DEFAULT", 0.65),
            "min_height_floor": _get_int("UI_WINDOW_MIN_HEIGHT_FLOOR_DEFAULT", 620),
            "min_height_ratio": _get_float("UI_WINDOW_MIN_HEIGHT_RATIO_DEFAULT", 0.72),
        },
    },
    "layout": {
        "main_padding": _get_int("UI_LAYOUT_MAIN_PADDING", 14),
        "main_padding_compact": _get_int("UI_LAYOUT_MAIN_PADDING_COMPACT", 10),
        "responsive_padding": _get_int("UI_LAYOUT_RESPONSIVE_PADDING", 10),
        "section_gap": _get_int("UI_LAYOUT_SECTION_GAP", 10),
        "section_gap_tight": _get_int("UI_LAYOUT_SECTION_GAP_TIGHT", 6),
        "content_stack_breakpoint": _get_int("UI_LAYOUT_CONTENT_STACK_BREAKPOINT", 1280),
        "model_support_stack_breakpoint": _get_int("UI_LAYOUT_MODEL_SUPPORT_STACK_BREAKPOINT", 1120),
        "header_top_padding": _get_int("UI_LAYOUT_HEADER_TOP_PADDING", 12),
        "card_padding": _get_int("UI_LAYOUT_CARD_PADDING", 12),
        "sidebar_edge_padding": _get_int("UI_LAYOUT_SIDEBAR_EDGE_PADDING", 16),
        "sidebar_inner_padding": _get_int("UI_LAYOUT_SIDEBAR_INNER_PADDING", 12),
        "status_card_height": _get_int("UI_LAYOUT_STATUS_CARD_HEIGHT", 34),
        "primary_button_height": _get_int("UI_LAYOUT_PRIMARY_BUTTON_HEIGHT", 36),
        "input_height": _get_int("UI_LAYOUT_INPUT_HEIGHT", 36),
        "segment_height": _get_int("UI_LAYOUT_SEGMENT_HEIGHT", 36),
        "guide_header_height": _get_int("UI_LAYOUT_GUIDE_HEADER_HEIGHT", 36),
        "guide_toggle_width": _get_int("UI_LAYOUT_GUIDE_TOGGLE_WIDTH", 88),
        "recommend_card_height": _get_int("UI_LAYOUT_RECOMMEND_CARD_HEIGHT", 82),
        "action_button_height": _get_int("UI_LAYOUT_ACTION_BUTTON_HEIGHT", 24),
        "status_badge_width": _get_int("UI_LAYOUT_STATUS_BADGE_WIDTH", 116),
        "status_badge_text_padding": _get_int("UI_LAYOUT_STATUS_BADGE_TEXT_PADDING", 28),
        "action_run_width": _get_int("UI_LAYOUT_ACTION_RUN_WIDTH", 108),
        "action_copy_width": _get_int("UI_LAYOUT_ACTION_COPY_WIDTH", 64),
        "action_download_width": _get_int("UI_LAYOUT_ACTION_DOWNLOAD_WIDTH", 94),
        "action_guide_width": _get_int("UI_LAYOUT_ACTION_GUIDE_WIDTH", 84),
        "action_stack_breakpoint": _get_int("UI_LAYOUT_ACTION_STACK_BREAKPOINT", 260),
        "support_min_width": _get_int("UI_LAYOUT_SUPPORT_MIN_WIDTH", 190),
        "support_max_width": _get_int("UI_LAYOUT_SUPPORT_MAX_WIDTH", 280),
        "support_width_ratio": _get_float("UI_LAYOUT_SUPPORT_WIDTH_RATIO", 0.29),
        "detail_min_width": _get_int("UI_LAYOUT_DETAIL_MIN_WIDTH", 260),
    },
    "font_sizes": {
        "sidebar_title": _get_int("UI_FONT_SIZE_SIDEBAR_TITLE", 18),
        "sidebar_text": _get_int("UI_FONT_SIZE_SIDEBAR_TEXT", 12),
        "sidebar_text_small": _get_int("UI_FONT_SIZE_SIDEBAR_TEXT_SMALL", 11),
        "status_dot": _get_int("UI_FONT_SIZE_STATUS_DOT", 14),
        "button": _get_int("UI_FONT_SIZE_BUTTON", 13),
        "spec_label": _get_int("UI_FONT_SIZE_SPEC_LABEL", 10),
        "spec_value": _get_int("UI_FONT_SIZE_SPEC_VALUE", 13),
        "spec_sub": _get_int("UI_FONT_SIZE_SPEC_SUB", 10),
        "main_title": _get_int("UI_FONT_SIZE_MAIN_TITLE", 28),
        "main_desc": _get_int("UI_FONT_SIZE_MAIN_DESC", 14),
        "input": _get_int("UI_FONT_SIZE_INPUT", 13),
        "segment": _get_int("UI_FONT_SIZE_SEGMENT", 12),
        "guide": _get_int("UI_FONT_SIZE_GUIDE", 11),
        "recommend_title": _get_int("UI_FONT_SIZE_RECOMMEND_TITLE", 12),
        "recommend_cat": _get_int("UI_FONT_SIZE_RECOMMEND_CAT", 9),
        "recommend_name": _get_int("UI_FONT_SIZE_RECOMMEND_NAME", 11),
        "recommend_badge": _get_int("UI_FONT_SIZE_RECOMMEND_BADGE", 8),
        "empty_state": _get_int("UI_FONT_SIZE_EMPTY_STATE", 14),
        "rec_badge": _get_int("UI_FONT_SIZE_REC_BADGE", 9),
        "model_name": _get_int("UI_FONT_SIZE_MODEL_NAME", 15),
        "model_meta": _get_int("UI_FONT_SIZE_MODEL_META", 12),
        "model_desc": _get_int("UI_FONT_SIZE_MODEL_DESC", 12),
        "status_badge": _get_int("UI_FONT_SIZE_STATUS_BADGE", 11),
        "model_req": _get_int("UI_FONT_SIZE_MODEL_REQ", 11),
        "model_details": _get_int("UI_FONT_SIZE_MODEL_DETAILS", 13),
        "model_tip": _get_int("UI_FONT_SIZE_MODEL_TIP", 11),
        "action": _get_int("UI_FONT_SIZE_ACTION", 12),
    },
}

UI_COLORS = {
    "background": _get_str("UI_COLOR_BACKGROUND", "#0B0F19"),
    "sidebar_background": _get_str("UI_COLOR_SIDEBAR_BACKGROUND", "#0D111C"),
    "card": _get_str("UI_COLOR_CARD", "#111827"),
    "border": _get_str("UI_COLOR_BORDER", "#1F2937"),
    "sidebar_border": _get_str("UI_COLOR_SIDEBAR_BORDER", "#1E293B"),
    "hover": _get_str("UI_COLOR_HOVER", "#3B82F6"),
    "text_primary": _get_str("UI_COLOR_TEXT_PRIMARY", "#F9FAFB"),
    "text_muted": _get_str("UI_COLOR_TEXT_MUTED", "#9CA3AF"),
    "text_subtle": _get_str("UI_COLOR_TEXT_SUBTLE", "#6B7280"),
    "guide_background": _get_str("UI_COLOR_GUIDE_BACKGROUND", "#1E1E2F"),
    "guide_border": _get_str("UI_COLOR_GUIDE_BORDER", "#2D2D44"),
    "guide_text": _get_str("UI_COLOR_GUIDE_TEXT", "#A5B4FC"),
    "success": _get_str("UI_COLOR_SUCCESS", "#10B981"),
    "warning": _get_str("UI_COLOR_WARNING", "#F59E0B"),
    "danger": _get_str("UI_COLOR_DANGER", "#EF4444"),
    "button_secondary": _get_str("UI_COLOR_BUTTON_SECONDARY", "#1E293B"),
    "button_secondary_hover": _get_str("UI_COLOR_BUTTON_SECONDARY_HOVER", "#334155"),
    "button_dark": _get_str("UI_COLOR_BUTTON_DARK", "#1F2937"),
    "button_dark_hover": _get_str("UI_COLOR_BUTTON_DARK_HOVER", "#374151"),
    "button_green": _get_str("UI_COLOR_BUTTON_GREEN", "#10B981"),
    "button_green_hover": _get_str("UI_COLOR_BUTTON_GREEN_HOVER", "#059669"),
    "button_blue": _get_str("UI_COLOR_BUTTON_BLUE", "#3B82F6"),
    "button_blue_hover": _get_str("UI_COLOR_BUTTON_BLUE_HOVER", "#2563EB"),
    "white": _get_str("UI_COLOR_WHITE", "#FFFFFF"),
    "recommend_title": _get_str("UI_COLOR_RECOMMEND_TITLE", "#F59E0B"),
    "recommend_great_text": _get_str("UI_COLOR_RECOMMEND_GREAT_TEXT", "#818CF8"),
    "recommend_normal_text": _get_str("UI_COLOR_RECOMMEND_NORMAL_TEXT", "#9CA3AF"),
    "tip_text": _get_str("UI_COLOR_TIP_TEXT", "#34D399"),
    "requirements_text": _get_str("UI_COLOR_REQUIREMENTS_TEXT", "#818CF8"),
}

UI_TEXT = {
    "sidebar_title": _get_str("UI_TEXT_SIDEBAR_TITLE", "MI HARDWARE 🖥️"),
    "sidebar_subtitle": _get_str("UI_TEXT_SIDEBAR_SUBTITLE", "Recursos detectados en tu máquina:"),
    "software_title": _get_str("UI_TEXT_SOFTWARE_TITLE", "MI SOFTWARE 🛠️"),
    "software_subtitle": _get_str("UI_TEXT_SOFTWARE_SUBTITLE", "Entornos y drivers de compilación:"),
    "main_title": _get_str("UI_TEXT_MAIN_TITLE", "Can I Run Local AI? 🚀"),
    "main_description": _get_str("UI_TEXT_MAIN_DESCRIPTION", "Evaluación automatizada de compatibilidad optimizada por Sistema Operativo."),
    "search_placeholder": _get_str("UI_TEXT_SEARCH_PLACEHOLDER", "🔍 Buscar modelos (ej. DeepSeek, Llama...)"),
    "guide_text": _get_str(
        "UI_TEXT_GUIDE",
        "💡 ¿Cómo ejecutar estos modelos? 1. Instala Ollama (para LLMs) o LM Studio. 2. Abre tu terminal y escribe: 'ollama run [nombre-modelo]' (ej: 'ollama run deepseek-r1:8b'). 3. Para generar imágenes, usa Stable Diffusion WebUI, ComfyUI o Draw Things.",
    ),
    "guide_title": _get_str("UI_TEXT_GUIDE_TITLE", "Guía rápida"),
    "guide_hide": _get_str("UI_TEXT_GUIDE_HIDE", "Ocultar"),
    "guide_show": _get_str("UI_TEXT_GUIDE_SHOW", "Mostrar"),
    "scan_status_running": _get_str("UI_TEXT_SCAN_RUNNING", "Escaneando hardware y runtimes del sistema..."),
    "scan_status_success": _get_str("UI_TEXT_SCAN_SUCCESS", "Sistema analizado correctamente"),
    "scan_status_error": _get_str("UI_TEXT_SCAN_ERROR", "Error al escanear"),
    "database_searching": _get_str("UI_TEXT_DATABASE_SEARCHING", "Base de Datos: Buscando..."),
    "database_online": _get_str("UI_TEXT_DATABASE_ONLINE", "Base de Datos: Online (Sincronizada)"),
    "database_offline": _get_str("UI_TEXT_DATABASE_OFFLINE", "Base de Datos: Offline (Local)"),
    "database_cached": _get_str("UI_TEXT_DATABASE_CACHED", "Base de Datos: Cache local"),
    "database_missing": _get_str("UI_TEXT_DATABASE_MISSING", "Base de Datos: Sin cache"),
    "scan_status_idle": _get_str("UI_TEXT_SCAN_IDLE", "Listo para analizar el equipo"),
    "rescan": _get_str("UI_TEXT_RESCAN", "🔄 Volver a Escanear"),
    "analyze": _get_str("UI_TEXT_ANALYZE", "🔎 Analizar equipo"),
    "scan_in_progress": _get_str("UI_TEXT_SCAN_IN_PROGRESS", "⌛ Escaneando..."),
    "loading_modal_title": _get_str("UI_TEXT_LOADING_MODAL_TITLE", "Analizando equipo"),
    "loading_modal_body": _get_str("UI_TEXT_LOADING_MODAL_BODY", "Escaneando hardware, memoria, GPU y runtimes locales.\nEspera un momento..."),
    "empty_state_title": _get_str("UI_TEXT_EMPTY_STATE_TITLE", "Analiza tu equipo para ver compatibilidad"),
    "empty_state_body": _get_str("UI_TEXT_EMPTY_STATE_BODY", "La aplicación puede cargar resultados desde cache o ejecutar un análisis nuevo cuando tú lo indiques."),
    "recommend_title": _get_str("UI_TEXT_RECOMMEND_TITLE", "🏆 MODELOS TOP RECOMENDADOS PARA TU PC"),
    "empty_models": _get_str("UI_TEXT_EMPTY_MODELS", "No se encontraron modelos que coincidan con la búsqueda."),
    "recommended_badge": _get_str("UI_TEXT_RECOMMENDED_BADGE", "✨ RECOMENDADO PARA TU PC"),
    "python_not_detected": _get_str("UI_TEXT_PYTHON_NOT_DETECTED", "Desconocida"),
    "python_env_default": _get_str("UI_TEXT_PYTHON_ENV_DEFAULT", "System"),
    "cuda_not_detected": _get_str("UI_TEXT_CUDA_NOT_DETECTED", "No Detectado"),
    "cuda_missing_support": _get_str("UI_TEXT_CUDA_MISSING_SUPPORT", "Sin GPU NVIDIA o Driver CUDA"),
    "rocm_not_detected": _get_str("UI_TEXT_ROCM_NOT_DETECTED", "No Detectado"),
    "rocm_missing_support": _get_str("UI_TEXT_ROCM_MISSING_SUPPORT", "Sin soporte AMD ROCm/HIP"),
    "compilers_missing": _get_str("UI_TEXT_COMPILERS_MISSING", "Ninguno Detectado"),
    "compilers_missing_help": _get_str("UI_TEXT_COMPILERS_MISSING_HELP", "Instala MSVC/GCC/Clang para construir de fuentes"),
    "compilers_ready": _get_str("UI_TEXT_COMPILERS_READY", "Listos para compilar dependencias"),
    "gpu_none": _get_str("UI_TEXT_GPU_NONE", "Sin GPU dedicada"),
    "gpu_none_help": _get_str("UI_TEXT_GPU_NONE_HELP", "Usa gráficos integrados / CPU"),
    "ram_system": _get_str("UI_TEXT_RAM_SYSTEM", "Memoria del Sistema"),
    "ram_unified": _get_str("UI_TEXT_RAM_UNIFIED", "Memoria Unificada"),
    "memory_pool_label": _get_str("UI_TEXT_MEMORY_POOL_LABEL", "Memoria compartida/unificada | Pool"),
    "memory_reported_label": _get_str("UI_TEXT_MEMORY_REPORTED_LABEL", "VRAM reportada"),
    "vram_dedicated_label": _get_str("UI_TEXT_VRAM_DEDICATED_LABEL", "VRAM dedicada"),
    "cpu_architecture_label": _get_str("UI_TEXT_CPU_ARCHITECTURE_LABEL", "Arquitectura"),
    "cpu_cores_label": _get_str("UI_TEXT_CPU_CORES_LABEL", "Núcleos"),
    "cpu_threads_label": _get_str("UI_TEXT_CPU_THREADS_LABEL", "hilos"),
    "cpu_physical_label": _get_str("UI_TEXT_CPU_PHYSICAL_LABEL", "físicos"),
    "cpu_avx2_label": _get_str("UI_TEXT_CPU_AVX2_LABEL", "AVX2"),
    "avx2_yes": _get_str("UI_TEXT_AVX2_YES", "Sí"),
    "avx2_no": _get_str("UI_TEXT_AVX2_NO", "No"),
    "requirements_base_label": _get_str("UI_TEXT_REQUIREMENTS_BASE_LABEL", "Requisitos base"),
    "requirements_ram_cpu_label": _get_str("UI_TEXT_REQUIREMENTS_RAM_CPU_LABEL", "RAM (CPU)"),
    "cuda_supported_label": _get_str("UI_TEXT_CUDA_SUPPORTED_LABEL", "CUDA Soportado"),
    "driver_label": _get_str("UI_TEXT_DRIVER_LABEL", "Driver"),
    "nvcc_missing": _get_str("UI_TEXT_NVCC_MISSING", " (Sin NVCC)"),
    "rocm_detected": _get_str("UI_TEXT_ROCM_DETECTED", "ROCm/HIP Detectado"),
    "version_label": _get_str("UI_TEXT_VERSION_LABEL", "Versión"),
    "clipboard_title": _get_str("UI_TEXT_CLIPBOARD_TITLE", "Copiado"),
    "clipboard_body": _get_str("UI_TEXT_CLIPBOARD_BODY", "Copiado al portapapeles:\n\n{value}"),
    "command_copied_title": _get_str("UI_TEXT_COMMAND_COPIED_TITLE", "Comando Copiado"),
    "command_copied_body": _get_str("UI_TEXT_COMMAND_COPIED_BODY", "Se copió el comando al portapapeles:\n\n{value}"),
    "terminal_missing_body": _get_str("UI_TEXT_TERMINAL_MISSING_BODY", "No se encontró un emulador de terminal compatible.\nSe copió el comando al portapapeles:\n\n{value}"),
    "ollama_missing_title": _get_str("UI_TEXT_OLLAMA_MISSING_TITLE", "Ollama No Detectado"),
    "ollama_missing_body": _get_str("UI_TEXT_OLLAMA_MISSING_BODY", "Ollama no parece estar instalado o configurado en tu PATH.\n\nPor favor, instala Ollama desde https://ollama.com antes de intentar ejecutar este modelo."),
    "ollama_install_body": _get_str("UI_TEXT_OLLAMA_INSTALL_BODY", "No se encontró Ollama en este equipo.\n\nPuedes abrir la descarga oficial o copiar un comando de instalación recomendado para tu sistema operativo."),
    "ollama_install_open_site": _get_str("UI_TEXT_OLLAMA_INSTALL_OPEN_SITE", "Abrir descarga oficial"),
    "ollama_install_copy_command": _get_str("UI_TEXT_OLLAMA_INSTALL_COPY_COMMAND", "Copiar comando"),
    "ollama_install_close": _get_str("UI_TEXT_OLLAMA_INSTALL_CLOSE", "Cerrar"),
    "ollama_install_command_missing": _get_str("UI_TEXT_OLLAMA_INSTALL_COMMAND_MISSING", "No hay un comando de instalación configurado para este sistema.\nSe abrirá la página oficial de descarga."),
    "error_title": _get_str("UI_TEXT_ERROR_TITLE", "Error"),
    "scan_error_body": _get_str("UI_TEXT_SCAN_ERROR_BODY", "Ocurrió un error al detectar los recursos:\n{value}"),
    "terminal_open_error": _get_str("UI_TEXT_TERMINAL_OPEN_ERROR", "No se pudo abrir la terminal: {value}"),
    "image_guide_title": _get_str("UI_TEXT_IMAGE_GUIDE_TITLE", "Guía de Uso - {value}"),
    "image_guide_body": _get_str(
        "UI_TEXT_IMAGE_GUIDE_BODY",
        "Guía para ejecutar {value} localmente:\n\n1. Descarga el archivo del modelo (.safetensors) usando el botón de HuggingFace.\n2. Instala una interfaz compatible como:\n   - ComfyUI (Recomendado, muy rápido e intermedio)\n   - Draw Things (Excelente para macOS con CoreML/Metal)\n   - Automatic1111 (Estándar de la industria)\n3. Coloca el archivo descargado en la carpeta de modelos de tu interfaz (por ejemplo, 'models/Stable-diffusion' o 'models/checkpoints').\n4. Inicia la interfaz y selecciona el modelo para empezar a generar imágenes.",
    ),
    "disk_label": _get_str("UI_TEXT_DISK_LABEL", "Disco"),
    "disk_subtitle": _get_str("UI_TEXT_DISK_SUBTITLE", "{free_disk} GB libres"),
    "disk_warning": _get_str("UI_TEXT_DISK_WARNING", "⚠️ Falta disco: se requieren {disk_needed:.1f} GB pero solo quedan {free_disk:.1f} GB libres"),
}

UI_SPEC_CARDS = {
    "os":        {"title": _get_str("UI_CARD_OS_TITLE",        "SISTEMA (OS)"),        "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_OS_ICON",        "💻")},
    "cpu":       {"title": _get_str("UI_CARD_CPU_TITLE",       "PROCESADOR (CPU)"),    "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_CPU_ICON",       "🧠")},
    "ram":       {"title": _get_str("UI_CARD_RAM_TITLE",       "MEMORIA RAM"),         "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_RAM_ICON",       "💾")},
    "gpu":       {"title": _get_str("UI_CARD_GPU_TITLE",       "GRÁFICOS (GPU)"),      "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_GPU_ICON",       "⚡")},
    "disk":      {"title": _get_str("UI_CARD_DISK_TITLE",      "DISCO"),               "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_DISK_ICON",      "📁")},
    "python":    {"title": _get_str("UI_CARD_PYTHON_TITLE",    "PYTHON"),              "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_PYTHON_ICON",    "🐍")},
    "cuda":      {"title": _get_str("UI_CARD_CUDA_TITLE",      "NVIDIA CUDA"),         "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_CUDA_ICON",      "💚")},
    "rocm":      {"title": _get_str("UI_CARD_ROCM_TITLE",      "AMD ROCm"),            "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_ROCM_ICON",       "❤️")},
    "compilers": {"title": _get_str("UI_CARD_COMPILERS_TITLE", "COMPILADORES"),        "value": _get_str("UI_CARD_DEFAULT_VALUE", "Detectando..."), "icon": _get_str("UI_CARD_COMPILERS_ICON", "🔧")},
}

UI_ACTIONS = {
    "linux_terminal_candidates": _get_json(
        "UI_LINUX_TERMINALS",
        ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"],
    ),
    "ollama_command_template": _get_str("UI_OLLAMA_COMMAND_TEMPLATE", "ollama run {tag}"),
    "ollama_download_url": _get_str("UI_OLLAMA_DOWNLOAD_URL", "https://ollama.com/download"),
    "ollama_install_commands": _get_json(
        "UI_OLLAMA_INSTALL_COMMANDS",
        {
            "Windows": "winget install Ollama.Ollama",
            "Darwin": "brew install --cask ollama",
            "Linux": "curl -fsSL https://ollama.com/install.sh | sh",
        },
    ),
}

MODEL_STATUS_COLORS = {
    "RUNS_GREAT": _get_str("MODEL_STATUS_COLOR_RUNS_GREAT", "#10B981"),
    "RUNS_WELL": _get_str("MODEL_STATUS_COLOR_RUNS_WELL", "#34D399"),
    "DECENT_SLOW": _get_str("MODEL_STATUS_COLOR_DECENT_SLOW", "#F59E0B"),
    "TIGHT_FIT": _get_str("MODEL_STATUS_COLOR_TIGHT_FIT", "#F97316"),
    "TOO_HEAVY": _get_str("MODEL_STATUS_COLOR_TOO_HEAVY", "#EF4444"),
}

MODEL_STATUS_LABELS = {
    "RUNS_GREAT": _get_str("MODEL_STATUS_LABEL_RUNS_GREAT", "Funciona Excelente"),
    "RUNS_WELL": _get_str("MODEL_STATUS_LABEL_RUNS_WELL", "Funciona Bien"),
    "DECENT_SLOW": _get_str("MODEL_STATUS_LABEL_DECENT_SLOW", "Lento (CPU)"),
    "TIGHT_FIT": _get_str("MODEL_STATUS_LABEL_TIGHT_FIT", "Ajustado (Lento)"),
    "TOO_HEAVY": _get_str("MODEL_STATUS_LABEL_TOO_HEAVY", "Demasiado Pesado"),
}

MODEL_TEXT = {
    "cpu_only_name": _get_str("MODEL_TEXT_CPU_ONLY_NAME", "CPU Only"),
    "image_category": _get_str("MODEL_TEXT_IMAGE_CATEGORY", "Image Generation"),
    "llm_category": _get_str("MODEL_TEXT_LLM_CATEGORY", "Text (LLM)"),
    "os_tip_image_nvidia": _get_str("MODEL_TEXT_OS_TIP_IMAGE_NVIDIA", "🪟/🐧 CUDA ofrece el rendimiento óptimo y nativo para este modelo."),
    "os_tip_image_nvidia_macos": _get_str("MODEL_TEXT_OS_TIP_IMAGE_NVIDIA_MACOS", "CUDA detectado."),
    "os_tip_image_amd_windows": _get_str("MODEL_TEXT_OS_TIP_IMAGE_AMD_WINDOWS", "🪟 En Windows (DirectML), AMD puede ser lento generando imágenes. Linux (ROCm) es mucho más rápido."),
    "os_tip_image_amd_linux": _get_str("MODEL_TEXT_OS_TIP_IMAGE_AMD_LINUX", "🐧 Excelente rendimiento nativo en Linux usando la arquitectura ROCm de AMD."),
    "os_tip_image_apple": _get_str("MODEL_TEXT_OS_TIP_IMAGE_APPLE", "🍎 Optimizado nativamente en Mac usando CoreML/Metal (Apps como Draw Things)."),
    "os_tip_llm_amd_windows": _get_str("MODEL_TEXT_OS_TIP_LLM_AMD_WINDOWS", "🪟 Ollama usará Vulkan para tu gráfica AMD. Funciona bien, pero en Linux tendrías mayor velocidad."),
    "os_tip_llm_nvidia_linux": _get_str("MODEL_TEXT_OS_TIP_LLM_NVIDIA_LINUX", "🐧 La combinación Linux + NVIDIA ofrece la menor latencia posible para LLMs locales."),
    "os_tip_llm_windows_cpu": _get_str("MODEL_TEXT_OS_TIP_LLM_WINDOWS_CPU", "🪟 Windows consume mucha RAM en segundo plano. Cierra navegadores pesados para liberar CPU/RAM."),
    "os_tip_llm_apple": _get_str("MODEL_TEXT_OS_TIP_LLM_APPLE", "🍎 Ollama aprovecha el framework MLX/Metal de Apple. Rendimiento espectacular y silencioso."),
    "apple_details_great": _get_str("MODEL_TEXT_APPLE_DETAILS_GREAT", "Carga completa en memoria unificada ({vram_needed}GB req, {total_ram}GB total). Muy rápido."),
    "apple_details_well": _get_str("MODEL_TEXT_APPLE_DETAILS_WELL", "Cabe en memoria unificada, pero dejará poco espacio para macOS y otras apps."),
    "apple_details_tight": _get_str("MODEL_TEXT_APPLE_DETAILS_TIGHT", "Al límite de la memoria unificada. Provocará swapping y ralentizará el Mac."),
    "apple_details_heavy": _get_str("MODEL_TEXT_APPLE_DETAILS_HEAVY", "Requiere {vram_needed}GB. Tu Mac de {total_ram}GB no tiene memoria suficiente."),
    "gpu_details_great": _get_str("MODEL_TEXT_GPU_DETAILS_GREAT", "Se ejecuta 100% en la GPU ({vendor}) usando {vram_needed}GB de VRAM."),
    "gpu_details_well": _get_str("MODEL_TEXT_GPU_DETAILS_WELL", "GPU VRAM ({max_vram}GB) comparte carga con la RAM. Funcionamiento fluido."),
    "gpu_details_cpu_slow": _get_str("MODEL_TEXT_GPU_DETAILS_CPU_SLOW", "VRAM insuficiente. Se apoyará fuertemente en CPU/RAM. Será lento."),
    "gpu_details_tight": _get_str("MODEL_TEXT_GPU_DETAILS_TIGHT", "Cabe en la RAM pero de forma muy ajustada. Riesgo de cuelgues del sistema operativo."),
    "gpu_details_heavy": _get_str("MODEL_TEXT_GPU_DETAILS_HEAVY", "Demasiado pesado. Requiere ~{adjusted_ram_needed}GB libres (ajustado por OS)."),
    "cpu_details_decent": _get_str("MODEL_TEXT_CPU_DETAILS_DECENT", "Sin GPU dedicada. Correrá en CPU. Funcional pero a baja velocidad."),
    "cpu_details_tight": _get_str("MODEL_TEXT_CPU_DETAILS_TIGHT", "Ajustado al límite de la RAM. El sistema {system_os} podría congelarse temporalmente."),
    "cpu_details_heavy": _get_str("MODEL_TEXT_CPU_DETAILS_HEAVY", "Falta memoria RAM. Requiere ~{adjusted_ram_needed}GB para operar estable en CPU."),
}
