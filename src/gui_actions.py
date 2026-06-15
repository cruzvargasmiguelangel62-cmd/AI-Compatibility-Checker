import platform
import shutil
import subprocess
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from src import config

UI_COLORS = config.UI_COLORS
UI_TEXT = config.UI_TEXT
UI_ACTIONS = config.UI_ACTIONS


class AppActionsMixin:
    def render_empty_state(self):
        for child in self.rec_frame.winfo_children():
            child.destroy()
        if hasattr(self, "scroll_frame"):
            for child in self.scroll_frame.winfo_children():
                if child != getattr(self, "guide_frame", None):
                    child.destroy()
            title = ctk.CTkLabel(
                self.scroll_frame,
                text=UI_TEXT["empty_state_title"],
                font=self._font("main_desc", weight="bold"),
                text_color=self.text_primary,
            )
            title.pack(pady=(50, 8))
            body = ctk.CTkLabel(
                self.scroll_frame,
                text=UI_TEXT["empty_state_body"],
                font=self._font("model_desc"),
                text_color=self.text_muted,
                wraplength=self._dynamic_wraplength(0.36, 320, 520),
                justify="center",
            )
            body.pack(pady=(0, 12))
            if hasattr(self, "guide_frame"):
                self.guide_frame.pack(fill="x", pady=(12, 4))

    def show_loading_modal(self, title_text=None, body_text=None):
        if self.loading_modal is not None and self.loading_modal.winfo_exists():
            return
            
        t_text = title_text or UI_TEXT["loading_modal_title"]
        b_text = body_text or UI_TEXT["loading_modal_body"]

        modal = ctk.CTkToplevel(self)
        modal.title(t_text)
        modal.geometry("420x180")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=UI_COLORS["background"])
        frame = ctk.CTkFrame(
            modal,
            fg_color=self.card_color,
            border_color=self.border_color,
            border_width=1,
            corner_radius=12,
        )
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        title = ctk.CTkLabel(
            frame,
            text=t_text,
            font=self._font("main_desc", weight="bold"),
            text_color=self.text_primary,
        )
        title.pack(anchor="w", padx=16, pady=(18, 8))
        body = ctk.CTkLabel(
            frame,
            text=b_text,
            font=self._font("model_desc"),
            text_color=self.text_muted,
            justify="left",
            wraplength=340,
        )
        body.pack(anchor="w", padx=16, pady=(0, 12))
        progress = ctk.CTkProgressBar(frame, mode="indeterminate", progress_color=UI_COLORS["hover"])
        progress.pack(fill="x", padx=16, pady=(0, 16))
        progress.start()
        self.loading_modal = modal

    def hide_loading_modal(self):
        if self.loading_modal is None:
            return
        if self.loading_modal.winfo_exists():
            try:
                self.loading_modal.grab_release()
            except Exception:
                pass
            self.loading_modal.destroy()
        self.loading_modal = None

    def show_ollama_install_modal(self):
        if self.loading_modal is not None and self.loading_modal.winfo_exists():
            self.hide_loading_modal()

        modal = ctk.CTkToplevel(self)
        modal.title(UI_TEXT["ollama_missing_title"])
        modal.geometry("500x240")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=UI_COLORS["background"])

        frame = ctk.CTkFrame(
            modal,
            fg_color=self.card_color,
            border_color=self.border_color,
            border_width=1,
            corner_radius=12,
        )
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        title = ctk.CTkLabel(
            frame,
            text=UI_TEXT["ollama_missing_title"],
            font=self._font("main_desc", weight="bold"),
            text_color=self.text_primary,
        )
        title.pack(anchor="w", padx=16, pady=(18, 8))

        body = ctk.CTkLabel(
            frame,
            text=UI_TEXT["ollama_install_body"],
            font=self._font("model_desc"),
            text_color=self.text_muted,
            justify="left",
            wraplength=430,
        )
        body.pack(anchor="w", padx=16, pady=(0, 16))

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 8))

        open_btn = ctk.CTkButton(
            actions,
            text=UI_TEXT["ollama_install_open_site"],
            font=self._font("action", weight="bold"),
            fg_color=UI_COLORS["button_blue"],
            hover_color=UI_COLORS["button_blue_hover"],
            text_color=UI_COLORS["white"],
            command=self.open_ollama_download_page,
        )
        open_btn.pack(side="left", padx=(0, 8))

        copy_btn = ctk.CTkButton(
            actions,
            text=UI_TEXT["ollama_install_copy_command"],
            font=self._font("action"),
            fg_color=UI_COLORS["button_dark"],
            hover_color=UI_COLORS["button_dark_hover"],
            text_color=UI_COLORS["white"],
            command=self.copy_ollama_install_command,
        )
        copy_btn.pack(side="left", padx=(0, 8))

        close_btn = ctk.CTkButton(
            actions,
            text=UI_TEXT["ollama_install_close"],
            font=self._font("action"),
            fg_color=UI_COLORS["button_secondary"],
            hover_color=UI_COLORS["button_secondary_hover"],
            text_color=UI_COLORS["white"],
            command=modal.destroy,
        )
        close_btn.pack(side="right")

    def show_scan_error(self, err):
        if self.is_closing or not self.winfo_exists():
            return
        self.hide_loading_modal()
        self.rescan_btn.configure(state="normal", text=UI_TEXT["analyze"])
        self.scan_status_label.configure(text=UI_TEXT["scan_status_error"], text_color=UI_COLORS["danger"])
        messagebox.showerror(UI_TEXT["error_title"], UI_TEXT["scan_error_body"].format(value=str(err)))

    def run_in_ollama(self, tag):
        sys_os = platform.system()

        try:
            subprocess.run(["ollama", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            self.show_ollama_install_modal()
            return

        try:
            command_text = UI_ACTIONS["ollama_command_template"].format(tag=tag)
            if sys_os == "Windows":
                subprocess.Popen(["cmd", "/c", f"start cmd /k {command_text}"])
            elif sys_os == "Darwin":
                subprocess.Popen(["osascript", "-e", f'tell app "Terminal" to do script "{command_text}"'])
            elif sys_os == "Linux":
                terminal_launched = False
                for term in UI_ACTIONS["linux_terminal_candidates"]:
                    if shutil.which(term):
                        if term == "gnome-terminal":
                            subprocess.Popen([term, "--", "bash", "-c", f"{command_text}; exec bash"])
                        else:
                            subprocess.Popen([term, "-e", f"bash -c '{command_text}; exec bash'"])
                        terminal_launched = True
                        break
                if not terminal_launched:
                    self.copy_to_clipboard(command_text)
                    messagebox.showinfo(UI_TEXT["command_copied_title"], UI_TEXT["terminal_missing_body"].format(value=command_text))
            else:
                self.copy_to_clipboard(command_text)
                messagebox.showinfo(UI_TEXT["command_copied_title"], UI_TEXT["command_copied_body"].format(value=command_text))
        except Exception as err:
            messagebox.showerror(UI_TEXT["error_title"], UI_TEXT["terminal_open_error"].format(value=err))

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        
        # Format the display text by stripping raw markdown symbols for the dialog view
        import re
        display_text = text
        if text.startswith("#") or "**" in text:
            # Remove header markers (#, ##, etc.)
            display_text = re.sub(r"^#+\s*", "", display_text, flags=re.MULTILINE)
            # Remove bold markers (**)
            display_text = display_text.replace("**", "")
            # Convert list hyphens to bullets
            display_text = re.sub(r"^-\s*", "• ", display_text, flags=re.MULTILINE)
            
        messagebox.showinfo(UI_TEXT["clipboard_title"], UI_TEXT["clipboard_body"].format(value=display_text))

    def open_download_url(self, url):
        webbrowser.open(url)

    def open_ollama_download_page(self):
        self.open_download_url(UI_ACTIONS["ollama_download_url"])

    def copy_ollama_install_command(self):
        install_command = UI_ACTIONS["ollama_install_commands"].get(self.platform_name)
        if install_command:
            self.copy_to_clipboard(install_command)
            return
        messagebox.showinfo(
            UI_TEXT["ollama_missing_title"],
            UI_TEXT["ollama_install_command_missing"],
        )
        self.open_ollama_download_page()

    def show_image_model_guide(self, model_name):
        guide = UI_TEXT["image_guide_body"].format(value=model_name)
        messagebox.showinfo(UI_TEXT["image_guide_title"].format(value=model_name), guide)

    def ping_ollama(self) -> bool:
        import urllib.request
        try:
            req = urllib.request.Request(f"{config.OLLAMA_HOST}/")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_installed_ollama_models(self) -> list[str]:
        import urllib.request
        import json
        try:
            req = urllib.request.Request(f"{config.OLLAMA_HOST}/api/tags")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = data.get("models", [])
            return [m.get("name") for m in models if m.get("name")]
        except Exception:
            return []

    def pull_ollama_model_async(self, tag, on_progress, on_complete):
        import threading
        
        def worker():
            import urllib.request
            import json
            try:
                req = urllib.request.Request(
                    f"{config.OLLAMA_HOST}/api/pull",
                    data=json.dumps({"name": tag, "stream": True}).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=1200) as resp:
                    while True:
                        chunk = resp.readline()
                        if not chunk:
                            break
                        try:
                            line = json.loads(chunk.decode("utf-8"))
                            status = line.get("status", "")
                            completed = line.get("completed", 0)
                            total = line.get("total", 0)
                            if on_progress:
                                self.after(0, lambda c=completed, t=total, s=status: on_progress(c, t, s))
                        except Exception:
                            pass
                if on_complete:
                    self.after(0, lambda: on_complete(True, None))
            except Exception as e:
                if on_complete:
                    self.after(0, lambda err=e: on_complete(False, str(err)))
                    
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def start_ollama_download(self, tag, progress_bar, status_label, download_btn):
        download_btn.configure(state="disabled", text=UI_TEXT["download_in_progress"])
        status_label.grid()
        progress_bar.grid()
        progress_bar.set(0)

        def on_progress(completed, total, status):
            if total > 0:
                pct = completed / total
                progress_bar.set(pct)
                status_label.configure(text=f"{status} ({pct*100:.1f}%)")
            else:
                status_label.configure(text=status)

        def on_complete(success, err):
            if success:
                status_label.configure(text=UI_TEXT["download_success"], text_color=config.UI_COLORS["success"])
                progress_bar.grid_remove()
                download_btn.pack_forget()
                # Trigger a refresh of installed models list and GUI redraw
                self.refresh_installed_ollama_models()
            else:
                status_label.configure(text=f"{UI_TEXT['error_title']}: {err}", text_color=config.UI_COLORS["danger"])
                download_btn.configure(state="normal", text=UI_TEXT["download_retry"])

        self.pull_ollama_model_async(tag, on_progress, on_complete)
