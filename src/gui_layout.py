import tkinter as tk

import customtkinter as ctk

from src import config

UI_BASE = config.UI_BASE
UI_COLORS = config.UI_COLORS
UI_TEXT = config.UI_TEXT
UI_SPEC_CARDS = config.UI_SPEC_CARDS
UI_ACTIONS = config.UI_ACTIONS
UI_LAYOUT = config.UI_BASE["layout"]


class AppLayoutMixin:
    def _on_window_resize(self, event):
        if self.is_closing:
            return
        if event.widget is not self:
            return
        if self.resize_job is not None:
            self.after_cancel(self.resize_job)
        self.resize_job = self.after(80, self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        if self.is_closing or not self.winfo_exists():
            return
        self.resize_job = None
        current_width = max(self.winfo_width(), self.ui_tokens["initial_width"])
        new_mode = "stacked" if current_width < UI_LAYOUT["content_stack_breakpoint"] else "split"
        if new_mode != self.responsive_mode:
            self.responsive_mode = new_mode
            self.grid_columnconfigure(0, weight=0, minsize=self.ui_tokens["sidebar_width"])
            self.grid_columnconfigure(1, weight=1)
            if new_mode == "stacked":
                self.sidebar.grid(row=0, column=0, columnspan=2, sticky="ew")
                self.main_container.grid(
                    row=1,
                    column=0,
                    columnspan=2,
                    sticky="nsew",
                    padx=self.ui_tokens["main_padding_compact"],
                    pady=self.ui_tokens["main_padding_compact"],
                )
                self.control_frame.grid_columnconfigure(0, weight=1)
                self.control_frame.grid_columnconfigure(1, weight=1)
                self.search_entry.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 0), pady=(0, 8))
                self.category_selector.grid(row=1, column=0, columnspan=2, sticky="ew")
            else:
                self.sidebar.grid(row=0, column=0, columnspan=1, sticky="nsew")
                self.main_container.grid(
                    row=0,
                    column=1,
                    columnspan=1,
                    sticky="nsew",
                    padx=self.ui_tokens["responsive_padding"],
                    pady=self.ui_tokens["responsive_padding"],
                )
                self.control_frame.grid_columnconfigure(0, weight=1)
                self.control_frame.grid_columnconfigure(1, weight=0)
                self.search_entry.grid(row=0, column=0, columnspan=1, sticky="ew", padx=(0, 10), pady=(0, 0))
                self.category_selector.grid(row=0, column=1, columnspan=1, sticky="e")

        if hasattr(self, "guide_label"):
            self.guide_label.configure(wraplength=self._dynamic_wraplength(0.42, 220, 620))
        self._update_guide_visibility()

    def toggle_guide_visibility(self):
        self.guide_visible = not self.guide_visible
        self._update_guide_visibility()

    def _update_guide_visibility(self):
        if not hasattr(self, "guide_label") or not hasattr(self, "guide_toggle_btn"):
            return
        if self.guide_visible:
            self.guide_label.grid()
            self.guide_toggle_btn.configure(text=UI_TEXT["guide_hide"])
        else:
            self.guide_label.grid_remove()
            self.guide_toggle_btn.configure(text=UI_TEXT["guide_show"])

    def _bind_mousewheel_to_frame(self, frame):
        def _on_mousewheel(event):
            if event.num == 4 or event.delta > 0:
                frame._parent_canvas.yview_scroll(-5, "units")
            elif event.num == 5 or event.delta < 0:
                frame._parent_canvas.yview_scroll(5, "units")

        frame.bind("<Button-4>", _on_mousewheel, add="+")
        frame.bind("<Button-5>", _on_mousewheel, add="+")
        frame.bind("<MouseWheel>", _on_mousewheel, add="+")
        try:
            frame._parent_canvas.bind("<Button-4>", _on_mousewheel, add="+")
            frame._parent_canvas.bind("<Button-5>", _on_mousewheel, add="+")
            frame._parent_canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
        except Exception:
            pass

    def create_layout(self):
        self.grid_columnconfigure(0, weight=0, minsize=self.ui_tokens["sidebar_width"])
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.sidebar = ctk.CTkScrollableFrame(
            self,
            width=self.ui_tokens["sidebar_width"],
            corner_radius=0,
            fg_color=UI_COLORS["sidebar_background"],
            border_color=UI_COLORS["sidebar_border"],
            border_width=1,
            scrollbar_fg_color="transparent",
            scrollbar_button_color=UI_COLORS["sidebar_border"],
            scrollbar_button_hover_color=UI_COLORS["hover"],
            label_text="",
        )
        self.sidebar._scrollbar.configure(width=8, corner_radius=4)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self._bind_mousewheel_to_frame(self.sidebar)
        self.build_sidebar()

        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=self.bg_color)
        self.main_container.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=self.ui_tokens["main_padding"],
            pady=self.ui_tokens["main_padding"],
        )
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(3, weight=1)

        self.rec_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.rec_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.ui_tokens["section_gap"]))

        self.build_main_header()
        self.build_model_list_section()
        self.after(0, self._apply_responsive_layout)

    def build_sidebar(self):
        sidebar_edge_padding = UI_LAYOUT["sidebar_edge_padding"]
        sidebar_inner_padding = UI_LAYOUT["sidebar_inner_padding"]

        self.side_title = ctk.CTkLabel(
            self.sidebar,
            text=UI_TEXT["sidebar_title"],
            font=self._font("sidebar_title", weight="bold"),
            text_color=self.text_primary,
        )
        self.side_title.pack(padx=sidebar_edge_padding, pady=(UI_LAYOUT["header_top_padding"], 2), anchor="w")

        self.side_subtitle = ctk.CTkLabel(
            self.sidebar,
            text=UI_TEXT["sidebar_subtitle"],
            font=self._font("sidebar_text"),
            text_color=self.text_muted,
        )
        self.side_subtitle.pack(padx=sidebar_edge_padding, pady=(0, self.ui_tokens["section_gap"]), anchor="w")

        self.cards_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.cards_frame.pack(fill="both", expand=True, padx=sidebar_inner_padding, pady=0)
        for key in ("os", "cpu", "ram", "gpu"):
            card = self.create_spec_card(self.cards_frame, **UI_SPEC_CARDS[key])
            setattr(self, f"{key}_card", card)
            card.pack(fill="x", pady=3)

        self.soft_title = ctk.CTkLabel(
            self.sidebar,
            text=UI_TEXT["software_title"],
            font=self._font("sidebar_title", weight="bold"),
            text_color=self.text_primary,
        )
        self.soft_title.pack(padx=sidebar_edge_padding, pady=(16, 2), anchor="w")

        self.soft_subtitle = ctk.CTkLabel(
            self.sidebar,
            text=UI_TEXT["software_subtitle"],
            font=self._font("sidebar_text_small"),
            text_color=self.text_muted,
        )
        self.soft_subtitle.pack(padx=sidebar_edge_padding, pady=(0, 6), anchor="w")

        self.soft_cards_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.soft_cards_frame.pack(fill="both", expand=True, padx=sidebar_inner_padding, pady=0)
        for key in ("python", "cuda", "rocm", "compilers"):
            card = self.create_spec_card(self.soft_cards_frame, **UI_SPEC_CARDS[key])
            setattr(self, f"{key}_card", card)
            card.pack(fill="x", pady=3)

        # Settings section
        self.settings_title = ctk.CTkLabel(
            self.sidebar,
            text="SIMULACIÓN LOCAL ⚙" if self.active_language == "es" else "LOCAL SIMULATION ⚙",
            font=self._font("sidebar_title", weight="bold"),
            text_color=self.text_primary,
        )
        self.settings_title.pack(padx=sidebar_edge_padding, pady=(16, 2), anchor="w")

        self.settings_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.settings_frame.pack(fill="both", expand=True, padx=sidebar_inner_padding, pady=0)

        # Quantization Dropdown
        self.quant_label = ctk.CTkLabel(
            self.settings_frame,
            text="Cuantización" if self.active_language == "es" else "Quantization",
            font=self._font("sidebar_text_small", weight="bold"),
            text_color=self.text_muted,
        )
        self.quant_label.pack(anchor="w", padx=4, pady=(4, 2))

        self.quant_dropdown = ctk.CTkOptionMenu(
            self.settings_frame,
            values=["Q4_K_M", "Q2_K", "Q8_0", "FP16"],
            font=self._font("sidebar_text"),
            dropdown_font=self._font("sidebar_text"),
            fg_color=self.card_color,
            button_color=UI_COLORS["button_secondary"],
            button_hover_color=UI_COLORS["button_secondary_hover"],
            dropdown_fg_color=self.card_color,
            dropdown_hover_color=UI_COLORS["hover"],
            dropdown_text_color=self.text_primary,
            command=self.on_quant_change,
        )
        self.quant_dropdown.pack(fill="x", padx=4, pady=(0, 8))
        self.quant_dropdown.set(self.active_quantization)

        # Context Size Dropdown
        self.context_label = ctk.CTkLabel(
            self.settings_frame,
            text="Contexto (KV Cache)" if self.active_language == "es" else "Context (KV Cache)",
            font=self._font("sidebar_text_small", weight="bold"),
            text_color=self.text_muted,
        )
        self.context_label.pack(anchor="w", padx=4, pady=(4, 2))

        self.context_dropdown = ctk.CTkOptionMenu(
            self.settings_frame,
            values=["8K", "16K", "32K", "64K", "128K"],
            font=self._font("sidebar_text"),
            dropdown_font=self._font("sidebar_text"),
            fg_color=self.card_color,
            button_color=UI_COLORS["button_secondary"],
            button_hover_color=UI_COLORS["button_secondary_hover"],
            dropdown_fg_color=self.card_color,
            dropdown_hover_color=UI_COLORS["hover"],
            dropdown_text_color=self.text_primary,
            command=self.on_context_change,
        )
        self.context_dropdown.pack(fill="x", padx=4, pady=(0, 8))
        self.context_dropdown.set(f"{self.active_context_size}K")

        # Language Dropdown
        self.lang_label = ctk.CTkLabel(
            self.settings_frame,
            text="Idioma / Language",
            font=self._font("sidebar_text_small", weight="bold"),
            text_color=self.text_muted,
        )
        self.lang_label.pack(anchor="w", padx=4, pady=(4, 2))

        self.lang_dropdown = ctk.CTkOptionMenu(
            self.settings_frame,
            values=["Español", "English"],
            font=self._font("sidebar_text"),
            dropdown_font=self._font("sidebar_text"),
            fg_color=self.card_color,
            button_color=UI_COLORS["button_secondary"],
            button_hover_color=UI_COLORS["button_secondary_hover"],
            dropdown_fg_color=self.card_color,
            dropdown_hover_color=UI_COLORS["hover"],
            dropdown_text_color=self.text_primary,
            command=self.on_lang_change,
        )
        self.lang_dropdown.pack(fill="x", padx=4, pady=(0, 8))
        self.lang_dropdown.set("Español" if self.active_language == "es" else "English")

        # Copy specs button
        self.copy_specs_btn = ctk.CTkButton(
            self.settings_frame,
            text="📋 Copiar Especificaciones" if self.active_language == "es" else "📋 Copy Specifications",
            font=self._font("sidebar_text_small", weight="bold"),
            fg_color=UI_COLORS["button_dark"],
            hover_color=UI_COLORS["button_dark_hover"],
            text_color=self.text_primary,
            height=28,
            command=self.copy_specs_report,
        )
        self.copy_specs_btn.pack(fill="x", padx=4, pady=(8, 4))

        self.scan_status_label = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=self._font("sidebar_text_small", slant="italic"),
            text_color=UI_COLORS["success"],
        )
        self.scan_status_label.pack(padx=sidebar_edge_padding, pady=(8, 2), fill="x")

        self.sidebar_buttons = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_buttons.pack(fill="x", padx=sidebar_edge_padding, pady=(12, 16))

        self.db_status_card = ctk.CTkFrame(
            self.sidebar_buttons,
            fg_color=self.card_color,
            border_color=self.border_color,
            border_width=1,
            corner_radius=8,
            height=UI_LAYOUT["status_card_height"],
        )
        self.db_status_card.pack(fill="x", pady=(0, 12))

        self.db_status_dot = ctk.CTkLabel(
            self.db_status_card,
            text="●",
            font=self._font("status_dot", weight="bold"),
            text_color=UI_COLORS["warning"],
        )
        self.db_status_dot.pack(side="left", padx=(12, 5))

        self.db_status_label = ctk.CTkLabel(
            self.db_status_card,
            text=UI_TEXT["database_searching"],
            font=self._font("sidebar_text_small", weight="bold"),
            text_color=self.text_primary,
        )
        self.db_status_label.pack(side="left", padx=5)

        self.ollama_status_card = ctk.CTkFrame(
            self.sidebar_buttons,
            fg_color=self.card_color,
            border_color=self.border_color,
            border_width=1,
            corner_radius=8,
            height=UI_LAYOUT["status_card_height"],
        )
        self.ollama_status_card.pack(fill="x", pady=(0, 12))

        self.ollama_status_dot = ctk.CTkLabel(
            self.ollama_status_card,
            text="●",
            font=self._font("status_dot", weight="bold"),
            text_color=UI_COLORS["danger"],
        )
        self.ollama_status_dot.pack(side="left", padx=(12, 5))

        self.ollama_status_label = ctk.CTkLabel(
            self.ollama_status_card,
            text="Ollama API: Inactivo" if self.active_language == "es" else "Ollama API: Offline",
            font=self._font("sidebar_text_small", weight="bold"),
            text_color=self.text_primary,
        )
        self.ollama_status_label.pack(side="left", padx=5)

        self.rescan_btn = ctk.CTkButton(
            self.sidebar_buttons,
            text=UI_TEXT["analyze"],
            font=self._font("button", weight="bold"),
            height=UI_LAYOUT["primary_button_height"],
            corner_radius=8,
            fg_color=UI_COLORS["button_secondary"],
            hover_color=UI_COLORS["button_secondary_hover"],
            text_color=self.text_primary,
            command=lambda: self.start_scan_thread(force_refresh=True),
        )
        self.rescan_btn.pack(fill="x", pady=0)

    def create_spec_card(self, parent, title, value, icon):
        card_padding = UI_LAYOUT["card_padding"]
        card = ctk.CTkFrame(parent, fg_color=self.card_color, border_color=self.border_color, border_width=1, corner_radius=10)
        card.grid_columnconfigure(0, weight=1)

        cat_label = ctk.CTkLabel(
            card,
            text=f"{icon}  {title}",
            font=self._font("spec_label", weight="bold"),
            text_color=self.text_muted,
        )
        cat_label.grid(row=0, column=0, sticky="w", padx=card_padding, pady=(8, 2))

        val_label = ctk.CTkLabel(
            card,
            text=value,
            font=self._font("spec_value", weight="bold"),
            text_color=self.text_primary,
            wraplength=self._dynamic_wraplength(0.18, 210, 300),
            justify="left",
            anchor="w",
        )
        val_label.grid(row=1, column=0, sticky="w", padx=card_padding, pady=(2, 4))

        sub_label = ctk.CTkLabel(
            card,
            text="",
            font=self._font("spec_sub"),
            text_color=UI_COLORS["text_subtle"],
            justify="left",
            anchor="w",
        )
        sub_label.grid(row=2, column=0, sticky="w", padx=card_padding, pady=(0, 8))

        card.cat_label = cat_label
        card.val_label = val_label
        card.sub_label = sub_label
        card.bind("<Enter>", lambda e: card.configure(border_color=self.hover_color))
        card.bind("<Leave>", lambda e: card.configure(border_color=self.border_color))
        val_label.bind("<Enter>", lambda e: card.configure(border_color=self.hover_color))
        val_label.bind("<Leave>", lambda e: card.configure(border_color=self.border_color))
        self._bind_label_to_container_width(card, [val_label, sub_label], horizontal_padding=(card_padding * 2) + 24, minimum=120)
        return card

    def build_main_header(self):
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.ui_tokens["section_gap"]))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.main_title = ctk.CTkLabel(
            self.header_frame,
            text=UI_TEXT["main_title"],
            font=self._font("main_title", weight="bold"),
            text_color=self.text_primary,
        )
        self.main_title.grid(row=0, column=0, sticky="w")

        self.main_desc = ctk.CTkLabel(
            self.header_frame,
            text=UI_TEXT["main_description"],
            font=self._font("main_desc"),
            text_color=self.text_muted,
            justify="left",
            anchor="w",
        )
        self.main_desc.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self._bind_label_to_container_width(self.header_frame, self.main_desc, horizontal_padding=32, minimum=160)

        self.control_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.control_frame.grid(row=2, column=0, sticky="ew", pady=(self.ui_tokens["section_gap"], self.ui_tokens["section_gap"]))
        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_frame.grid_columnconfigure(1, weight=0)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search_change)
        self.search_entry = ctk.CTkEntry(
            self.control_frame,
            placeholder_text=UI_TEXT["search_placeholder"],
            font=self._font("input"),
            height=UI_LAYOUT["input_height"],
            corner_radius=8,
            fg_color=self.card_color,
            border_color=self.border_color,
            text_color=self.text_primary,
            placeholder_text_color=UI_COLORS["text_subtle"],
            textvariable=self.search_var,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.category_selector = ctk.CTkSegmentedButton(
            self.control_frame,
            values=UI_BASE["search_categories"],
            font=self._font("segment", weight="bold"),
            height=UI_LAYOUT["segment_height"],
            corner_radius=8,
            command=self.on_category_select,
        )
        self.category_selector.grid(row=0, column=1, sticky="e")
        self.category_selector.set(UI_BASE["search_categories"][0])

    def build_model_list_section(self):
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color="transparent",
            label_text="",
            corner_radius=0,
            scrollbar_fg_color="transparent",
            scrollbar_button_color="#1E293B",
            scrollbar_button_hover_color="#3B82F6",
        )
        self.scroll_frame.grid(row=3, column=0, sticky="nsew", pady=(0, self.ui_tokens["section_gap_tight"]))
        self.scroll_frame._scrollbar.configure(width=8, corner_radius=4)
        self._bind_mousewheel_to_frame(self.scroll_frame)

        self.guide_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=UI_COLORS["guide_background"],
            border_color=UI_COLORS["guide_border"],
            border_width=1,
            corner_radius=10,
        )
        self.guide_frame.grid(row=4, column=0, sticky="ew", pady=(self.ui_tokens["section_gap"], 0))
        self.guide_frame.grid_columnconfigure(0, weight=1)
        self.guide_frame.grid_columnconfigure(1, weight=0)

        self.guide_title = ctk.CTkLabel(
            self.guide_frame,
            text=UI_TEXT["guide_title"],
            font=self._font("guide", weight="bold"),
            text_color=self.text_primary,
        )
        self.guide_title.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.guide_toggle_btn = ctk.CTkButton(
            self.guide_frame,
            text=UI_TEXT["guide_hide"],
            font=self._font("action"),
            fg_color=UI_COLORS["button_secondary"],
            hover_color=UI_COLORS["button_secondary_hover"],
            text_color=UI_COLORS["white"],
            height=UI_LAYOUT["guide_header_height"],
            width=UI_LAYOUT["guide_toggle_width"],
            command=self.toggle_guide_visibility,
        )
        self.guide_toggle_btn.grid(row=0, column=1, sticky="e", padx=(8, 12), pady=(8, 4))

        self.guide_label = ctk.CTkLabel(
            self.guide_frame,
            text=UI_TEXT["guide_text"],
            font=self._font("guide"),
            text_color=UI_COLORS["guide_text"],
            wraplength=self._dynamic_wraplength(0.42, 220, 620),
            justify="left",
            anchor="w",
        )
        self.guide_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        self._bind_wrapped_text(self.guide_frame, self.guide_label, self._font("guide"), horizontal_padding=48, minimum=160)
        self._update_guide_visibility()

    def update_scan_results(self, from_cache=False):
        if self.is_closing or not self.winfo_exists():
            return
        self.hide_loading_modal()
        self.rescan_btn.configure(state="normal", text=UI_TEXT["analyze"])
        self.scan_status_label.configure(text=UI_TEXT["scan_status_success"], text_color=UI_COLORS["success"])

        if from_cache:
            self.db_status_dot.configure(text_color=UI_COLORS["success"])
            self.db_status_label.configure(text=UI_TEXT["database_cached"])
        elif self.online_mode:
            self.db_status_dot.configure(text_color=UI_COLORS["success"])
            self.db_status_label.configure(text=UI_TEXT["database_online"])
        else:
            self.db_status_dot.configure(text_color=UI_COLORS["warning"])
            self.db_status_label.configure(text=UI_TEXT["database_offline"])

        hw_specs = self.specs.get("hardware", self.specs)
        sw_specs = self.specs.get("software", {})
        for child in self.rec_frame.winfo_children():
            child.destroy()

        self._render_recommendations()
        self._update_hardware_cards(hw_specs)
        self._update_software_cards(sw_specs)
        self.render_models_list()

    def _render_recommendations(self):
        recs = [m for m in self.rated_models if m.get("recommended")]
        if not recs:
            return

        rec_title = ctk.CTkLabel(
            self.rec_frame,
            text=UI_TEXT["recommend_title"],
            font=self._font("recommend_title", weight="bold"),
            text_color=UI_COLORS["recommend_title"],
        )
        rec_title.pack(anchor="w", pady=(0, 6))

        cards_container = ctk.CTkFrame(self.rec_frame, fg_color="transparent")
        cards_container.pack(fill="x")

        for col_idx, r_model in enumerate(recs[:4]):
            cards_container.grid_columnconfigure(col_idx, weight=1, uniform="rec_cards")
            r_status = r_model["status"]
            bg_c = "#1E1B4B" if r_status == "RUNS_GREAT" else "#1E293B" if r_status == "RUNS_WELL" else "#111827"
            bd_c = "#312E81" if r_status == "RUNS_GREAT" else "#334155" if r_status == "RUNS_WELL" else "#1F2937"

            card = ctk.CTkFrame(
                cards_container,
                fg_color=bg_c,
                border_color=bd_c,
                border_width=2 if r_status in ["RUNS_GREAT", "RUNS_WELL"] else 1,
                corner_radius=10,
                height=UI_LAYOUT["recommend_card_height"],
            )
            card.grid(row=0, column=col_idx, padx=4, sticky="nsew")
            card.grid_propagate(False)

            r_cat = ctk.CTkLabel(
                card,
                text=r_model["category"].upper(),
                font=self._font("recommend_cat", weight="bold"),
                text_color=UI_COLORS["recommend_great_text"] if r_status == "RUNS_GREAT" else UI_COLORS["recommend_normal_text"],
            )
            r_cat.pack(anchor="w", padx=10, pady=(6, 0))

            r_name = ctk.CTkLabel(
                card,
                text=r_model["name"],
                font=self._font("recommend_name", weight="bold"),
                text_color=self.text_primary,
                wraplength=self._dynamic_wraplength(0.1, 110, 160),
                justify="left",
            )
            r_name.pack(anchor="w", padx=10, pady=(0, 2))

            r_badge = ctk.CTkLabel(
                card,
                text=r_model["status_label"].upper(),
                font=self._font("recommend_badge", weight="bold"),
                text_color=self.text_primary,
                fg_color=r_model["color"],
                corner_radius=4,
                height=18,
                width=110,
            )
            r_badge.pack(anchor="w", padx=10, pady=(2, 6))

    def _update_hardware_cards(self, hw_specs):
        os_pretty = hw_specs.get("os_pretty", f"{hw_specs.get('os')} {hw_specs.get('os_release')}")
        self.os_card.val_label.configure(text=os_pretty)
        self.os_card.sub_label.configure(text=f"{UI_TEXT['cpu_architecture_label']}: {hw_specs.get('arch')}")

        cpu_display = hw_specs.get("cpu_name")
        self.cpu_card.val_label.configure(text=cpu_display)
        avx2_label = UI_TEXT["avx2_yes"] if hw_specs.get("has_avx2") else UI_TEXT["avx2_no"]
        self.cpu_card.sub_label.configure(
            text=f"{UI_TEXT['cpu_cores_label']}: {hw_specs.get('cores')} {UI_TEXT['cpu_physical_label']}, {hw_specs.get('threads')} {UI_TEXT['cpu_threads_label']} | {UI_TEXT['cpu_avx2_label']}: {avx2_label}"
        )

        ram_val = hw_specs.get("ram", 0.0)
        ram_installed = hw_specs.get("ram_installed", ram_val)
        ram_desc = UI_TEXT["ram_unified"] if hw_specs.get("is_apple_silicon") else UI_TEXT["ram_system"]
        if ram_installed > ram_val and not hw_specs.get("is_apple_silicon"):
            ram_desc = f"Usable ({ram_installed} GB física)"
        self.ram_card.val_label.configure(text=f"{ram_val} GB RAM")
        self.ram_card.sub_label.configure(text=ram_desc)

        gpus = hw_specs.get("gpus", [])
        if not gpus:
            self.gpu_card.val_label.configure(text=UI_TEXT["gpu_none"])
            self.gpu_card.sub_label.configure(text=UI_TEXT["gpu_none_help"])
            return

        primary_gpu = gpus[0]
        gpu_name = primary_gpu.get("name")
        if primary_gpu.get("unified"):
            memory_pool_gb = primary_gpu.get("memory_pool_gb") or ram_val
            vram_info = f"{UI_TEXT['memory_pool_label']}: {memory_pool_gb} GB"
            if primary_gpu.get("vram", 0) > 0:
                vram_info += f" | {UI_TEXT['memory_reported_label']}: {primary_gpu.get('vram')} GB"
        else:
            vram_info = f"{primary_gpu.get('vram')} GB {UI_TEXT['vram_dedicated_label']}"
        self.gpu_card.val_label.configure(text=gpu_name)
        self.gpu_card.sub_label.configure(text=vram_info)

    def _update_software_cards(self, sw_specs):
        py_info = sw_specs.get("python", {})
        py_ver = py_info.get("version", UI_TEXT["python_not_detected"])
        py_env = py_info.get("env_type", UI_TEXT["python_env_default"])
        py_arch = py_info.get("arch", "")
        self.python_card.val_label.configure(text=f"Python {py_ver} ({py_arch})")
        self.python_card.sub_label.configure(text=f"Entorno: {py_env}")

        cuda_info = sw_specs.get("cuda", {})
        if cuda_info.get("available"):
            driver_ver = cuda_info.get("driver_version") or UI_TEXT["python_not_detected"]
            cuda_sup = cuda_info.get("cuda_version_supported") or UI_TEXT["python_not_detected"]
            nvcc_ver = cuda_info.get("nvcc_toolkit_version")
            nvcc_str = f", NVCC: {nvcc_ver}" if nvcc_ver else UI_TEXT["nvcc_missing"]
            self.cuda_card.val_label.configure(text=f"{UI_TEXT['cuda_supported_label']}: {cuda_sup}")
            self.cuda_card.sub_label.configure(text=f"{UI_TEXT['driver_label']}: {driver_ver}{nvcc_str}")
        else:
            self.cuda_card.val_label.configure(text=UI_TEXT["cuda_not_detected"])
            self.cuda_card.sub_label.configure(text=UI_TEXT["cuda_missing_support"])

        rocm_info = sw_specs.get("rocm", {})
        if rocm_info.get("available"):
            rocm_ver = rocm_info.get("version") or UI_TEXT["version_label"]
            self.rocm_card.val_label.configure(text=UI_TEXT["rocm_detected"])
            self.rocm_card.sub_label.configure(text=f"{UI_TEXT['version_label']}: {rocm_ver}")
        else:
            self.rocm_card.val_label.configure(text=UI_TEXT["rocm_not_detected"])
            self.rocm_card.sub_label.configure(text=UI_TEXT["rocm_missing_support"])

        comp_info = sw_specs.get("compilers", {})
        avail_compilers = [k for k, value in comp_info.items() if value]
        if avail_compilers:
            self.compilers_card.val_label.configure(text=", ".join([c.upper() for c in avail_compilers]))
            self.compilers_card.sub_label.configure(text=UI_TEXT["compilers_ready"])
        else:
            self.compilers_card.val_label.configure(text=UI_TEXT["compilers_missing"])
            self.compilers_card.sub_label.configure(text=UI_TEXT["compilers_missing_help"])

    def on_category_select(self, category):
        self.active_category = category
        self.render_models_list()

    def on_search_change(self, *args):
        self.search_query = self.search_entry.get().strip().lower()
        self.render_models_list()

    def render_models_list(self):
        if self.is_closing or not self.winfo_exists():
            return
        if self.render_job is not None:
            self.after_cancel(self.render_job)
            self.render_job = None
        self.pending_models = []
        self.model_row_widgets = []

        for child in self.scroll_frame.winfo_children():
            child.destroy()

        filtered_models = []
        for model in self.rated_models:
            if self.active_category == config.MODEL_TEXT["llm_category"] and model["category"] != config.MODEL_TEXT["llm_category"]:
                continue
            if self.active_category == config.MODEL_TEXT["image_category"] and model["category"] != config.MODEL_TEXT["image_category"]:
                continue
            if self.search_query:
                name_match = self.search_query in model["name"].lower()
                desc_match = self.search_query in model["description"].lower()
                prov_match = self.search_query in model["provider"].lower()
                if not (name_match or desc_match or prov_match):
                    continue
            filtered_models.append(model)

        if not filtered_models:
            no_results = ctk.CTkLabel(
                self.scroll_frame,
                text=UI_TEXT["empty_models"],
                font=self._font("empty_state", slant="italic"),
                text_color=self.text_muted,
            )
            no_results.pack(pady=40)
            return

        self.pending_models = list(filtered_models)
        self.model_row_widgets = []
        self._schedule_model_render()

    def _schedule_model_render(self):
        if self.is_closing or not self.winfo_exists():
            return
        if self.render_job is not None:
            self.after_cancel(self.render_job)
        self.render_job = self.after(1, self._render_model_batch)

    def _render_model_batch(self):
        if self.is_closing or not self.winfo_exists():
            return
        self.render_job = None
        batch_size = UI_BASE["render_batch_size"]
        current_batch = self.pending_models[:batch_size]
        self.pending_models = self.pending_models[batch_size:]

        for model in current_batch:
            if self.is_closing or not self.winfo_exists():
                return
            try:
                row = self.create_model_row(self.scroll_frame, model)
                self.model_row_widgets.append(row)
            except tk.TclError:
                return

        if self.pending_models:
            self.render_job = self.after(1, self._render_model_batch)

    def create_model_row(self, parent, model):
        is_rec = model.get("recommended", False)
        border_c = UI_COLORS["hover"] if is_rec else self.border_color
        border_w = 2 if is_rec else 1

        row = ctk.CTkFrame(parent, fg_color=self.card_color, border_color=border_c, border_width=border_w, corner_radius=10)
        row.pack(fill="x", pady=4, ipady=2)
        row.grid_columnconfigure(0, weight=1, minsize=0)
        row.grid_columnconfigure(1, weight=0, minsize=0)

        def on_enter(_):
            row.configure(border_color=self.hover_color)

        def on_leave(_):
            row.configure(border_color=border_c)

        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 4))
        info_frame.grid_columnconfigure(0, weight=1, minsize=0)
        info_frame.grid_columnconfigure(1, weight=0, minsize=0)

        if is_rec:
            rec_badge = ctk.CTkLabel(
                info_frame,
                text=UI_TEXT["recommended_badge"],
                font=self._font("rec_badge", weight="bold"),
                text_color=UI_COLORS["recommend_title"],
            )
            rec_badge.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))

        name_row = 1 if is_rec else 0
        m_name = ctk.CTkLabel(info_frame, text=model["name"], font=self._font("model_name", weight="bold"), text_color=self.text_primary, anchor="w")
        m_name.grid(row=name_row, column=0, sticky="ew", padx=(0, 12))
        m_name.bind("<Enter>", on_enter)
        m_name.bind("<Leave>", on_leave)

        badge_font = self._font("status_badge", weight="bold")
        badge = ctk.CTkLabel(
            info_frame,
            text=model["status_label"].upper(),
            font=badge_font,
            text_color=self.text_primary,
            fg_color=model["color"],
            corner_radius=6,
            width=UI_LAYOUT["status_badge_width"],
            height=28,
        )
        badge.grid(row=name_row, column=1, sticky="e")
        badge.bind("<Enter>", on_enter)
        badge.bind("<Leave>", on_leave)

        meta_str = f"{model['category']} • {model['params']} • {model['context']}"
        m_meta = ctk.CTkLabel(
            info_frame,
            text=meta_str,
            font=self._font("model_meta"),
            text_color=self.text_muted,
            justify="left",
            anchor="w",
        )
        m_meta.grid(row=name_row + 1, column=0, columnspan=2, sticky="ew", pady=(2, 4))

        m_desc = self._create_wrapped_message(info_frame, model["description"], self._font("model_desc"), self.text_muted, self.card_color)
        m_desc.grid(row=name_row + 2, column=0, columnspan=2, sticky="ew")
        self._bind_label_to_container_width(info_frame, [m_name, m_meta], horizontal_padding=32, minimum=120)
        self._bind_message_width(info_frame, m_desc, self._font("model_desc"), horizontal_padding=40, minimum=180)

        exp_frame = ctk.CTkFrame(row, fg_color="transparent")
        exp_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))
        exp_frame.grid_columnconfigure(0, weight=1, minsize=0)
        exp_frame.grid_columnconfigure(1, weight=0, minsize=UI_LAYOUT["support_min_width"])

        detail_frame = ctk.CTkFrame(exp_frame, fg_color="transparent")
        detail_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        support_frame = ctk.CTkFrame(exp_frame, fg_color="transparent")
        support_frame.grid(row=0, column=1, sticky="ne")
        support_frame.grid_columnconfigure(0, weight=1)

        disk_space_text = "Disco" if self.active_language == "es" else "Disk"
        req_text = f"{UI_TEXT['requirements_base_label']}: {model['vram_q4']} GB VRAM"
        if model["category"] == config.MODEL_TEXT["llm_category"]:
            req_text += f" | {model['ram_q4']} GB {UI_TEXT['requirements_ram_cpu_label']}"
        req_text += f" | {model['vram_q4']:.1f} GB {disk_space_text}"

        m_details = self._create_wrapped_message(detail_frame, model["details"], self._font("model_details"), self.text_primary, self.card_color)
        m_details.pack(fill="x", anchor="w")
        self._bind_message_width(detail_frame, m_details, self._font("model_details"), horizontal_padding=0, minimum=UI_LAYOUT["detail_min_width"])

        m_req = ctk.CTkLabel(
            support_frame,
            text=req_text,
            font=self._font("model_req", weight="bold"),
            text_color=UI_COLORS["requirements_text"],
            justify="right",
            anchor="e",
        )
        m_req.pack(fill="x", anchor="e", pady=(0, 6))
        m_req.bind("<Enter>", on_enter)
        m_req.bind("<Leave>", on_leave)

        has_tip = model.get("os_tip")
        if has_tip:
            m_tip = ctk.CTkLabel(
                exp_frame,
                text=model["os_tip"],
                font=self._font("model_tip", slant="italic"),
                text_color=UI_COLORS["tip_text"],
                justify="left",
                anchor="w",
            )
            m_tip.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            m_tip.bind("<Enter>", on_enter)
            m_tip.bind("<Leave>", on_leave)
            self._bind_wrapped_text(exp_frame, m_tip, self._font("model_tip", slant="italic"), horizontal_padding=36, minimum=120)

        def _sync_exp_wraplength(event):
            if event.widget is not exp_frame:
                return
            total_width = max(10, event.width)
            stacked_support = total_width < UI_LAYOUT["model_support_stack_breakpoint"]
            if stacked_support:
                exp_frame.grid_columnconfigure(1, weight=0, minsize=0)
                detail_frame.grid(row=0, column=0, sticky="ew", padx=(0, 0))
                support_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
                support_width = max(10, total_width - 36)
                detail_width = max(10, total_width - 36)
            else:
                exp_frame.grid_columnconfigure(1, weight=0, minsize=UI_LAYOUT["support_min_width"])
                detail_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
                support_frame.grid(row=0, column=1, sticky="ne", pady=(0, 0))
                support_width = max(
                    UI_LAYOUT["support_min_width"],
                    min(UI_LAYOUT["support_max_width"], int(total_width * UI_LAYOUT["support_width_ratio"])),
                )
                detail_width = max(UI_LAYOUT["detail_min_width"], total_width - support_width - 44)
            m_details.configure(wraplength=detail_width)
            m_req.configure(wraplength=support_width, justify="left" if stacked_support else "right", anchor="w" if stacked_support else "e")
            if has_tip:
                m_tip.configure(wraplength=max(10, total_width - 36), anchor="w", justify="left")

        exp_frame.bind("<Configure>", _sync_exp_wraplength, add="+")

        self._render_model_actions(support_frame, model, exp_frame)
        return row

    def _render_model_actions(self, support_frame, model, resize_container=None):
        ollama_tag = model.get("ollama_tag")
        download_url = model.get("download_url")
        if not (ollama_tag or download_url):
            return

        actions_frame = ctk.CTkFrame(support_frame, fg_color="transparent")
        actions_frame.pack(fill="x", pady=(2, 0))

        # Check if Ollama model is already installed
        is_installed = False
        if ollama_tag:
            tag_lower = ollama_tag.lower()
            for installed in self.installed_ollama_models:
                inst_lower = installed.lower()
                if tag_lower in inst_lower or inst_lower in tag_lower:
                    is_installed = True
                    break

        if ollama_tag:
            if is_installed:
                btn_run = ctk.CTkButton(
                    actions_frame,
                    text="⚡ Ejecutar" if self.active_language == "es" else "⚡ Run",
                    font=self._font("action", weight="bold"),
                    fg_color=UI_COLORS["button_green"],
                    hover_color=UI_COLORS["button_green_hover"],
                    text_color=UI_COLORS["white"],
                    height=UI_LAYOUT["action_button_height"],
                    width=UI_LAYOUT["action_run_width"],
                    command=lambda val=ollama_tag: self.run_in_ollama(val),
                )
                btn_run.pack(side="left", padx=(0, 6))

                lbl_installed = ctk.CTkLabel(
                    actions_frame,
                    text="✓ Instalado" if self.active_language == "es" else "✓ Installed",
                    font=self._font("model_tip", weight="bold"),
                    text_color=UI_COLORS["success"],
                )
                lbl_installed.pack(side="left", padx=(6, 0))
                buttons = [btn_run]
            else:
                # Create hidden progress controls inside support_frame
                progress_bar = ctk.CTkProgressBar(support_frame, progress_color=UI_COLORS["hover"])
                progress_bar.pack(fill="x", pady=(6, 0))
                progress_bar.pack_forget()

                status_lbl = ctk.CTkLabel(
                    support_frame,
                    text="",
                    font=self._font("sidebar_text_small", slant="italic"),
                    text_color=self.text_primary,
                )
                status_lbl.pack(anchor="w", pady=(2, 0))
                status_lbl.pack_forget()

                btn_download = ctk.CTkButton(
                    actions_frame,
                    text="📥 Descargar" if self.active_language == "es" else "📥 Download",
                    font=self._font("action", weight="bold"),
                    fg_color=UI_COLORS["button_blue"],
                    hover_color=UI_COLORS["button_blue_hover"],
                    text_color=UI_COLORS["white"],
                    height=UI_LAYOUT["action_button_height"],
                    width=UI_LAYOUT["action_run_width"],
                    command=lambda: self.start_ollama_download(ollama_tag, progress_bar, status_lbl, btn_download),
                )
                btn_download.pack(side="left", padx=(0, 6))

                btn_copy = ctk.CTkButton(
                    actions_frame,
                    text="📋 Copiar" if self.active_language == "es" else "📋 Copy",
                    font=self._font("action"),
                    fg_color=UI_COLORS["button_dark"],
                    hover_color=UI_COLORS["button_dark_hover"],
                    text_color=UI_COLORS["white"],
                    height=UI_LAYOUT["action_button_height"],
                    width=UI_LAYOUT["action_copy_width"],
                    command=lambda val=ollama_tag: self.copy_to_clipboard(UI_ACTIONS["ollama_command_template"].format(tag=val)),
                )
                btn_copy.pack(side="left")
                buttons = [btn_download, btn_copy]
        else:
            btn_download = ctk.CTkButton(
                actions_frame,
                text="🌐 HuggingFace",
                font=self._font("action", weight="bold"),
                fg_color=UI_COLORS["button_blue"],
                hover_color=UI_COLORS["button_blue_hover"],
                text_color=UI_COLORS["white"],
                height=UI_LAYOUT["action_button_height"],
                width=UI_LAYOUT["action_download_width"],
                command=lambda val=download_url: self.open_download_url(val),
            )
            btn_download.pack(side="left", padx=(0, 6))

            btn_guide = ctk.CTkButton(
                actions_frame,
                text="💡 Guía SD/Flux" if self.active_language == "es" else "💡 SD/Flux Guide",
                font=self._font("action"),
                fg_color=UI_COLORS["button_dark"],
                hover_color=UI_COLORS["button_dark_hover"],
                text_color=UI_COLORS["white"],
                height=UI_LAYOUT["action_button_height"],
                width=UI_LAYOUT["action_guide_width"],
                command=lambda name=model["name"]: self.show_image_model_guide(name),
            )
            btn_guide.pack(side="left")
            buttons = [btn_download, btn_guide]

        if resize_container is None:
            return

        def _sync_action_layout(event):
            if event.widget is not resize_container:
                return
            stack_actions = support_frame.winfo_width() < UI_LAYOUT["action_stack_breakpoint"]
            for index, button in enumerate(buttons):
                button.pack_forget()
                if stack_actions:
                    button.pack(fill="x", pady=(0, 6 if index < len(buttons) - 1 else 0))
                else:
                    button.pack(side="left", padx=(0, 6 if index < len(buttons) - 1 else 0))

        resize_container.bind("<Configure>", _sync_action_layout, add="+")

    def on_quant_change(self, value):
        self.active_quantization = value
        self._trigger_recalc()

    def on_context_change(self, value):
        self.active_context_size = int(value.replace("K", ""))
        self._trigger_recalc()

    def on_lang_change(self, value):
        new_lang = "es" if value == "Español" else "en"
        if new_lang != self.active_language:
            self.active_language = new_lang
            self.change_language(new_lang)
            self.refresh_ui_texts()
            self._trigger_recalc()

    def _trigger_recalc(self):
        from src.models import evaluate_compatibility
        if self.specs is not None:
            rated_models, self.online_mode = evaluate_compatibility(
                self.specs,
                quantization=self.active_quantization,
                context_size=self.active_context_size,
            )
            self.rated_models = self._normalize_rated_models(rated_models)
            self.update_scan_results()

    def copy_specs_report(self):
        if self.specs is None:
            return
        import platform
        hw = self.specs.get("hardware", {})
        sw = self.specs.get("software", {})
        
        report = []
        report.append("# AI Compatibility Checker Report 🖥️")
        report.append(f"**Generated**: {platform.node()} ({platform.system()} {platform.release()})")
        report.append("\n## Hardware Specs")
        report.append(f"- **OS**: {hw.get('os_pretty', hw.get('os'))}")
        report.append(f"- **CPU**: {hw.get('cpu_name')} ({hw.get('cores')} Cores, {hw.get('threads')} Threads)")
        report.append(f"- **AVX2 Support**: {'Yes' if hw.get('has_avx2') else 'No'}")
        report.append(f"- **RAM**: {hw.get('ram')} GB")
        
        report.append("\n## GPUs")
        for idx, gpu in enumerate(hw.get("gpus", [])):
            vram_type = "Unified" if gpu.get("unified") else "Dedicated"
            report.append(f"{idx+1}. **{gpu.get('name')}**")
            report.append(f"   - VRAM: {gpu.get('vram')} GB ({vram_type})")
            if gpu.get("driver_version"):
                report.append(f"   - Driver: {gpu.get('driver_version')}")
                
        report.append("\n## Software Runtimes")
        py = sw.get("python", {})
        report.append(f"- **Python**: {py.get('version')} ({py.get('env_type', 'system')})")
        cuda = sw.get("cuda", {})
        if cuda.get("available"):
            report.append(f"- **CUDA**: Supported (Driver: {cuda.get('driver_version')})")
        rocm = sw.get("rocm", {})
        if rocm.get("available"):
            report.append(f"- **ROCm**: Supported (Version: {rocm.get('version')})")
            
        report_text = "\n".join(report)
        self.copy_to_clipboard(report_text)

    def refresh_ui_texts(self):
        self.side_title.configure(text=config.UI_TEXT["sidebar_title"])
        self.side_subtitle.configure(text=config.UI_TEXT["sidebar_subtitle"])
        self.soft_title.configure(text=config.UI_TEXT["software_title"])
        self.soft_subtitle.configure(text=config.UI_TEXT["software_subtitle"])
        self.main_title.configure(text=config.UI_TEXT["main_title"])
        self.main_desc.configure(text=config.UI_TEXT["main_description"])
        self.search_entry.configure(placeholder_text=config.UI_TEXT["search_placeholder"])
        self.guide_title.configure(text=config.UI_TEXT["guide_title"])
        self.guide_label.configure(text=config.UI_TEXT["guide_text"])
        self.rescan_btn.configure(text=config.UI_TEXT["analyze"] if self.specs is None else config.UI_TEXT["rescan"])
        
        # Update settings labels
        if hasattr(self, "settings_title"):
            self.settings_title.configure(text="SIMULACIÓN LOCAL ⚙" if self.active_language == "es" else "LOCAL SIMULATION ⚙")
            self.quant_label.configure(text="Cuantización" if self.active_language == "es" else "Quantization")
            self.context_label.configure(text="Contexto (KV Cache)" if self.active_language == "es" else "Context (KV Cache)")
            self.copy_specs_btn.configure(text="📋 Copiar Especificaciones" if self.active_language == "es" else "📋 Copy Specifications")
            
        # Update spec card titles in place
        for key in ("os", "cpu", "ram", "gpu", "python", "cuda", "rocm", "compilers"):
            card = getattr(self, f"{key}_card", None)
            if card and hasattr(card, "cat_label"):
                title = config.UI_SPEC_CARDS[key]["title"]
                icon = config.UI_SPEC_CARDS[key]["icon"]
                card.cat_label.configure(text=f"{icon}  {title}")
                
        # Re-populate segment button values
        self.category_selector.configure(values=config.UI_BASE["search_categories"])
