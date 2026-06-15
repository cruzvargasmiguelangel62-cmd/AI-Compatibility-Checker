import os
import json
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

from src import config

UI_BASE = config.UI_BASE

# Load TRANSLATIONS dynamically from external JSON file
translations_path = os.path.join(config.CURRENT_DIR, "data", "translations.json")
try:
    with open(translations_path, "r", encoding="utf-8") as f:
        TRANSLATIONS = json.load(f)
except Exception as e:
    # Fallback to empty structures to prevent crash
    TRANSLATIONS = {
        "es": {
            "UI_TEXT": {},
            "UI_SPEC_CARDS": {},
            "MODEL_STATUS_LABELS": {},
            "MODEL_TEXT": {},
            "search_categories": []
        },
        "en": {
            "UI_TEXT": {},
            "UI_SPEC_CARDS": {},
            "MODEL_STATUS_LABELS": {},
            "MODEL_TEXT": {},
            "search_categories": []
        }
    }
    print(f"Warning: Failed to load translations from {translations_path}: {e}")


class AppTextMixin:
    def change_language(self, lang):
        self.lang = lang
        config.UI_TEXT.update(TRANSLATIONS[lang]["UI_TEXT"])
        for key in config.UI_SPEC_CARDS:
            if key in TRANSLATIONS[lang]["UI_SPEC_CARDS"]:
                config.UI_SPEC_CARDS[key]["title"] = TRANSLATIONS[lang]["UI_SPEC_CARDS"][key]["title"]
        config.MODEL_STATUS_LABELS.update(TRANSLATIONS[lang]["MODEL_STATUS_LABELS"])
        config.MODEL_TEXT.update(TRANSLATIONS[lang]["MODEL_TEXT"])
        config.UI_BASE["search_categories"] = TRANSLATIONS[lang]["search_categories"]

        if hasattr(self, "update_catalog_btn"):
            self.update_catalog_btn.configure(text=config.UI_TEXT.get("btn_update_catalog", "🔄 Actualizar Catálogo Online"))

    def _configure_typography(self):
        default_font = self.ui_tokens["font_family"]
        try:
            tkfont.nametofont("TkDefaultFont").configure(
                family=default_font,
                size=UI_BASE["font_sizes"]["sidebar_text"],
            )
            tkfont.nametofont("TkTextFont").configure(
                family=default_font,
                size=UI_BASE["font_sizes"]["sidebar_text"],
            )
            tkfont.nametofont("TkMenuFont").configure(
                family=default_font,
                size=UI_BASE["font_sizes"]["sidebar_text_small"],
            )
        except Exception:
            pass

    def _font(self, token, weight=None, slant="roman"):
        cache_key = (token, weight or "normal", slant)
        if cache_key not in self.font_cache:
            self.font_cache[cache_key] = ctk.CTkFont(
                family=self.ui_tokens["font_family"],
                size=UI_BASE["font_sizes"][token],
                weight=weight or "normal",
                slant=slant,
            )
        return self.font_cache[cache_key]

    def _dynamic_wraplength(self, ratio, minimum, maximum):
        current_width = max(self.winfo_width(), self.ui_tokens["initial_width"])
        return max(minimum, min(maximum, int(current_width * ratio)))

    def _wrap_text_to_pixels(self, text, font, max_width):
        if not text or max_width <= 0:
            return text

        if not hasattr(self, "_wrap_cache"):
            self._wrap_cache = {}

        # Safely extract font properties to use as cache key
        font_key = (
            font.cget("family") + str(font.cget("size")) + font.cget("weight") + font.cget("slant")
            if hasattr(font, "cget")
            else str(font)
        )
        cache_key = (text, font_key, max_width)
        if cache_key in self._wrap_cache:
            return self._wrap_cache[cache_key]

        measure_font = tkfont.Font(font=font)
        wrapped_lines = []
        for paragraph in str(text).splitlines() or [""]:
            words = paragraph.split()
            if not words:
                wrapped_lines.append("")
                continue

            current_line = words[0]
            for word in words[1:]:
                candidate = f"{current_line} {word}"
                if measure_font.measure(candidate) <= max_width:
                    current_line = candidate
                else:
                    wrapped_lines.append(current_line)
                    current_line = word
            wrapped_lines.append(current_line)

        res = "\n".join(wrapped_lines)
        self._wrap_cache[cache_key] = res
        return res

    def _measure_text_width(self, font, text, horizontal_padding=0, minimum=0, maximum=None):
        measured_width = tkfont.Font(font=font).measure(str(text)) + horizontal_padding
        measured_width = max(minimum, measured_width)
        if maximum is not None:
            measured_width = min(maximum, measured_width)
        return measured_width

    def _bind_wrapped_text(self, container, label, font, horizontal_padding=0, minimum=10, maximum=None):
        label._original_text = label.cget("text")

        # Intercept configure and config to dynamically update _original_text when changed
        orig_configure = label.configure
        def custom_configure(**kwargs):
            if "text" in kwargs:
                label._original_text = kwargs["text"]
            return orig_configure(**kwargs)
        label.configure = custom_configure

        if hasattr(label, "config"):
            orig_config = label.config
            def custom_config(**kwargs):
                if "text" in kwargs:
                    label._original_text = kwargs["text"]
                return orig_config(**kwargs)
            label.config = custom_config

        def _sync_text_wrap(event):
            if event.widget is not container:
                return
            available_width = max(minimum, event.width - horizontal_padding)
            if maximum is not None:
                available_width = min(maximum, available_width)
            
            # Avoid redundant layout/wrapping if the width hasn't changed
            if getattr(label, "_last_wrap_width", None) == available_width:
                return
            label._last_wrap_width = available_width

            wrapped_text = self._wrap_text_to_pixels(label._original_text, font, available_width)
            orig_configure(text=wrapped_text, wraplength=available_width)

        container.bind("<Configure>", _sync_text_wrap, add="+")

    def _ctk_font_to_tk(self, ctk_font):
        return tkfont.Font(
            family=ctk_font.cget("family"),
            size=ctk_font.cget("size"),
            weight=ctk_font.cget("weight"),
            slant=ctk_font.cget("slant"),
        )

    def _create_wrapped_message(self, parent, text, ctk_font, text_color, bg_color):
        label = tk.Label(
            parent,
            text=text,
            font=self._ctk_font_to_tk(ctk_font),
            fg=text_color,
            bg=bg_color,
            justify="left",
            anchor="w",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
        )
        label._original_text = text
        return label

    def _bind_message_width(self, container, message_widget, font=None, horizontal_padding=0, minimum=10, maximum=None):
        if isinstance(message_widget, (ctk.CTkLabel, tk.Label)):
            self._bind_wrapped_text(
                container,
                message_widget,
                font or message_widget.cget("font"),
                horizontal_padding=horizontal_padding,
                minimum=minimum,
                maximum=maximum,
            )
            return

        def _sync_message_width(event):
            if event.widget is not container:
                return
            available_width = max(minimum, event.width - horizontal_padding)
            if maximum is not None:
                available_width = min(maximum, available_width)
            
            # Avoid redundant configuration if the width hasn't changed
            if getattr(message_widget, "_last_message_width", None) == available_width:
                return
            message_widget._last_message_width = available_width

            message_widget.configure(width=available_width)

        container.bind("<Configure>", _sync_message_width, add="+")

    def _bind_label_to_container_width(self, container, labels, horizontal_padding=0, minimum=10, maximum=None):
        if not isinstance(labels, (list, tuple)):
            labels = [labels]

        def _sync_wraplength(event):
            if event.widget is not container:
                return
            available_width = max(minimum, event.width - horizontal_padding)
            if maximum is not None:
                available_width = min(maximum, available_width)
            
            # Avoid redundant configuration if the width hasn't changed
            if getattr(container, "_last_sync_width", None) == available_width:
                return
            container._last_sync_width = available_width

            for label in labels:
                label.configure(wraplength=available_width, anchor="w", justify="left")

        container.bind("<Configure>", _sync_wraplength, add="+")
