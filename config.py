import platform
import tkinter as tk

VERI_DOSYASI = "hisseler.json"

# Cross-platform font seçimi
_sistem = platform.system()
if _sistem == "Windows":
    _FONT_AILE = "MS Sans Serif"
    _FONT_MONO_AILE = "Courier New"
elif _sistem == "Darwin":  # macOS
    _FONT_AILE = "Helvetica"
    _FONT_MONO_AILE = "Monaco"
else:  # Linux / diğer
    _FONT_AILE = "DejaVu Sans"
    _FONT_MONO_AILE = "DejaVu Sans Mono"

# Tkinter'ın varsayılan fontlarını fallback olarak kullan
try:
    _test_root = tk.Tk()
    _test_root.withdraw()
    _default_font = _test_root.tk.call("font", "actual", "TkDefaultFont")
    _test_root.destroy()
except Exception:
    _default_font = (_FONT_AILE, 9)

FONT_APP_TITLE = (_FONT_AILE, 10, "bold")
FONT_LABEL = (_FONT_AILE, 9, "bold")
FONT_ENTRY = (_FONT_AILE, 9)
FONT_MONO = (_FONT_MONO_AILE, 9)
FONT_CARD_TITLE = (_FONT_MONO_AILE, 11, "bold")
FONT_CARD_VAL = (_FONT_MONO_AILE, 10, "bold")
FONT_TICKER = (_FONT_MONO_AILE, 9, "bold")

TEMALAR = {
    "Aydınlık": {
        "bg": "#d4d0c8",
        "fg": "#000000",
        "entry_bg": "#ffffff",
        "entry_fg": "#000000",
        "btn_bg": "#c0c0c0",
        "btn_fg": "#000080",
        "calc_btn_bg": "#c0c0c0",
        "calc_btn_fg": "#000080",
        "tree_bg": "#ffffff",
        "tree_fg": "#000000",
        "tree_head_bg": "#d4d0c8",
        "tree_head_fg": "#000000",
        "tree_selected": "#0a246a",
        "card_bg": "#e3e0d8",
        "card_fg": "#000080",
        "ticker_bg": "#1c1c1c",
        "ticker_fg": "#00ff66",
        "drawer_bg": "#e8e5df",
    },
    "Karanlık": {
        "bg": "#1e1e1e",
        "fg": "#e0e0e0",
        "entry_bg": "#2d2d2d",
        "entry_fg": "#00ff66",
        "btn_bg": "#333333",
        "btn_fg": "#00ffcc",
        "calc_btn_bg": "#2d4f3b",
        "calc_btn_fg": "#55ff99",
        "tree_bg": "#252526",
        "tree_fg": "#d4d4d4",
        "tree_head_bg": "#333333",
        "tree_head_fg": "#00e5ff",
        "tree_selected": "#264f78",
        "card_bg": "#121212",
        "card_fg": "#00e5ff",
        "ticker_bg": "#0a0a0a",
        "ticker_fg": "#00ffcc",
        "drawer_bg": "#252526",
    },
}