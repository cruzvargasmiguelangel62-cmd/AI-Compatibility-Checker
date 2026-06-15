# -*- coding: utf-8 -*-
import os
import platform
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
        self.pending_models = []
        self.model_row_widgets = []
        self.is_closing = False
        self.loading_modal = None
        self.guide_visible = True

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
        self.search_query = ""
        self.online_mode = False

        self.active_quantization = config.DEFAULT_QUANTIZATION
        self.active_context_size = config.DEFAULT_CONTEXT_SIZE
        self.active_language = config.DEFAULT_LANGUAGE
        self.installed_ollama_models = []
        self.ollama_api_online = False
        self.change_language(self.active_language)

        self.create_layout()
        self.bind("<Configure>", self._on_window_resize)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.load_cached_snapshot()
        self.refresh_installed_ollama_models()

    def _normalize_rated_models(self, rated_models):
        normalized = []
        for model in rated_models or []:
            if hasattr(model, "to_dict"):
                normalized.append(model.to_dict())
            elif isinstance(model, dict):
                normalized.append(model)
        return normalized

    def load_cached_snapshot(self):
        cached_snapshot = get_cached_snapshot()
        if cached_snapshot is None:
            self.specs = None
            self.rated_models = []
            self.online_mode = False
            self.set_idle_state()
            return

        self.specs = cached_snapshot
        rated_models, self.online_mode = evaluate_compatibility(
            self.specs,
            quantization=self.active_quantization,
            context_size=self.active_context_size,
        )
        self.rated_models = self._normalize_rated_models(rated_models)
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
            rated_models, self.online_mode = evaluate_compatibility(
                self.specs,
                quantization=self.active_quantization,
                context_size=self.active_context_size,
            )
            self.rated_models = self._normalize_rated_models(rated_models)
            if not self.is_closing and self.winfo_exists():
                self.after(0, self.update_scan_results)
        except Exception as err:
            if not self.is_closing and self.winfo_exists():
                self.after(0, lambda: self.show_scan_error(err))

    def trigger_catalog_update(self):
        if self.is_closing:
            return
        self.update_catalog_btn.configure(state="disabled", text=UI_TEXT.get("catalog_updating", "Actualizando..."))

        def worker():
            from src.updater import update_models_catalog
            res = update_models_catalog()
            if not self.is_closing and self.winfo_exists():
                self.after(0, lambda: self._on_catalog_update_done(res))

        threading.Thread(target=worker, daemon=True).start()

    def _on_catalog_update_done(self, res):
        if self.is_closing or not self.winfo_exists():
            return
        self.update_catalog_btn.configure(state="normal", text=UI_TEXT.get("btn_update_catalog", "🔄 Actualizar Catálogo Online"))

        if res.get("success", False):
            # Re-evaluate with the new models if hardware specs have been detected
            if self.specs is not None:
                rated_models, self.online_mode = evaluate_compatibility(
                    self.specs,
                    quantization=self.active_quantization,
                    context_size=self.active_context_size,
                )
                self.rated_models = self._normalize_rated_models(rated_models)
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
        self.after(0, lambda snap=snapshot: self._apply_background_snapshot(snap))

    def _apply_background_snapshot(self, snapshot):
        if self.is_closing or not self.winfo_exists():
            return
        self.specs = snapshot
        rated_models, self.online_mode = evaluate_compatibility(
            self.specs,
            quantization=self.active_quantization,
            context_size=self.active_context_size,
        )
        self.rated_models = self._normalize_rated_models(rated_models)
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
        self.pending_models = []
        try:
            self.quit()
        except tk.TclError:
            pass
        try:
            self.destroy()
        except tk.TclError:
            pass

    def refresh_installed_ollama_models(self):
        import threading
        def worker():
            online = self.ping_ollama()
            if online:
                models = self.get_installed_ollama_models()
            else:
                models = []
            
            # Update GUI safely in main thread
            if not self.is_closing:
                try:
                    self.after(0, lambda o=online, m=models: self._update_ollama_status_gui(o, m))
                except Exception:
                    pass
            
        threading.Thread(target=worker, daemon=True).start()

    def _update_ollama_status_gui(self, online, models):
        self.ollama_api_online = online
        self.installed_ollama_models = models
        if hasattr(self, "db_status_dot"):
            dot_color = UI_COLORS["success"] if online else UI_COLORS["danger"]
            label_text = UI_TEXT["ollama_api_online"] if online else UI_TEXT["ollama_api_offline"]

            if hasattr(self, "ollama_status_dot"):
                self.ollama_status_dot.configure(text_color=dot_color)
                self.ollama_status_label.configure(text=label_text)
                
        # Re-evaluate models locally since list of installed models changed
        if self.specs is not None:
            rated_models, self.online_mode = evaluate_compatibility(
                self.specs,
                quantization=self.active_quantization,
                context_size=self.active_context_size,
            )
            self.rated_models = self._normalize_rated_models(rated_models)
        
        # Redraw model rows to update buttons and badges!
        if hasattr(self, "scroll_frame"):
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
