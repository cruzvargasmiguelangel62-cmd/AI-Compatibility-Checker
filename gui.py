# -*- coding: utf-8 -*-
import os
import platform
import queue
import threading
import tkinter as tk

import customtkinter as ctk

from src import config
from src.cache import get_cached_snapshot, get_snapshot
from src.gui_actions import AppActionsMixin
from src.gui_layout import AppLayoutMixin
from src.gui_text import AppTextMixin
from src.models import evaluate_compatibility

UI_BASE = config.UI_BASE
UI_COLORS = config.UI_COLORS
UI_TEXT = config.UI_TEXT
UI_LAYOUT = config.UI_BASE["layout"]


class App(AppLayoutMixin, AppActionsMixin, AppTextMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        self.platform_name = platform.system()
        self.ui_tokens = self._build_ui_tokens()
        self.font_cache = {}
        self.responsive_mode = None
        self.resize_job = None
        self.render_job = None
        self.search_debounce_job = None
        self.pending_models = []
        self.model_row_widgets = []
        self.widgets_to_destroy = []
        self.destroy_job = None
        self.is_closing = False
        self.loading_modal = None
        self.guide_visible = True
        self._last_ollama_signature = None
        self._last_rated_models_signature = None
        self._ui_queue = queue.Queue()
        self._ui_queue_job = None

        ctk.set_appearance_mode(config.APP_THEME)
        ctk.set_default_color_theme(config.APP_COLOR_THEME)

        self._configure_typography()
        self._configure_scaling(config.APP_SCALING)
        self._configure_window()

        self.bg_color = UI_COLORS["background"]
        self.card_color = UI_COLORS["card"]
        self.border_color = UI_COLORS["border"]
        self.hover_color = UI_COLORS["hover"]
        self.text_primary = UI_COLORS["text_primary"]
        self.text_muted = UI_COLORS["text_muted"]
        self.configure(fg_color=self.bg_color)

        self.specs = None
        self.rated_models = []
        self.active_category = UI_BASE["search_categories"][0]
        self.active_use_case = "all"
        self.search_query = ""
        self.online_mode = False
        self.comparison_models = []
        self._new_models_pending = []

        self.active_quantization = config.DEFAULT_QUANTIZATION
        self.active_context_size = config.DEFAULT_CONTEXT_SIZE
        self.active_language = config.DEFAULT_LANGUAGE
        self.installed_ollama_models = []
        self.ollama_api_online = False
        self.change_language(self.active_language)

        self._ollama_poll_job = None
        self.create_layout()
        self.bind("<Configure>", self._on_window_resize)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._schedule_ui_queue_drain()
        # Defer all heavy work so the window can paint its first frame before blocking
        self.after(50, self._startup_sequence)


    def _normalize_rated_models(self, rated_models):
        normalized = []
        for model in rated_models or []:
            if hasattr(model, "to_dict"):
                normalized.append(model.to_dict())
            elif isinstance(model, dict):
                normalized.append(model)
        return normalized

    def _build_ollama_signature(self, online, models):
        normalized_models = tuple(sorted((model or "").strip().lower() for model in models or []))
        return online, normalized_models

    def _build_rated_models_signature(self, rated_models):
        normalized = self._normalize_rated_models(rated_models)
        return tuple(
            (
                model.get("id"),
                model.get("status"),
                model.get("recommended"),
                model.get("vram_q4"),
                model.get("ram_q4"),
                model.get("ollama_tag"),
            )
            for model in normalized
        )

    def _store_compatibility_results(self, rated_models, online_mode):
        normalized = self._normalize_rated_models(rated_models)
        new_signature = self._build_rated_models_signature(normalized)
        changed = (
            new_signature != self._last_rated_models_signature
            or online_mode != self.online_mode
        )
        self.online_mode = online_mode
        self.rated_models = normalized
        self._last_rated_models_signature = new_signature
        return changed

    def call_in_ui_thread(self, callback):
        if self.is_closing:
            return False
        self._ui_queue.put(callback)
        return True

    def _schedule_ui_queue_drain(self):
        if self.is_closing:
            return
        self._ui_queue_job = self.after(16, self._drain_ui_queue)

    def _drain_ui_queue(self):
        self._ui_queue_job = None
        if self.is_closing:
            return
        drained = 0
        for _ in range(50):
            try:
                callback = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
                drained += 1
            except Exception:
                pass
        # Always reschedule — background threads add items asynchronously.
        # Use a longer interval when idle to reduce wake-ups.
        interval = 16 if drained > 0 else 200
        self._ui_queue_job = self.after(interval, self._drain_ui_queue)

    def _get_local_extra_models(self) -> list[dict]:
        extra_models = []
        if not self.ollama_api_online or not self.installed_ollama_models:
            return extra_models

        from src.models import load_models_data
        try:
            models_db, _ = load_models_data()
        except Exception:
            models_db = []
        
        existing_tags = set()
        for m in models_db:
            tag = m.get("ollama_tag")
            if tag:
                existing_tags.add(tag.lower())

        import re
        for tag in self.installed_ollama_models:
            tag_lower = tag.lower()
            
            is_matched = False
            for ext_tag in existing_tags:
                if tag_lower == ext_tag or f"{tag_lower}:" in f"{ext_tag}:" or f"{ext_tag}:" in f"{tag_lower}:":
                    is_matched = True
                    break
            
            if not is_matched:
                params_match = re.search(r"([0-9.]+)\s*([bBmM])", tag)
                params_b = 8.0
                if params_match:
                    try:
                        val = float(params_match.group(1))
                        unit = params_match.group(2).lower()
                        if unit == 'b':
                            params_b = val
                        elif unit == 'm':
                            params_b = val / 1000.0
                    except ValueError:
                        pass
                else:
                    if "70b" in tag_lower:
                        params_b = 70.0
                    elif "32b" in tag_lower:
                        params_b = 32.0
                    elif "13b" in tag_lower:
                        params_b = 13.0
                    elif "8b" in tag_lower:
                        params_b = 8.0
                    elif "7b" in tag_lower:
                        params_b = 7.0
                    elif "3b" in tag_lower:
                        params_b = 3.0
                    elif "1.5b" in tag_lower:
                        params_b = 1.5

                vram_est = round(params_b * 0.6 + 0.5, 1)
                ram_est = round(params_b * 0.95 + 1.0, 1)
                
                clean_name = tag.split(":")[0].replace("-", " ").replace("_", " ").title()
                if ":" in tag:
                    clean_name += f" ({tag.split(':')[1]})"

                extra_models.append({
                    "id": f"local_{tag.replace(':', '_').replace('-', '_').lower()}",
                    "name": clean_name,
                    "category": "Text (LLM)",
                    "params": f"{params_b} Billion" if params_b >= 0.1 else f"{int(params_b * 1000)} Million",
                    "context": "8K ctx",
                    "vram_q4": vram_est,
                    "ram_q4": ram_est,
                    "description": f"Modelo local detectado en tu instancia de Ollama.",
                    "provider": "Ollama (Local)",
                    "ollama_tag": tag
                })
        return extra_models

    def evaluate_compatibility_with_local(self):
        if self.specs is None:
            return [], False
        
        extra = self._get_local_extra_models()
        return evaluate_compatibility(
            self.specs,
            quantization=self.active_quantization,
            context_size=self.active_context_size,
            extra_models=extra
        )

    def _toggle_comparison(self, model, checked):
        if checked:
            if len(self.comparison_models) >= 4:
                return
            if model not in self.comparison_models:
                self.comparison_models.append(model)
        else:
            if model in self.comparison_models:
                self.comparison_models.remove(model)
        self._update_compare_button()

    def _update_compare_button(self):
        count = len(self.comparison_models)
        if count >= 2:
            if not hasattr(self, "compare_floating_btn") or self.compare_floating_btn is None:
                import customtkinter as ctk
                self.compare_floating_btn = ctk.CTkButton(
                    self.main_container,
                    text=UI_TEXT.get("compare_btn", "Comparar").format(count=count),
                    font=self._font("action", weight="bold"),
                    fg_color="#7C3AED",
                    hover_color="#6D28D9",
                    text_color=UI_COLORS["white"],
                    height=36,
                    corner_radius=18,
                    command=self.show_comparison_modal,
                )
            self.compare_floating_btn.configure(
                text=UI_TEXT.get("compare_btn", "Comparar").format(count=count)
            )
            self.compare_floating_btn.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
        elif hasattr(self, "compare_floating_btn") and self.compare_floating_btn is not None:
            self.compare_floating_btn.place_forget()

    def show_comparison_modal(self):
        if not self.comparison_models:
            return
        import customtkinter as ctk

        modal = ctk.CTkToplevel(self)
        modal.title(UI_TEXT.get("compare_title", "Comparar Modelos"))
        modal.geometry("700x400")
        modal.resizable(True, False)
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=UI_COLORS["background"])

        header = ctk.CTkFrame(modal, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(header, text=UI_TEXT.get("compare_title", "Comparar Modelos"), font=self._font("main_title", weight="bold"), text_color=self.text_primary).pack(side="left")

        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        cols = len(self.comparison_models)
        for ci, col in enumerate(scroll.winfo_children()):
            col.destroy()

        table = ctk.CTkFrame(scroll, fg_color="transparent")
        table.pack(fill="x")
        for i in range(cols + 1):
            table.grid_columnconfigure(i, weight=1 if i > 0 else 0, minsize=100)

        fields = [
            ("", lambda m: ""),
            (UI_TEXT.get("compare_header_model", "Modelo"), lambda m: m.get("name", "")),
            (UI_TEXT.get("compare_header_status", "Estado"), lambda m: m.get("status_label", "")),
            (UI_TEXT.get("compare_header_vram", "VRAM"), lambda m: f"{m.get('vram_q4', 0)} GB"),
            (UI_TEXT.get("compare_header_ram", "RAM"), lambda m: f"{m.get('ram_q4', 0)} GB"),
            (UI_TEXT.get("compare_header_speed", "Velocidad"), lambda m: self._get_speed_str(m)),
        ]

        for ri, (label, getter) in enumerate(fields):
            lbl = ctk.CTkLabel(table, text=label, font=self._font("sidebar_text_small", weight="bold") if ri > 0 else self._font("action"), text_color=self.text_muted if ri > 0 else "transparent", anchor="w", width=80)
            lbl.grid(row=ri, column=0, sticky="w", padx=(0, 8), pady=4)
            for ci, model in enumerate(self.comparison_models):
                val = getter(model)
                if ri == 0:
                    ctk.CTkLabel(table, text="", height=2).grid(row=ri, column=ci + 1, sticky="ew", pady=2)
                elif ri == 2:
                    color = model.get("color", self.text_primary)
                    ctk.CTkLabel(table, text=val.upper(), font=self._font("action", weight="bold"), text_color=color, anchor="center").grid(row=ri, column=ci + 1, sticky="ew", pady=4)
                else:
                    ctk.CTkLabel(table, text=val, font=self._font("sidebar_text"), text_color=self.text_primary, anchor="center").grid(row=ri, column=ci + 1, sticky="ew", pady=4)

    def _get_speed_str(self, model):
        if self.specs is None:
            return "-"
        if model.get("category") == config.MODEL_TEXT.get("image_category", "Image Generation"):
            return "-"
        from src.models import estimate_tokens_per_sec
        info = estimate_tokens_per_sec(model.get("vram_q4", 0), self.specs)
        return f"~{info['tps']} tok/s ({info['backend']})"


    def _startup_sequence(self):
        """Runs after the window has rendered its first frame."""
        if self.is_closing:
            return
        self.load_cached_snapshot()
        self.refresh_installed_ollama_models()
        self._schedule_ollama_poll()
        self._auto_update_catalog_background()
        self._check_first_run()

    def _auto_update_catalog_background(self):
        old_ids = {m.get("id") for m in self.rated_models}

        def worker():
            if self.is_closing:
                return
            try:
                from src.updater import auto_update_catalog_if_stale
                result = auto_update_catalog_if_stale()
                if result.get("success") and not result.get("skipped") and result.get("added", 0) > 0:
                    if self.specs is not None:
                        rated_models, online_mode = self.evaluate_compatibility_with_local()
                        self._store_compatibility_results(rated_models, online_mode)
                        new_ids = {m.get("id") for m in self.rated_models} - old_ids
                        self._new_models_pending = [
                            m for m in self.rated_models
                            if m.get("id") in new_ids and m.get("status") != "TOO_HEAVY"
                        ]
                        self.call_in_ui_thread(self._show_new_models_banner)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _show_new_models_banner(self):
        if self.is_closing or not self.winfo_exists():
            return
        new_models = self._new_models_pending
        if not new_models:
            return
        if not hasattr(self, "new_models_frame") or self.new_models_frame is None:
            import customtkinter as ctk
            self.new_models_frame = ctk.CTkFrame(
                self.main_container,
                fg_color="#1E3A5F",
                border_color="#3B82F6",
                border_width=1,
                corner_radius=8,
            )
            self.new_models_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 6), before=self.header_frame)
            self.main_container.grid_rowconfigure(0, weight=0)

            lang = self.active_language
            count = len(new_models)
            if lang == "es":
                banner_text = f"🆕 {count} modelo(s) nuevo(s) compatible(s) encontrado(s)!"
            else:
                banner_text = f"🆕 {count} new compatible model(s) found!"

            lbl = ctk.CTkLabel(
                self.new_models_frame,
                text=banner_text,
                font=self._font("sidebar_text", weight="bold"),
                text_color="#93C5FD",
            )
            lbl.pack(side="left", padx=12, pady=8)

            def dismiss():
                if self.new_models_frame:
                    self.new_models_frame.destroy()
                    self.new_models_frame = None
                    self._new_models_pending = []
            btn = ctk.CTkButton(
                self.new_models_frame,
                text="✕",
                font=self._font("action"),
                fg_color="transparent",
                hover_color="#2563EB",
                text_color="#93C5FD",
                width=28,
                height=28,
                command=dismiss,
            )
            btn.pack(side="right", padx=8, pady=8)

            names = ", ".join(m.get("name", "") for m in new_models[:3])
            if len(new_models) > 3:
                names += f" +{len(new_models) - 3}"
            detail_lbl = ctk.CTkLabel(
                self.new_models_frame,
                text=names,
                font=self._font("sidebar_text_small"),
                text_color="#BFDBFE",
            )
            detail_lbl.pack(side="left", padx=(0, 8), pady=8)

    def load_cached_snapshot(self):
        import threading
        cached_snapshot = get_cached_snapshot()
        if cached_snapshot is None:
            self.specs = None
            self.rated_models = []
            self.online_mode = False
            self.set_idle_state()
            return

        self.specs = cached_snapshot

        def _eval_worker():
            if self.is_closing:
                return
            try:
                rated_models, online_mode = self.evaluate_compatibility_with_local()
            except Exception:
                rated_models, online_mode = [], False
            self.call_in_ui_thread(lambda: self._apply_cached_results(rated_models, online_mode))

        threading.Thread(target=_eval_worker, daemon=True).start()

    def _apply_cached_results(self, rated_models, online_mode):
        """Called on main thread after background cache evaluation completes."""
        if self.is_closing or not self.winfo_exists():
            return
        self._store_compatibility_results(rated_models, online_mode)
        self.update_scan_results(from_cache=True)

    def set_idle_state(self):
        self.rescan_btn.configure(state="normal", text=UI_TEXT["analyze"])
        self.scan_status_label.configure(text=UI_TEXT["scan_status_idle"], text_color=UI_COLORS["text_muted"])
        self.db_status_dot.configure(text_color=UI_COLORS["warning"])
        self.db_status_label.configure(text=UI_TEXT["database_missing"])
        self.render_empty_state()

    def _build_ui_tokens(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        dpi_scale = self.winfo_fpixels("1i") / 72.0
        geometry_config = UI_BASE["window_geometry"].get(
            self.platform_name,
            UI_BASE["window_geometry"]["default"],
        )
        font_family = UI_BASE["font_family"].get(
            self.platform_name,
            UI_BASE["font_family"]["default"],
        )
        sidebar_width = UI_BASE["sidebar_width"].get(
            self.platform_name,
            UI_BASE["sidebar_width"]["default"],
        )
        return {
            "font_family": font_family,
            "sidebar_width": sidebar_width,
            "screen_width": screen_width,
            "screen_height": screen_height,
            "dpi_scale": dpi_scale,
            "initial_width": min(
                geometry_config["initial_width_max"],
                max(geometry_config["initial_width_min"], int(screen_width * geometry_config["initial_width_ratio"])),
            ),
            "initial_height": min(
                geometry_config["initial_height_max"],
                max(geometry_config["initial_height_min"], int(screen_height * geometry_config["initial_height_ratio"])),
            ),
            "min_width": max(
                geometry_config["min_width_floor"],
                int(screen_width * geometry_config["min_width_ratio"]),
            ),
            "min_height": max(
                geometry_config["min_height_floor"],
                int(screen_height * geometry_config["min_height_ratio"]),
            ),
            "main_padding": UI_LAYOUT["main_padding"],
            "main_padding_compact": UI_LAYOUT["main_padding_compact"],
            "responsive_padding": UI_LAYOUT["responsive_padding"],
            "section_gap": UI_LAYOUT["section_gap"],
            "section_gap_tight": UI_LAYOUT["section_gap_tight"],
        }

    def _resolve_scaling_value(self, requested_scale):
        try:
            env_scale = float(os.environ.get("UI_SCALE", "0"))
        except Exception:
            env_scale = 0.0
        if env_scale > 0:
            return env_scale, env_scale

        base_tk_scale = UI_BASE["tk_scaling"].get(self.platform_name, UI_BASE["tk_scaling"]["default"])
        base_widget_scale = UI_BASE["widget_scaling"].get(self.platform_name, UI_BASE["widget_scaling"]["default"])
        dpi_scale = self.ui_tokens["dpi_scale"]
        if requested_scale != "auto":
            try:
                custom_scale = float(requested_scale)
                return custom_scale, custom_scale
            except ValueError:
                pass

        adaptive_scale = max(1.0, min(1.35, dpi_scale * base_widget_scale))
        return base_tk_scale * adaptive_scale, adaptive_scale

    def _configure_scaling(self, requested_scale):
        tk_scale, widget_scale = self._resolve_scaling_value(requested_scale)
        self.tk.call("tk", "scaling", tk_scale)
        ctk.set_widget_scaling(widget_scale)
        ctk.set_window_scaling(widget_scale)

    def _configure_window(self):
        self.title(UI_BASE["window_title"])
        self.geometry(f"{self.ui_tokens['initial_width']}x{self.ui_tokens['initial_height']}")
        self.minsize(self.ui_tokens["min_width"], self.ui_tokens["min_height"])

    def start_scan_thread(self, force_refresh=False):
        if self.is_closing:
            return
        self.rescan_btn.configure(state="disabled", text=UI_TEXT["scan_in_progress"])
        self.scan_status_label.configure(text=UI_TEXT["scan_status_running"], text_color=UI_COLORS["hover"])
        self.db_status_dot.configure(text_color=UI_COLORS["warning"])
        self.db_status_label.configure(text=UI_TEXT["database_searching"])
        self.show_loading_modal()

        worker = threading.Thread(target=self.perform_scan, args=(force_refresh,))
        worker.daemon = True
        worker.start()

    def perform_scan(self, force_refresh=False):
        try:
            self.specs = get_snapshot(
                force_refresh=force_refresh,
                on_background_done=self._on_background_snapshot,
            )
            rated_models, self.online_mode = self.evaluate_compatibility_with_local()
            self._store_compatibility_results(rated_models, self.online_mode)
            self.call_in_ui_thread(self.update_scan_results)
        except Exception as err:
            self.call_in_ui_thread(lambda: self.show_scan_error(err))

    def on_ollama_status_click(self):
        if self.is_closing:
            return
        if not self.ollama_api_online:
            self.show_ollama_install_modal()

    def trigger_catalog_update(self):
        if self.is_closing:
            return
        
        t_text = UI_TEXT.get("catalog_updating_title", "Actualizando Catálogo Online")
        b_text = UI_TEXT.get("catalog_updating_body", "Conectando con el servidor y descargando la base de datos de modelos...\nEspera un momento...")
        self.show_loading_modal(title_text=t_text, body_text=b_text)
        
        self.update_catalog_btn.configure(state="disabled", text=UI_TEXT.get("catalog_updating", "Actualizando..."))

        def worker():
            from src.updater import update_models_catalog
            res = update_models_catalog()
            self.call_in_ui_thread(lambda: self._on_catalog_update_done(res))

        threading.Thread(target=worker, daemon=True).start()

    def _check_first_run(self):
        import os
        flag_path = os.path.join(config.CURRENT_DIR, "data", ".first_run_done")
        if not os.path.exists(flag_path):
            self.after(500, self.show_first_time_wizard)

    def show_first_time_wizard(self):
        if self.is_closing or not self.winfo_exists():
            return
        import customtkinter as ctk
        import os

        self.wizard_step = 1
        self.wizard_use_case = "chat"
        self.wizard_space = "medium"

        modal = ctk.CTkToplevel(self)
        modal.title(UI_TEXT.get("wizard_title", "Bienvenido"))
        modal_width = min(440, max(380, self.winfo_screenwidth() - 420))
        modal_height = min(420, max(360, self.winfo_screenheight() - 320))
        modal.geometry(f"{modal_width}x{modal_height}")
        modal.minsize(380, 360)
        modal.resizable(True, True)
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=UI_COLORS["background"])

        modal.grid_rowconfigure(0, weight=1)
        modal.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(modal, fg_color=self.card_color, border_color=self.border_color, border_width=1, corner_radius=22)
        content.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(content, text="", font=self._font("model_name", weight="bold"), text_color=self.text_primary, anchor="w", justify="left")
        title_lbl.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))
        title_lbl.configure(wraplength=modal_width - 28)

        body_frame = ctk.CTkScrollableFrame(content, fg_color="transparent", border_width=0, corner_radius=0)
        body_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))
        body_frame.grid_columnconfigure(0, weight=1)
        body_frame.grid_rowconfigure(0, weight=1)
        body_frame.grid_rowconfigure(2, weight=1)

        nav_frame = ctk.CTkFrame(content, fg_color="transparent")
        nav_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        nav_frame.grid_columnconfigure(0, weight=1)
        nav_frame.grid_columnconfigure(1, weight=1)

        btn_back = ctk.CTkButton(nav_frame, text=UI_TEXT.get("wizard_back", "Atras"), font=self._font("action"), fg_color=UI_COLORS["button_secondary"], hover_color=UI_COLORS["button_secondary_hover"], text_color=self.text_primary, height=32, command=lambda: None)
        btn_back.grid(row=0, column=0, sticky="w")

        btn_next = ctk.CTkButton(nav_frame, text=UI_TEXT.get("wizard_next", "Siguiente"), font=self._font("action", weight="bold"), fg_color=UI_COLORS["button_blue"], hover_color=UI_COLORS["button_blue_hover"], text_color=UI_COLORS["white"], height=32, width=120, command=lambda: None)
        btn_next.grid(row=0, column=1, sticky="e")

        selected_lbl = ctk.CTkLabel(content, text="", font=self._font("sidebar_text_small", slant="italic"), text_color=self.text_muted)
        selected_lbl.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 6))

        def clear_body():
            for widget in body_frame.winfo_children():
                widget.destroy()

        def build_use_case_cards():
            clear_body()
            use_case_keys = [key for key in config.WIZARD_USE_CASE_KEYS if key in config.USE_CASES]
            cards_shell = ctk.CTkFrame(body_frame, fg_color="transparent")
            cards_shell.grid(row=1, column=0, sticky="nsew")
            cards_shell.grid_columnconfigure(0, weight=1)
            cards_shell.grid_rowconfigure(0, weight=1)
            cards_shell.grid_rowconfigure(2, weight=1)
            cards_frame = ctk.CTkFrame(cards_shell, fg_color="transparent")
            cards_frame.grid(row=1, column=0, sticky="ew")
            cards_frame.grid_columnconfigure(0, weight=1)
            columns = 1
            for index, key in enumerate(use_case_keys):
                meta = config.USE_CASES.get(key, {})
                icon = meta.get("icon", "")
                label = meta.get(f"label_{self.active_language}", meta.get("label_es", key))
                is_selected = key == self.wizard_use_case
                btn = ctk.CTkButton(
                    cards_frame,
                    text=f"{icon}  {label}",
                    font=self._font("sidebar_text_small", weight="bold"),
                    fg_color=UI_COLORS["hover"] if is_selected else "#1A2332",
                    hover_color="#2563EB",
                    border_color=UI_COLORS["hover"] if is_selected else "#334155",
                    border_width=2,
                    text_color=UI_COLORS["white"],
                    height=36,
                    corner_radius=14,
                    command=lambda k=key: select_uc(k),
                )
                btn.grid(row=index, column=0, sticky="ew", pady=3)
            selected_lbl.configure(text="")

        def show_step(step):
            clear_body()
            self.wizard_step = step

            if step == 1:
                title_lbl.configure(text=UI_TEXT.get("wizard_step1_title", "¿Que quieres hacer?"), wraplength=modal_width - 28)
                btn_back.configure(state="disabled")
                btn_next.configure(text=UI_TEXT.get("wizard_next", "Siguiente"), state="normal", command=lambda: show_step(2))
                build_use_case_cards()

            elif step == 2:
                title_lbl.configure(text=UI_TEXT.get("wizard_step2_title", "¿Cuanto espacio puedes dedicar?"), wraplength=modal_width - 28)
                btn_back.configure(state="normal", command=lambda: show_step(1))
                btn_next.configure(text=UI_TEXT.get("wizard_next", "Siguiente"), state="normal", command=lambda: show_step(3))
                space_shell = ctk.CTkFrame(body_frame, fg_color="transparent")
                space_shell.grid(row=1, column=0, sticky="nsew")
                space_shell.grid_columnconfigure(0, weight=1)
                space_shell.grid_rowconfigure(0, weight=1)
                space_shell.grid_rowconfigure(2, weight=1)
                space_cards_frame = ctk.CTkFrame(space_shell, fg_color="transparent")
                space_cards_frame.grid(row=1, column=0, sticky="ew")
                space_cards_frame.grid_columnconfigure(0, weight=1)
                spaces = [
                    (
                        "small",
                        "📦",
                        UI_TEXT.get("wizard_space_small", "Poco (< 10 GB)"),
                        UI_TEXT.get("wizard_space_small_desc", "Ideal para modelos de 1-3B"),
                    ),
                    (
                        "medium",
                        "📂",
                        UI_TEXT.get("wizard_space_medium", "Medio (10-30 GB)"),
                        UI_TEXT.get("wizard_space_medium_desc", "Perfecto para modelos de 7-14B"),
                    ),
                    (
                        "large",
                        "🗄️",
                        UI_TEXT.get("wizard_space_large", "Mucho (> 30 GB)"),
                        UI_TEXT.get("wizard_space_large_desc", "Modelos grandes de 32B+"),
                    ),
                ]
                for row, (key, icon, label, desc) in enumerate(spaces):
                    option_frame = ctk.CTkFrame(space_cards_frame, fg_color="transparent")
                    option_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))
                    option_frame.grid_columnconfigure(0, weight=1)
                    is_selected = key == self.wizard_space
                    btn = ctk.CTkButton(
                        option_frame,
                        text=f"{icon}  {label}",
                        font=self._font("sidebar_text_small", weight="bold"),
                        fg_color=UI_COLORS["hover"] if is_selected else "#1A2332",
                        hover_color="#2563EB",
                        border_color=UI_COLORS["hover"] if is_selected else "#334155",
                        border_width=2,
                        text_color=UI_COLORS["white"],
                        height=36,
                        corner_radius=14,
                        command=lambda k=key: select_sp(k),
                    )
                    btn.grid(row=0, column=0, sticky="ew")
                    desc_lbl = ctk.CTkLabel(option_frame, text=desc, font=self._font("sidebar_text_small"), text_color=self.text_muted)
                    desc_lbl.grid(row=1, column=0, sticky="w", padx=16, pady=(1, 0))
                selected_lbl.configure(text="")

            elif step == 3:
                title_lbl.configure(text=UI_TEXT.get("wizard_step3_title", "Estos son tus modelos recomendados"), wraplength=modal_width - 28)
                btn_back.configure(state="normal", command=lambda: show_step(2))
                btn_next.configure(text=UI_TEXT.get("wizard_finish", "Listo!"), state="normal", command=lambda: finish_wizard())
                uc_label = config.USE_CASES.get(self.wizard_use_case, {}).get(f"label_{self.active_language}", self.wizard_use_case)
                selected_lbl.configure(text=f"Uso: {uc_label}")
                space_map = {"small": 4.0, "medium": 16.0, "large": 40.0}
                max_vram = space_map.get(self.wizard_space, 16.0)
                suggestions = [m for m in self.rated_models if m.get("status") in ("RUNS_GREAT", "RUNS_WELL") and m.get("vram_q4", 0) <= max_vram]
                if self.wizard_use_case != "all":
                    suggestions = [m for m in suggestions if self.wizard_use_case in m.get("use_cases", [])]
                if not suggestions:
                    suggestions = [m for m in self.rated_models if m.get("status") in ("RUNS_GREAT", "RUNS_WELL")]
                suggestions = suggestions[:5]
                for m in suggestions:
                    row = ctk.CTkFrame(body_frame, fg_color=UI_COLORS["card"], corner_radius=8, border_color=self.border_color, border_width=1)
                    row.pack(fill="x", pady=3, padx=4)
                    ctk.CTkLabel(row, text=m["name"], font=self._font("model_name", weight="bold"), text_color=self.text_primary, anchor="w").pack(side="left", padx=10, pady=6)
                    badge = ctk.CTkLabel(row, text=m["status_label"], font=self._font("action", weight="bold"), fg_color=m["color"], text_color=UI_COLORS["white"], corner_radius=6, height=22)
                    badge.pack(side="right", padx=10, pady=6)
                    speed_info = estimate_tokens_per_sec(m["vram_q4"], self.specs) if self.specs else {"tps": 0, "backend": "?"}
                    speed_text = f"~{speed_info['tps']} tok/s"
                    ctk.CTkLabel(row, text=speed_text, font=self._font("sidebar_text_small"), text_color=self.text_muted).pack(side="right", padx=(0, 8), pady=6)
                if not suggestions:
                    ctk.CTkLabel(body_frame, text=UI_TEXT.get("wizard_no_suggestions", "Analiza tu equipo primero para ver recomendaciones personalizadas."), font=self._font("model_desc"), text_color=self.text_muted, wraplength=400).grid(row=0, column=0, sticky="ew", pady=20)

        def select_uc(key):
            self.wizard_use_case = key
            show_step(1)

        def select_sp(key):
            self.wizard_space = key
            show_step(2)

        def finish_wizard():
            flag_path = os.path.join(config.CURRENT_DIR, "data", ".first_run_done")
            try:
                with open(flag_path, "w") as f:
                    f.write("done")
            except Exception:
                pass
            self.active_use_case = self.wizard_use_case
            if hasattr(self, "use_case_buttons") and self.wizard_use_case in self.use_case_buttons:
                for k, btn in self.use_case_buttons.items():
                    btn.configure(fg_color=UI_COLORS["hover"] if k == self.wizard_use_case else UI_COLORS["button_secondary"])
            self.apply_filter()
            modal.destroy()

        from src.models import estimate_tokens_per_sec
        show_step(1)

    def _on_catalog_update_done(self, res):
        if self.is_closing or not self.winfo_exists():
            return
        self.hide_loading_modal()
        self.update_catalog_btn.configure(state="normal", text=UI_TEXT.get("btn_update_catalog", "🔄 Actualizar Catálogo Online"))

        if res.get("success", False):
            # Re-evaluate with the new models if hardware specs have been detected
            if self.specs is not None:
                rated_models, self.online_mode = self.evaluate_compatibility_with_local()
                self._store_compatibility_results(rated_models, self.online_mode)
                self.render_models_list()

            title = UI_TEXT.get("catalog_update_success_title", "Catálogo Actualizado")
            body = UI_TEXT.get("catalog_update_success_body", "Actualización completada.").format(
                added=res.get("added", 0),
                total=res.get("total", 0)
            )
            from tkinter import messagebox
            messagebox.showinfo(title, body)
        else:
            title = UI_TEXT.get("catalog_update_failed_title", "Error de Actualización")
            body = UI_TEXT.get("catalog_update_failed_body", "Error al actualizar:\n{error}").format(
                error=res.get("error", "Error desconocido")
            )
            from tkinter import messagebox
            messagebox.showerror(title, body)

    def _on_background_snapshot(self, snapshot):
        if self.is_closing or not self.winfo_exists():
            return
        self.call_in_ui_thread(lambda snap=snapshot: self._apply_background_snapshot(snap))

    def _apply_background_snapshot(self, snapshot):
        if self.is_closing or not self.winfo_exists():
            return
        self.specs = snapshot
        rated_models, self.online_mode = self.evaluate_compatibility_with_local()
        self._store_compatibility_results(rated_models, self.online_mode)
        self.update_scan_results()

    def on_close(self):
        if self.is_closing:
            return
        self.is_closing = True
        self.hide_loading_modal()
        if self.resize_job is not None:
            self.after_cancel(self.resize_job)
            self.resize_job = None
        if self.render_job is not None:
            self.after_cancel(self.render_job)
            self.render_job = None
        if self.search_debounce_job is not None:
            self.after_cancel(self.search_debounce_job)
            self.search_debounce_job = None
        if hasattr(self, "destroy_job") and self.destroy_job is not None:
            self.after_cancel(self.destroy_job)
            self.destroy_job = None
        if self._ui_queue_job is not None:
            self.after_cancel(self._ui_queue_job)
            self._ui_queue_job = None
        if hasattr(self, "_ollama_poll_job") and self._ollama_poll_job is not None:
            try:
                self.after_cancel(self._ollama_poll_job)
            except Exception:
                pass
            self._ollama_poll_job = None
        self.pending_models = []
        try:
            self.quit()
        except tk.TclError:
            pass
        try:
            self.destroy()
        except tk.TclError:
            pass

    def _schedule_ollama_poll(self):
        """Re-check Ollama status every 30 s so the indicator auto-updates."""
        if self.is_closing:
            return
        self._ollama_poll_job = self.after(30_000, self._run_ollama_poll)

    def _run_ollama_poll(self):
        if self.is_closing:
            return
        self.refresh_installed_ollama_models()
        self._schedule_ollama_poll()

    def refresh_installed_ollama_models(self):
        import threading
        def worker():
            online = self.ping_ollama()
            if online:
                models = self.get_installed_ollama_models()
            else:
                models = []
            
            self.call_in_ui_thread(lambda o=online, m=models: self._update_ollama_status_gui(o, m))
            
        threading.Thread(target=worker, daemon=True).start()

    def _update_ollama_status_gui(self, online, models):
        ollama_signature = self._build_ollama_signature(online, models)
        ollama_changed = ollama_signature != self._last_ollama_signature
        self._last_ollama_signature = ollama_signature
        self.ollama_api_online = online
        self.installed_ollama_models = models
        if hasattr(self, "db_status_dot"):
            dot_color = UI_COLORS["success"] if online else UI_COLORS["danger"]
            label_text = UI_TEXT["ollama_api_online"] if online else UI_TEXT["ollama_api_offline"]

            if hasattr(self, "ollama_status_dot"):
                self.ollama_status_dot.configure(text_color=dot_color)
                self.ollama_status_label.configure(text=label_text)
                
        # Re-evaluate only when Ollama availability or the installed model set changed.
        if self.specs is not None and ollama_changed:
            rated_models, self.online_mode = self.evaluate_compatibility_with_local()
            compatibility_changed = self._store_compatibility_results(rated_models, self.online_mode)
            if compatibility_changed and hasattr(self, "scroll_frame"):
                self.render_models_list()



if __name__ == "__main__":
    app = App()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        try:
            app.after(0, app.on_close)
            app.mainloop()
        except tk.TclError:
            pass
