# -*- coding: utf-8 -*-

import os
import sys
import json
from . import config

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # One level up from src/models.py
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load models database dynamically from remote URL with local fallback
# Updates local models.json automatically on successful download
def load_models_data():
    import urllib.request
    current_dir = get_base_dir()
    local_json_path = os.path.join(current_dir, "data", "models.json")
    
    url = config.ONLINE_MODELS_URL
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        # 3 seconds timeout to keep startup and scan fast
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 0:
                # Successfully loaded. Save it to local models.json to update it!
                try:
                    with open(local_json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print("Offline database updated successfully from online source.")
                except Exception as save_err:
                    print(f"Failed to update offline database locally: {save_err}")
                return data, True
    except Exception as e:
        print(f"Error fetching online models from {url}: {e}. Falling back to offline database.")
    
    # Offline fallback (loads the local models.json which might have been updated previously)
    try:
        if os.path.exists(local_json_path):
            with open(local_json_path, "r", encoding="utf-8") as f:
                return json.load(f), False
    except Exception as e:
        print(f"Error loading offline models.json: {e}")
        
    # Secondary fallback to local models_online.json if models.json has issues
    try:
        local_online_path = os.path.join(current_dir, "data", "models_online.json")
        if os.path.exists(local_online_path):
            with open(local_online_path, "r", encoding="utf-8") as f:
                return json.load(f), False
    except Exception:
        pass
        
    return [], False

TIER_COLORS = {
    "RUNS_GREAT": "#10B981", # Emerald Green
    "RUNS_WELL": "#34D399",  # Light Green
    "DECENT_SLOW": "#F59E0B",# Amber/Yellow
    "TIGHT_FIT": "#F97316",  # Orange
    "TOO_HEAVY": "#EF4444"   # Red
}

TIER_LABELS = {
    "RUNS_GREAT": "Funciona Excelente",
    "RUNS_WELL": "Funciona Bien",
    "DECENT_SLOW": "Lento (CPU)",
    "TIGHT_FIT": "Ajustado (Lento)",
    "TOO_HEAVY": "Demasiado Pesado"
}

def evaluate_compatibility(specs):
    # Support both old flat specs and new nested specs dictionary
    hw_specs = specs.get("hardware", specs)
    
    total_ram = hw_specs["ram"]
    is_apple_silicon = hw_specs["is_apple_silicon"]
    system_os = hw_specs["os"] # 'Windows', 'Linux', 'Darwin'
    
    # Find active GPU with maximum VRAM
    gpus = hw_specs["gpus"]
    max_vram = 0.0
    has_discrete_gpu = False
    active_gpu_name = "CPU Only"
    active_gpu_vendor = "Other"
    
    if gpus:
        # Sort to find the best GPU
        best_gpu = max(gpus, key=lambda g: g["vram"])
        max_vram = best_gpu["vram"]
        active_gpu_name = best_gpu["name"]
        active_gpu_vendor = best_gpu["vendor"]
        if best_gpu["vendor"] in ["NVIDIA", "AMD", "Apple"] and max_vram > 1.0:
            has_discrete_gpu = True

    rated_models = []
    models_db, is_online = load_models_data()
    for model in models_db:
        vram_needed = model["vram_q4"]
        ram_needed = model["ram_q4"]
        
        status = "TOO_HEAVY"
        details = ""
        os_tip = ""
        
        # OS-SPECIFIC RAM ADJUSTMENTS
        # Linux is lightweight, Windows is heavy. We adjust the required RAM buffer.
        os_ram_penalty = 0.0
        if system_os == "Windows":
            os_ram_penalty = config.OS_RAM_PENALTY_WINDOWS
        elif system_os == "Linux":
            os_ram_penalty = config.OS_RAM_PENALTY_LINUX
            
        adjusted_ram_needed = ram_needed + os_ram_penalty

        # ==========================================
        # OS & GPU SYNERGY TIPS
        # ==========================================
        if model["category"] == "Image Generation":
            if active_gpu_vendor == "NVIDIA":
                os_tip = "🪟/🐧 CUDA ofrece el rendimiento óptimo y nativo para este modelo." if system_os in ["Windows", "Linux"] else "CUDA detectado."
            elif active_gpu_vendor == "AMD" and system_os == "Windows":
                os_tip = "🪟 En Windows (DirectML), AMD puede ser lento generando imágenes. Linux (ROCm) es mucho más rápido."
            elif active_gpu_vendor == "AMD" and system_os == "Linux":
                os_tip = "🐧 Excelente rendimiento nativo en Linux usando la arquitectura ROCm de AMD."
            elif system_os == "Darwin" and is_apple_silicon:
                os_tip = "🍎 Optimizado nativamente en Mac usando CoreML/Metal (Apps como Draw Things)."
                
        elif model["category"] == "Text (LLM)":
            if active_gpu_vendor == "AMD" and system_os == "Windows":
                os_tip = "🪟 Ollama usará Vulkan para tu gráfica AMD. Funciona bien, pero en Linux tendrías mayor velocidad."
            elif active_gpu_vendor == "NVIDIA" and system_os == "Linux":
                os_tip = "🐧 La combinación Linux + NVIDIA ofrece la menor latencia posible para LLMs locales."
            elif system_os == "Windows" and not has_discrete_gpu:
                os_tip = "🪟 Windows consume mucha RAM en segundo plano. Cierra navegadores pesados para liberar CPU/RAM."
            elif system_os == "Darwin" and is_apple_silicon:
                os_tip = "🍎 Ollama aprovecha el framework MLX/Metal de Apple. Rendimiento espectacular y silencioso."

        # ==========================================
        # HARDWARE EVALUATION LOGIC
        # ==========================================
        if is_apple_silicon:
            # macOS Unified Memory
            usable_memory = total_ram
            
            if usable_memory >= vram_needed + config.MAC_RAM_BUFFER_GREAT:
                status = "RUNS_GREAT"
                details = f"Carga completa en memoria unificada ({vram_needed}GB req, {total_ram}GB total). Muy rápido."
            elif usable_memory >= vram_needed + config.MAC_RAM_BUFFER_WELL:
                status = "RUNS_WELL"
                details = f"Cabe en memoria unificada, pero dejará poco espacio para macOS y otras apps."
            elif usable_memory >= vram_needed:
                status = "TIGHT_FIT"
                details = f"Al límite de la memoria unificada. Provocará swapping y ralentizará el Mac."
            else:
                status = "TOO_HEAVY"
                details = f"Requiere {vram_needed}GB. Tu Mac de {total_ram}GB no tiene memoria suficiente."
                
        else:
            # Windows / Linux (Dedicated GPU + System RAM)
            if has_discrete_gpu:
                if max_vram >= vram_needed + config.WIN_VRAM_BUFFER_GREAT:
                    status = "RUNS_GREAT"
                    details = f"Se ejecuta 100% en la GPU ({active_gpu_vendor}) usando {vram_needed}GB de VRAM."
                elif max_vram >= vram_needed * config.WIN_VRAM_MULTIPLIER_WELL and total_ram >= adjusted_ram_needed + config.WIN_RAM_BUFFER_GPU_WELL:
                    status = "RUNS_WELL"
                    details = f"GPU VRAM ({max_vram}GB) comparte carga con la RAM. Funcionamiento fluido."
                elif total_ram >= adjusted_ram_needed + config.CPU_RAM_BUFFER_DECENT:
                    status = "DECENT_SLOW"
                    details = f"VRAM insuficiente. Se apoyará fuertemente en CPU/RAM. Será lento."
                elif total_ram >= adjusted_ram_needed + config.CPU_RAM_BUFFER_TIGHT:
                    status = "TIGHT_FIT"
                    details = f"Cabe en la RAM pero de forma muy ajustada. Riesgo de cuelgues del sistema operativo."
                else:
                    status = "TOO_HEAVY"
                    details = f"Demasiado pesado. Requiere ~{round(adjusted_ram_needed, 1)}GB libres (ajustado por OS)."
            else:
                # CPU Only
                if total_ram >= adjusted_ram_needed + config.CPU_RAM_BUFFER_DECENT:
                    status = "DECENT_SLOW"
                    details = f"Sin GPU dedicada. Correrá en CPU. Funcional pero a baja velocidad."
                elif total_ram >= adjusted_ram_needed + config.CPU_RAM_BUFFER_TIGHT:
                    status = "TIGHT_FIT"
                    details = f"Ajustado al límite de la RAM. El sistema {system_os} podría congelarse temporalmente."
                else:
                    status = "TOO_HEAVY"
                    details = f"Falta memoria RAM. Requiere ~{round(adjusted_ram_needed, 1)}GB para operar estable en CPU."

        rated_models.append({
            **model,
            "status": status,
            "color": TIER_COLORS[status],
            "status_label": TIER_LABELS[status],
            "details": details,
            "os_tip": os_tip
        })
        
    # Select recommended models (Top 3-4 models that are ideal for the system)
    # Filter to compatible models (RUNS_GREAT or RUNS_WELL)
    compatible_llms = [m for m in rated_models if m["category"] == "Text (LLM)" and m["status"] in ["RUNS_GREAT", "RUNS_WELL"]]
    compatible_imgs = [m for m in rated_models if m["category"] == "Image Generation" and m["status"] in ["RUNS_GREAT", "RUNS_WELL"]]
    
    # Fallback if no models are RUNS_GREAT/WELL: try DECENT_SLOW, then TIGHT_FIT
    if not compatible_llms:
        compatible_llms = [m for m in rated_models if m["category"] == "Text (LLM)" and m["status"] == "DECENT_SLOW"]
    if not compatible_llms:
        compatible_llms = [m for m in rated_models if m["category"] == "Text (LLM)" and m["status"] == "TIGHT_FIT"]
        
    if not compatible_imgs:
        compatible_imgs = [m for m in rated_models if m["category"] == "Image Generation" and m["status"] == "DECENT_SLOW"]
    if not compatible_imgs:
        compatible_imgs = [m for m in rated_models if m["category"] == "Image Generation" and m["status"] == "TIGHT_FIT"]
        
    # Sort compatible models by requirements/capabilities (larger models first, as they have higher quality)
    compatible_llms.sort(key=lambda x: x["vram_q4"], reverse=True)
    compatible_imgs.sort(key=lambda x: x["vram_q4"], reverse=True)
    
    recommended_ids = set()
    # Recommend top 2 LLMs and top 2 Image models (up to 4 total)
    for m in compatible_llms[:2]:
        recommended_ids.add(m["id"])
    for m in compatible_imgs[:2]:
        recommended_ids.add(m["id"])
        
    # Mark models in the rated list
    for m in rated_models:
        m["recommended"] = m["id"] in recommended_ids
        
    return rated_models, is_online
