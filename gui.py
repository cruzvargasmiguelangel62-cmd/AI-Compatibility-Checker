# -*- coding: utf-8 -*-
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Import our custom modules
from src.detector import detect_system
from src.models import evaluate_compatibility

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Config
        self.title("AI Local Hardware Detector & Compatibility Engine")
        self.geometry("1150x660")
        self.minsize(1000, 580)
        
        # Appearance from config
        from src import config
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
        
        # Sidebar Frame (Specs) - Scrollable to fit all screens dynamically
        self.sidebar = ctk.CTkScrollableFrame(
            self, 
            width=280, 
            corner_radius=0, 
            fg_color="#0D111C", 
            border_color="#1E293B",
            border_width=1,
            scrollbar_fg_color="transparent",
            scrollbar_button_color="#1E293B",
            scrollbar_button_hover_color="#3B82F6",
            label_text=""
        )
        self.sidebar._scrollbar.configure(width=8, corner_radius=4)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.build_sidebar()
        
        # Main Frame (Models)
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=self.bg_color)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(3, weight=1) # The scrollable models list (now on row 3)
        
        # Recommendations Frame
        self.rec_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.rec_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
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

        # Software Header
        self.soft_title = ctk.CTkLabel(
            self.sidebar, 
            text="MI SOFTWARE 🛠️", 
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=self.text_primary
        )
        self.soft_title.pack(padx=20, pady=(20, 2), anchor="w")
        
        self.soft_subtitle = ctk.CTkLabel(
            self.sidebar, 
            text="Entornos y drivers de compilación:", 
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=self.text_muted
        )
        self.soft_subtitle.pack(padx=20, pady=(0, 8), anchor="w")

        # Container for Software Cards
        self.soft_cards_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.soft_cards_frame.pack(fill="both", expand=True, padx=15, pady=0)

        # 1. Python Card
        self.python_card = self.create_spec_card(self.soft_cards_frame, "ENTORNO PYTHON", "Detectando...", "🐍")
        self.python_card.pack(fill="x", pady=4)
        
        # 2. CUDA Card
        self.cuda_card = self.create_spec_card(self.soft_cards_frame, "NVIDIA CUDA / DRIVER", "Detectando...", "💚")
        self.cuda_card.pack(fill="x", pady=4)
        
        # 3. ROCm Card
        self.rocm_card = self.create_spec_card(self.soft_cards_frame, "AMD ROCm / HIP", "Detectando...", "❤️")
        self.rocm_card.pack(fill="x", pady=4)
        
        # 4. Compilers Card
        self.compilers_card = self.create_spec_card(self.soft_cards_frame, "COMPILADORES C++", "Detectando...", "🔧")
        self.compilers_card.pack(fill="x", pady=4)

        # Scanning/Loading status in sidebar
        self.scan_status_label = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"),
            text_color="#10B981"
        )
        self.scan_status_label.pack(padx=20, pady=(10, 2), fill="x")

        # Action Buttons Frame
        self.sidebar_buttons = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_buttons.pack(fill="x", padx=20, pady=(15, 20))
        
        # Database Mode Status Card
        self.db_status_card = ctk.CTkFrame(
            self.sidebar_buttons,
            fg_color=self.card_color,
            border_color=self.border_color,
            border_width=1,
            corner_radius=8,
            height=38
        )
        self.db_status_card.pack(fill="x", pady=(0, 15))
        
        self.db_status_dot = ctk.CTkLabel(
            self.db_status_card,
            text="●",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#F97316"
        )
        self.db_status_dot.pack(side="left", padx=(12, 5))
        
        self.db_status_label = ctk.CTkLabel(
            self.db_status_card,
            text="Base de Datos: Buscando...",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.text_primary
        )
        self.db_status_label.pack(side="left", padx=5)
        
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
            wraplength=210,
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

        # Filter & Search controls frame (moved to row 2)
        self.control_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.control_frame.grid(row=2, column=0, sticky="ew", pady=(10, 15))
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
            corner_radius=0,
            scrollbar_fg_color="transparent",
            scrollbar_button_color="#1E293B",
            scrollbar_button_hover_color="#3B82F6"
        )
        # Moved to row 3
        self.scroll_frame.grid(row=3, column=0, sticky="nsew", pady=5)
        self.scroll_frame._scrollbar.configure(width=8, corner_radius=4)
        
        # Instructions/Summary banner underneath or in sidebar (moved to row 4)
        self.guide_frame = ctk.CTkFrame(
            self.main_container, 
            fg_color="#1E1E2F", 
            border_color="#2D2D44", 
            border_width=1, 
            corner_radius=10
        )
        self.guide_frame.grid(row=4, column=0, sticky="ew", pady=(15, 0))
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
        self.scan_status_label.configure(text="Escaneando hardware del sistema...", text_color="#3B82F6")
        self.db_status_dot.configure(text_color="#F97316")
        self.db_status_label.configure(text="Base de Datos: Buscando...")
        
        # Run scan in thread so window doesn't freeze
        t = threading.Thread(target=self.perform_scan)
        t.daemon = True
        t.start()

    def perform_scan(self):
        try:
            self.specs = detect_system()
            self.rated_models, self.online_mode = evaluate_compatibility(self.specs)
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
        self.scan_status_label.configure(text="Sistema analizado correctamente", text_color="#10B981")
        
        # Update DB status indicator
        if self.online_mode:
            self.db_status_dot.configure(text_color="#10B981")
            self.db_status_label.configure(text="Base de Datos: Online (Sincronizada)")
        else:
            self.db_status_dot.configure(text_color="#F59E0B")
            self.db_status_label.configure(text="Base de Datos: Offline (Local)")
            
        # Extract hardware and software from specs dictionary
        hw_specs = self.specs.get("hardware", self.specs)
        sw_specs = self.specs.get("software", {})
        
        # Clear previous recommendations and render new ones
        for child in self.rec_frame.winfo_children():
            child.destroy()
            
        recs = [m for m in self.rated_models if m.get("recommended")]
        if recs:
            rec_title = ctk.CTkLabel(
                self.rec_frame,
                text="🏆 MODELOS TOP RECOMENDADOS PARA TU PC",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="#F59E0B"
            )
            rec_title.pack(anchor="w", pady=(0, 6))
            
            cards_container = ctk.CTkFrame(self.rec_frame, fg_color="transparent")
            cards_container.pack(fill="x")
            
            for col_idx, r_model in enumerate(recs[:4]):
                cards_container.grid_columnconfigure(col_idx, weight=1, uniform="rec_cards")
                
                # Check status color
                r_status = r_model["status"]
                bg_c = "#1E1B4B" if r_status == "RUNS_GREAT" else "#1E293B" if r_status == "RUNS_WELL" else "#111827"
                bd_c = "#312E81" if r_status == "RUNS_GREAT" else "#334155" if r_status == "RUNS_WELL" else "#1F2937"
                
                card = ctk.CTkFrame(
                    cards_container,
                    fg_color=bg_c,
                    border_color=bd_c,
                    border_width=2 if r_status in ["RUNS_GREAT", "RUNS_WELL"] else 1,
                    corner_radius=10,
                    height=95
                )
                card.grid(row=0, column=col_idx, padx=4, sticky="nsew")
                card.grid_propagate(False)
                
                # Category label
                r_cat = ctk.CTkLabel(
                    card,
                    text=r_model["category"].upper(),
                    font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                    text_color="#818CF8" if r_status == "RUNS_GREAT" else "#9CA3AF"
                )
                r_cat.pack(anchor="w", padx=10, pady=(6, 0))
                
                # Model Name
                r_name = ctk.CTkLabel(
                    card,
                    text=r_model["name"],
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color=self.text_primary,
                    wraplength=125,
                    justify="left"
                )
                r_name.pack(anchor="w", padx=10, pady=(0, 2))
                
                # Status Badge
                r_badge = ctk.CTkLabel(
                    card,
                    text=r_model["status_label"].upper(),
                    font=ctk.CTkFont(family="Segoe UI", size=8, weight="bold"),
                    text_color=self.text_primary,
                    fg_color=r_model["color"],
                    corner_radius=4,
                    height=18,
                    width=110
                )
                r_badge.pack(anchor="w", padx=10, pady=(2, 6))
        
        # 1. Update OS Info
        os_pretty = hw_specs.get("os_pretty", f"{hw_specs.get('os')} {hw_specs.get('os_release')}")
        self.os_card.val_label.configure(text=os_pretty)
        self.os_card.sub_label.configure(text=f"Arquitectura: {hw_specs.get('arch')}")
        
        # 2. Update CPU Info
        cpu_display = hw_specs.get("cpu_name")
        self.cpu_card.val_label.configure(text=cpu_display)
        self.cpu_card.sub_label.configure(text=f"Núcleos: {hw_specs.get('cores')} físicos, {hw_specs.get('threads')} hilos")
        
        # 3. Update RAM Info
        ram_val = hw_specs.get("ram", 0.0)
        ram_installed = hw_specs.get("ram_installed", ram_val)
        ram_desc = "Memoria del Sistema"
        if hw_specs.get("is_apple_silicon"):
            ram_desc = "Memoria Unificada"
        elif ram_installed > ram_val:
            ram_desc = f"Usable ({ram_installed} GB física)"
        self.ram_card.val_label.configure(text=f"{ram_val} GB RAM")
        self.ram_card.sub_label.configure(text=ram_desc)
        
        # 4. Update GPU Info
        gpus = hw_specs.get("gpus", [])
        if gpus:
            primary_gpu = gpus[0]
            gpu_name = primary_gpu.get("name")
            
            vram_info = f"{primary_gpu.get('vram')} GB"
            if primary_gpu.get("unified"):
                vram_info += " (Compartido/Unified)"
            else:
                vram_info += " VRAM dedicada"
                
            self.gpu_card.val_label.configure(text=gpu_name)
            self.gpu_card.sub_label.configure(text=vram_info)
        else:
            self.gpu_card.val_label.configure(text="Sin GPU dedicada")
            self.gpu_card.sub_label.configure(text="Usa gráficos integrados / CPU")
            
        # Update Software Cards
        # 1. Python
        py_info = sw_specs.get("python", {})
        py_ver = py_info.get("version", "Desconocida")
        py_env = py_info.get("env_type", "System")
        py_arch = py_info.get("arch", "")
        self.python_card.val_label.configure(text=f"Python {py_ver} ({py_arch})")
        self.python_card.sub_label.configure(text=f"Entorno: {py_env}")

        # 2. CUDA
        cuda_info = sw_specs.get("cuda", {})
        if cuda_info.get("available"):
            driver_ver = cuda_info.get("driver_version") or "Desconocido"
            cuda_sup = cuda_info.get("cuda_version_supported") or "Desconocido"
            nvcc_ver = cuda_info.get("nvcc_toolkit_version")
            nvcc_str = f", NVCC: {nvcc_ver}" if nvcc_ver else " (Sin NVCC)"
            
            self.cuda_card.val_label.configure(text=f"CUDA Soportado: {cuda_sup}")
            self.cuda_card.sub_label.configure(text=f"Driver: {driver_ver}{nvcc_str}")
        else:
            self.cuda_card.val_label.configure(text="No Detectado")
            self.cuda_card.sub_label.configure(text="Sin GPU NVIDIA o Driver CUDA")

        # 3. ROCm
        rocm_info = sw_specs.get("rocm", {})
        if rocm_info.get("available"):
            rocm_ver = rocm_info.get("version") or "Instalado"
            self.rocm_card.val_label.configure(text=f"ROCm/HIP Detectado")
            self.rocm_card.sub_label.configure(text=f"Versión: {rocm_ver}")
        else:
            self.rocm_card.val_label.configure(text="No Detectado")
            self.rocm_card.sub_label.configure(text="Sin soporte AMD ROCm/HIP")

        # 4. Compilers
        comp_info = sw_specs.get("compilers", {})
        avail_compilers = [k for k, v in comp_info.items() if v]
        if avail_compilers:
            comp_list = ", ".join([c.upper() for c in avail_compilers])
            self.compilers_card.val_label.configure(text=comp_list)
            self.compilers_card.sub_label.configure(text="Listos para compilar dependencias")
        else:
            self.compilers_card.val_label.configure(text="Ninguno Detectado")
            self.compilers_card.sub_label.configure(text="Instala MSVC/GCC/Clang para construir de fuentes")
            
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
        is_rec = model.get("recommended", False)
        border_c = "#3B82F6" if is_rec else self.border_color
        border_w = 2 if is_rec else 1
        
        # Row Frame
        row = ctk.CTkFrame(
            parent,
            fg_color=self.card_color,
            border_color=border_c,
            border_width=border_w,
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
            row.configure(border_color=border_c)
            
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

        # ------------------ COL 0: INFO ------------------
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=15, pady=12)
        
        if is_rec:
            rec_badge = ctk.CTkLabel(
                info_frame,
                text="✨ RECOMENDADO PARA TU PC",
                font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                text_color="#F59E0B"
            )
            rec_badge.pack(anchor="w", pady=(0, 2))
        
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
            wraplength=280,
            justify="left"
        )
        m_desc.pack(anchor="w")

        # ------------------ COL 1: STATUS BADGE ------------------
        badge_frame = ctk.CTkFrame(row, fg_color="transparent")
        badge_frame.grid(row=0, column=1, padx=10, pady=12)
        
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
            wraplength=290,
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
                wraplength=290,
                justify="left"
            )
            m_tip.pack(anchor="w", pady=(4, 0))
            m_tip.bind("<Enter>", on_enter)
            m_tip.bind("<Leave>", on_leave)

        # Actions frame (buttons)
        ollama_tag = model.get("ollama_tag")
        download_url = model.get("download_url")
        
        if ollama_tag or download_url:
            actions_frame = ctk.CTkFrame(exp_frame, fg_color="transparent")
            actions_frame.pack(anchor="w", pady=(8, 0))
            
            if ollama_tag:
                btn_run = ctk.CTkButton(
                    actions_frame,
                    text="⚡ Ejecutar (Ollama)",
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    fg_color="#10B981", # Emerald green
                    hover_color="#059669",
                    text_color="#FFFFFF",
                    height=24,
                    width=120,
                    command=lambda val=ollama_tag: self.run_in_ollama(val)
                )
                btn_run.pack(side="left", padx=(0, 6))
                
                btn_copy = ctk.CTkButton(
                    actions_frame,
                    text="📋 Copiar",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    fg_color="#1F2937", # Dark gray
                    hover_color="#374151",
                    text_color="#FFFFFF",
                    height=24,
                    width=70,
                    command=lambda val=ollama_tag: self.copy_to_clipboard(f"ollama run {val}")
                )
                btn_copy.pack(side="left")
            elif download_url:
                btn_download = ctk.CTkButton(
                    actions_frame,
                    text="🌐 HuggingFace",
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    fg_color="#3B82F6", # Blue
                    hover_color="#2563EB",
                    text_color="#FFFFFF",
                    height=24,
                    width=100,
                    command=lambda val=download_url: self.open_download_url(val)
                )
                btn_download.pack(side="left", padx=(0, 6))
                
                btn_guide = ctk.CTkButton(
                    actions_frame,
                    text="💡 Guía SD/Flux",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    fg_color="#1F2937", # Dark gray
                    hover_color="#374151",
                    text_color="#FFFFFF",
                    height=24,
                    width=90,
                    command=lambda name=model["name"]: self.show_image_model_guide(name)
                )
                btn_guide.pack(side="left")

    def run_in_ollama(self, tag):
        import subprocess
        import platform
        import shutil
        sys_os = platform.system()
        
        try:
            # Check if ollama is installed by running `ollama --version`
            subprocess.run(["ollama", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            messagebox.showerror(
                "Ollama No Detectado",
                "Ollama no parece estar instalado o configurado en tu PATH.\n\n"
                "Por favor, instala Ollama desde https://ollama.com antes de intentar ejecutar este modelo."
            )
            return

        # Start model in a new terminal window
        try:
            if sys_os == "Windows":
                # Start a new cmd window running the command
                subprocess.Popen(["cmd", "/c", f"start cmd /k ollama run {tag}"])
            elif sys_os == "Darwin":
                # Open Terminal app and run the command
                subprocess.Popen(["osascript", "-e", f'tell app "Terminal" to do script "ollama run {tag}"'])
            elif sys_os == "Linux":
                # Try common terminal emulators
                terminal_launched = False
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
                    if shutil.which(term):
                        if term == "gnome-terminal":
                            subprocess.Popen([term, "--", "bash", "-c", f"ollama run {tag}; exec bash"])
                        else:
                            subprocess.Popen([term, "-e", f"bash -c 'ollama run {tag}; exec bash'"])
                        terminal_launched = True
                        break
                if not terminal_launched:
                    # Fallback to copy to clipboard
                    self.copy_to_clipboard(f"ollama run {tag}")
                    messagebox.showinfo("Comando Copiado", f"No se encontró un emulador de terminal compatible.\nSe copió el comando al portapapeles:\n\nollama run {tag}")
            else:
                self.copy_to_clipboard(f"ollama run {tag}")
                messagebox.showinfo("Comando Copiado", f"Se copió el comando al portapapeles:\n\nollama run {tag}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la terminal: {e}")

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update() # Keep clipboard contents after app closes
        messagebox.showinfo("Copiado", f"Copiado al portapapeles:\n\n{text}")

    def open_download_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def show_image_model_guide(self, model_name):
        guide = (
            f"Guía para ejecutar {model_name} localmente:\n\n"
            "1. Descarga el archivo del modelo (.safetensors) usando el botón de HuggingFace.\n"
            "2. Instala una interfaz compatible como:\n"
            "   - ComfyUI (Recomendado, muy rápido e intermedio)\n"
            "   - Draw Things (Excelente para macOS con CoreML/Metal)\n"
            "   - Automatic1111 (Estándar de la industria)\n"
            "3. Coloca el archivo descargado en la carpeta de modelos de tu interfaz (por ejemplo, 'models/Stable-diffusion' o 'models/checkpoints').\n"
            "4. Inicia la interfaz y selecciona el modelo para empezar a generar imágenes."
        )
        messagebox.showinfo(f"Guía de Uso - {model_name}", guide)

if __name__ == "__main__":
    app = App()
    app.mainloop()