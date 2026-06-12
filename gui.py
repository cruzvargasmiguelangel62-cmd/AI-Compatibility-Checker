# -*- coding: utf-8 -*-
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Import our custom modules
from detector import detect_system
from models import evaluate_compatibility

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Config
        self.title("AI Local Hardware Detector & Compatibility Engine")
        self.geometry("1150x660")
        self.minsize(1000, 580)
        
        # Appearance from config
        import config
        ctk.set_appearance_mode(config.APP_THEME)
        ctk.set_default_color_theme(config.APP_COLOR_THEME)
        
        # Color Palette
        self.bg_color = "#0B0F19"       # Deep dark space cadet blue
        self.card_color = "#111827"     # Dark card background
        self.border_color = "#1F2937"   # Subtle card border
        self.hover_color = "#3B82F6"    # Vibrant blue accent
        self.text_primary = "#F9FAFB"   # White
        self.text_muted = "#9CA3AF"     # Gray

        self.configure(fg_color=self.bg_color)
        
        # System Specs State
        self.specs = None
        self.rated_models = []
        self.active_category = "Todos"
        self.search_query = ""
        self.online_mode = False

        # Build GUI
        self.create_layout()
        
        # Initial scan in background
        self.start_scan_thread()

    def create_layout(self):
        # Configure Grid Layout
        self.grid_columnconfigure(0, weight=0, minsize=320)  # Sidebar specs
        self.grid_columnconfigure(1, weight=1)              # Models browser
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar Frame (Specs)
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#0D111C", border_color="#1E293B", border_width=1)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_propagate(False)
        self.build_sidebar()
        
        # Main Frame (Models)
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=self.bg_color)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1) # The scrollable models list
        
        self.build_main_header()
        self.build_model_list_section()

    def build_sidebar(self):
        # Sidebar Header
        self.side_title = ctk.CTkLabel(
            self.sidebar, 
            text="MI HARDWARE 🖥️", 
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=self.text_primary
        )
        self.side_title.pack(padx=20, pady=(15, 2), anchor="w")
        
        self.side_subtitle = ctk.CTkLabel(
            self.sidebar, 
            text="Recursos detectados en tu máquina:", 
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.text_muted
        )
        self.side_subtitle.pack(padx=20, pady=(0, 10), anchor="w")

        # Container for Specs Cards
        self.cards_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.cards_frame.pack(fill="both", expand=True, padx=15, pady=0)

        # 1. OS Card
        self.os_card = self.create_spec_card(self.cards_frame, "SISTEMA OPERATIVO", "Detectando...", "💻")
        self.os_card.pack(fill="x", pady=4)
        
        # 2. CPU Card
        self.cpu_card = self.create_spec_card(self.cards_frame, "PROCESADOR (CPU)", "Detectando...", "🧠")
        self.cpu_card.pack(fill="x", pady=4)
        
        # 3. RAM Card
        self.ram_card = self.create_spec_card(self.cards_frame, "MEMORIA RAM", "Detectando...", "💾")
        self.ram_card.pack(fill="x", pady=4)
        
        # 4. GPU Card
        self.gpu_card = self.create_spec_card(self.cards_frame, "GRÁFICOS (GPU)", "Detectando...", "⚡")
        self.gpu_card.pack(fill="x", pady=4)

        # Scanning/Loading status in sidebar
        self.scan_status_label = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"),
            text_color="#10B981"
        )
        self.scan_status_label.pack(padx=20, pady=(5, 2), fill="x")

        # Action Buttons Frame
        self.sidebar_buttons = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_buttons.pack(fill="x", side="bottom", padx=20, pady=20)
        
        # Database Mode Label
        self.mode_label = ctk.CTkLabel(
            self.sidebar_buttons,
            text="BASE DE DATOS DE MODELOS",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.text_muted
        )
        self.mode_label.pack(anchor="w", padx=2, pady=(0, 4))
        
        # Database Mode Selector
        self.mode_selector = ctk.CTkSegmentedButton(
            self.sidebar_buttons,
            values=["Offline (Local)", "Online (Remoto)"],
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=34,
            corner_radius=6,
            command=self.on_mode_change
        )
        self.mode_selector.pack(fill="x", pady=(0, 15))
        self.mode_selector.set("Offline (Local)")
        
        self.rescan_btn = ctk.CTkButton(
            self.sidebar_buttons, 
            text="🔄 Volver a Escanear", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40,
            corner_radius=8,
            fg_color="#1E293B",
            hover_color="#334155",
            text_color=self.text_primary,
            command=self.start_scan_thread
        )
        self.rescan_btn.pack(fill="x", pady=0)

    def on_mode_change(self, mode):
        self.online_mode = (mode == "Online (Remoto)")
        self.start_scan_thread()

    def create_spec_card(self, parent, category, value, icon):
        card = ctk.CTkFrame(parent, fg_color=self.card_color, border_color=self.border_color, border_width=1, corner_radius=10)
        card.grid_columnconfigure(0, weight=1)
        
        # Category label
        cat_label = ctk.CTkLabel(
            card, 
            text=f"{icon}  {category}", 
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.text_muted
        )
        cat_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))
        
        # Value label
        val_label = ctk.CTkLabel(
            card, 
            text=value, 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.text_primary,
            wraplength=270,
            justify="left"
        )
        val_label.grid(row=1, column=0, sticky="w", padx=12, pady=(2, 6))
        
        # Detail sublabel
        sub_label = ctk.CTkLabel(
            card, 
            text="", 
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#6B7280"
        )
        sub_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))
        
        # Save reference to label elements to update them later
        card.val_label = val_label
        card.sub_label = sub_label
        
        # Hover micro-animation
        card.bind("<Enter>", lambda e: card.configure(border_color=self.hover_color))
        card.bind("<Leave>", lambda e: card.configure(border_color=self.border_color))
        val_label.bind("<Enter>", lambda e: card.configure(border_color=self.hover_color))
        val_label.bind("<Leave>", lambda e: card.configure(border_color=self.border_color))
        
        return card

    def build_main_header(self):
        # Title and Subtitle Row
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.main_title = ctk.CTkLabel(
            self.header_frame,
            text="Can I Run Local AI? 🚀",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=self.text_primary
        )
        self.main_title.grid(row=0, column=0, sticky="w")
        
        self.main_desc = ctk.CTkLabel(
            self.header_frame,
            text="Evaluación automatizada de compatibilidad optimizada por Sistema Operativo.",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=self.text_muted
        )
        self.main_desc.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Filter & Search controls frame
        self.control_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.control_frame.grid(row=1, column=0, sticky="ew", pady=(10, 15))
        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_frame.grid_columnconfigure(1, weight=0)
        
        # Search Box
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search_change)
        self.search_entry = ctk.CTkEntry(
            self.control_frame,
            placeholder_text="🔍 Buscar modelos (ej. DeepSeek, Llama...)",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=40,
            corner_radius=8,
            fg_color=self.card_color,
            border_color=self.border_color,
            text_color=self.text_primary,
            placeholder_text_color="#4B5563",
            textvariable=self.search_var
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # Segmented Category Button
        self.category_selector = ctk.CTkSegmentedButton(
            self.control_frame,
            values=["Todos", "Text (LLM)", "Image Generation"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=40,
            corner_radius=8,
            command=self.on_category_select
        )
        self.category_selector.grid(row=0, column=1, sticky="e")
        self.category_selector.set("Todos")

    def build_model_list_section(self):
        # Models scrollable list
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.main_container, 
            fg_color="transparent", 
            label_text="", 
            corner_radius=0
        )
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        
        # Instructions/Summary banner underneath or in sidebar
        self.guide_frame = ctk.CTkFrame(
            self.main_container, 
            fg_color="#1E1E2F", 
            border_color="#2D2D44", 
            border_width=1, 
            corner_radius=10
        )
        self.guide_frame.grid(row=3, column=0, sticky="ew", pady=(15, 0))
        self.guide_frame.grid_columnconfigure(0, weight=1)
        
        guide_text = (
            "💡 ¿Cómo ejecutar estos modelos? "
            "1. Instala Ollama (para LLMs) o LM Studio. "
            "2. Abre tu terminal y escribe: 'ollama run [nombre-modelo]' (ej: 'ollama run deepseek-r1:8b'). "
            "3. Para generar imágenes, usa Stable Diffusion WebUI, ComfyUI o Draw Things (macOS)."
        )
        
        self.guide_label = ctk.CTkLabel(
            self.guide_frame,
            text=guide_text,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#A5B4FC",
            wraplength=750,
            justify="left"
        )
        self.guide_label.grid(row=0, column=0, sticky="w", padx=15, pady=12)

    def start_scan_thread(self):
        # Update UI to scanning state
        self.rescan_btn.configure(state="disabled", text="⌛ Escaneando...")
        self.scan_status_label.configure(text="Escanenado hardware del sistema...", text_color="#3B82F6")
        
        # Run scan in thread so window doesn't freeze
        t = threading.Thread(target=self.perform_scan)
        t.daemon = True
        t.start()

    def perform_scan(self):
        try:
            self.specs = detect_system()
            self.rated_models = evaluate_compatibility(self.specs, online=self.online_mode)
            self.after(0, self.update_scan_results)
        except Exception as e:
            self.after(0, lambda: self.show_scan_error(e))

    def show_scan_error(self, err):
        self.rescan_btn.configure(state="normal", text="🔄 Volver a Escanear")
        self.scan_status_label.configure(text="Error al escanear", text_color="#EF4444")
        messagebox.showerror("Error", f"Ocurrió un error al detectar los recursos:\n{str(err)}")

    def update_scan_results(self):
        # Enable rescan button
        self.rescan_btn.configure(state="normal", text="🔄 Volver a Escanear")
        self.scan_status_label.configure(text="Hardware detectado correctamente", text_color="#10B981")
        
        # 1. Update OS Info
        os_pretty = self.specs.get("os_pretty", f"{self.specs['os']} {self.specs['os_release']}")
        self.os_card.val_label.configure(text=os_pretty)
        self.os_card.sub_label.configure(text=f"Arquitectura: {self.specs['arch']}")
        
        # 2. Update CPU Info
        cpu_display = self.specs["cpu_name"]
        self.cpu_card.val_label.configure(text=cpu_display)
        self.cpu_card.sub_label.configure(text=f"Núcleos: {self.specs['cores']} físicos, {self.specs['threads']} hilos")
        
        # 3. Update RAM Info
        ram_installed = self.specs.get("ram_installed", self.specs["ram"])
        ram_desc = "Memoria del Sistema"
        if self.specs["is_apple_silicon"]:
            ram_desc = "Memoria Unificada"
        elif ram_installed > self.specs["ram"]:
            ram_desc = f"Usable ({ram_installed} GB física)"
        self.ram_card.val_label.configure(text=f"{self.specs['ram']} GB RAM")
        self.ram_card.sub_label.configure(text=ram_desc)
        
        # 4. Update GPU Info
        gpus = self.specs["gpus"]
        if gpus:
            primary_gpu = gpus[0]
            gpu_name = primary_gpu["name"]
            
            vram_info = f"{primary_gpu['vram']} GB"
            if primary_gpu.get("unified"):
                vram_info += " (Compartido/Unified)"
            else:
                vram_info += " VRAM dedicada"
                
            self.gpu_card.val_label.configure(text=gpu_name)
            self.gpu_card.sub_label.configure(text=vram_info)
        else:
            self.gpu_card.val_label.configure(text="Sin GPU dedicada")
            self.gpu_card.sub_label.configure(text="Usa gráficos integrados / CPU")
            
        # Refresh models display
        self.render_models_list()

    def on_category_select(self, category):
        self.active_category = category
        self.render_models_list()

    def on_search_change(self, *args):
        self.search_query = self.search_entry.get().strip().lower()
        self.render_models_list()

    def render_models_list(self):
        # Clear previous items in scrollable frame
        for child in self.scroll_frame.winfo_children():
            child.destroy()
            
        # Filter models
        filtered_models = []
        for model in self.rated_models:
            # Category filter
            if self.active_category == "Text (LLM)" and model["category"] != "Text (LLM)":
                continue
            if self.active_category == "Image Generation" and model["category"] != "Image Generation":
                continue
                
            # Search query filter
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
                text="No se encontraron modelos que coincidan con la búsqueda.",
                font=ctk.CTkFont(family="Segoe UI", size=14, slant="italic"),
                text_color=self.text_muted
            )
            no_results.pack(pady=40)
            return

        # Render list items
        for model in filtered_models:
            self.create_model_row(self.scroll_frame, model)

    def create_model_row(self, parent, model):
        # Row Frame
        row = ctk.CTkFrame(
            parent,
            fg_color=self.card_color,
            border_color=self.border_color,
            border_width=1,
            corner_radius=10
        )
        row.pack(fill="x", pady=6, ipady=4)
        
        # Grid settings for row contents
        row.grid_columnconfigure(0, weight=4, minsize=300)
        row.grid_columnconfigure(1, weight=0, minsize=170)
        row.grid_columnconfigure(2, weight=5, minsize=300)
        
        def on_enter(e):
            row.configure(border_color=self.hover_color)
        def on_leave(e):
            row.configure(border_color=self.border_color)
            
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

        # ------------------ COL 0: INFO ------------------
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=15, pady=12)
        
        m_name = ctk.CTkLabel(
            info_frame, 
            text=model["name"],
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=self.text_primary,
            anchor="w"
        )
        m_name.pack(anchor="w")
        m_name.bind("<Enter>", on_enter)
        m_name.bind("<Leave>", on_leave)
        
        meta_str = f"{model['category']} • {model['params']} • {model['context']}"
        m_meta = ctk.CTkLabel(
            info_frame,
            text=meta_str,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.text_muted,
            anchor="w"
        )
        m_meta.pack(anchor="w", pady=(2, 4))
        
        m_desc = ctk.CTkLabel(
            info_frame,
            text=model["description"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#9CA3AF",
            wraplength=350,
            justify="left"
        )
        m_desc.pack(anchor="w")

        # ------------------ COL 1: STATUS BADGE ------------------
        badge_frame = ctk.CTkFrame(row, fg_color="transparent")
        badge_frame.grid(row=0, column=1, sticky="c", padx=10, pady=12)
        
        badge_color = model["color"]
        badge = ctk.CTkLabel(
            badge_frame,
            text=model["status_label"].upper(),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.text_primary,
            fg_color=badge_color,
            corner_radius=6,
            width=150,
            height=28
        )
        badge.pack(padx=5, pady=5)
        badge.bind("<Enter>", on_enter)
        badge.bind("<Leave>", on_leave)

        # ------------------ COL 2: EXPLANATION ------------------
        exp_frame = ctk.CTkFrame(row, fg_color="transparent")
        exp_frame.grid(row=0, column=2, sticky="w", padx=15, pady=12)
        
        vram_req = model["vram_q4"]
        ram_req = model["ram_q4"]
        req_text = f"Requisitos base: {vram_req} GB VRAM"
        if model["category"] == "Text (LLM)":
            req_text += f" | {ram_req} GB RAM (CPU)"
            
        m_req = ctk.CTkLabel(
            exp_frame,
            text=req_text,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#818CF8",
            anchor="w"
        )
        m_req.pack(anchor="w", pady=(0, 2))
        m_req.bind("<Enter>", on_enter)
        m_req.bind("<Leave>", on_leave)
        
        m_details = ctk.CTkLabel(
            exp_frame,
            text=model["details"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.text_primary,
            wraplength=380,
            justify="left"
        )
        m_details.pack(anchor="w")
        m_details.bind("<Enter>", on_enter)
        m_details.bind("<Leave>", on_leave)
        
        # Render OS tip if exists
        if model.get("os_tip"):
            m_tip = ctk.CTkLabel(
                exp_frame,
                text=model["os_tip"],
                font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"),
                text_color="#34D399", # Green highlight for tip
                wraplength=380,
                justify="left"
            )
            m_tip.pack(anchor="w", pady=(4, 0))
            m_tip.bind("<Enter>", on_enter)
            m_tip.bind("<Leave>", on_leave)

if __name__ == "__main__":
    app = App()
    app.mainloop()