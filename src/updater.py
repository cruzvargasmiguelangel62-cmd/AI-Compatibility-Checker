# -*- coding: utf-8 -*-
"""
updater.py
----------
Queries the Hugging Face API for popular GGUF model repositories,
parses parameters, estimates memory, and updates the models database.
"""

import json
import os
import re
import urllib.request
from src import config

__all__ = ["update_models_catalog"]


def update_models_catalog() -> dict:
    """
    Query Hugging Face API for popular GGUF model repositories,
    parse parameters size, estimate RAM/VRAM requirements,
    and update data/models.json and data/models_online.json
    without deleting pre-existing entries.

    Returns a dict: {'success': bool, 'added': int, 'total': int, 'error': str}
    """
    url = "https://huggingface.co/api/models?filter=gguf&sort=downloads&direction=-1&limit=40"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            models_data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "error": str(e), "added": 0, "total": 0}

    models_path = os.path.join(config.CURRENT_DIR, "data", "models.json")
    models_online_path = os.path.join(config.CURRENT_DIR, "data", "models_online.json")

    # Read current models
    try:
        with open(models_path, "r", encoding="utf-8") as f:
            existing_models = json.load(f)
    except Exception:
        existing_models = []

    # Map existing entries by lowercase name or ollama_tag or id
    existing_ids = {m["id"] for m in existing_models}
    existing_tags = {m.get("ollama_tag") for m in existing_models if m.get("ollama_tag")}

    added_count = 0

    for item in models_data:
        repo_id = item.get("id", "")
        if not repo_id:
            continue

        repo_parts = repo_id.split("/")
        author = repo_parts[0] if len(repo_parts) > 1 else "Hugging Face"
        name_raw = repo_parts[-1]

        cleaned_id = repo_id.replace("/", "_").replace("-", "_").lower()

        # Check tags for parameter size (e.g. 7b, 8b)
        params_match = re.search(r"([0-9.]+)\s*[bB]", name_raw)
        if not params_match:
            for tag in item.get("tags", []):
                m = re.match(r"^([0-9.]+)[bB]$", tag)
                if m:
                    params_match = m
                    break

        if not params_match:
            continue  # Skip if we cannot infer parameter size

        try:
            params_b = float(params_match.group(1))
        except ValueError:
            continue

        # Format clean name
        name_clean = name_raw.replace("-GGUF", "").replace("-gguf", "").replace("-", " ")
        name_clean = " ".join([w.capitalize() for w in name_clean.split()])

        # Guess Ollama tag
        ollama_tag = ""
        name_lower = name_clean.lower()
        param_str = params_match.group(1).lower()

        if "llama" in name_lower:
            v_num = "4" if "4" in name_lower else "3.1" if "3.1" in name_lower else "3"
            ollama_tag = f"llama{v_num}:{param_str}"
        elif "qwen" in name_lower:
            v_num = "2.5" if "2.5" in name_lower else "3" if "3" in name_lower else ""
            prefix = f"qwen{v_num}" if v_num else "qwen"
            if "coder" in name_lower:
                ollama_tag = f"{prefix}-coder:{param_str}"
            else:
                ollama_tag = f"{prefix}:{param_str}"
        elif "gemma" in name_lower:
            v_num = "2" if "2" in name_lower else "3" if "3" in name_lower else "4" if "4" in name_lower else ""
            prefix = f"gemma{v_num}" if v_num else "gemma"
            ollama_tag = f"{prefix}:{param_str}"
        elif "phi" in name_lower:
            v_num = "4" if "4" in name_lower else "3"
            if "mini" in name_lower:
                ollama_tag = f"phi{v_num}:mini"
            else:
                ollama_tag = f"phi{v_num}:{param_str}"
        elif "mistral" in name_lower:
            ollama_tag = "mistral"
        elif "glm" in name_lower:
            ollama_tag = f"glm4:{param_str}"
        elif "deepseek" in name_lower:
            if "r1" in name_lower:
                ollama_tag = f"deepseek-r1:{param_str}"
            elif "coder" in name_lower:
                ollama_tag = f"deepseek-coder-v2:{param_str}"

        # Prevent duplicate entries by ID or Ollama tag
        if cleaned_id in existing_ids:
            continue
        if ollama_tag and ollama_tag in existing_tags:
            continue

        # Resource estimates for Q4 quantization
        vram_est = round(params_b * 0.6 + 0.5, 1)
        ram_est = round(params_b * 0.95 + 1.0, 1)

        category = "Text (LLM)"
        if item.get("pipeline_tag") in ["image-to-text", "text-to-image"]:
            category = "Image Generation"

        new_model = {
            "id": cleaned_id,
            "name": name_clean,
            "category": category,
            "params": f"{params_match.group(1)} Billion",
            "context": "8K ctx",
            "vram_q4": vram_est,
            "ram_q4": ram_est,
            "description": f"Modelo {name_clean} alojado en Hugging Face ({author}). Descubierto y analizado de forma automática.",
            "provider": f"{author} / HuggingFace"
        }

        if ollama_tag:
            new_model["ollama_tag"] = ollama_tag
            new_model["provider"] = f"{author} / Ollama"
        else:
            new_model["download_url"] = f"https://huggingface.co/{repo_id}"

        existing_models.append(new_model)
        existing_ids.add(cleaned_id)
        if ollama_tag:
            existing_tags.add(ollama_tag)
        added_count += 1

    if added_count > 0:
        for path in [models_path, models_online_path]:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing_models, f, ensure_ascii=False, indent=2)
        from .models import clear_models_cache
        clear_models_cache()

    return {"success": True, "added": added_count, "total": len(existing_models)}
