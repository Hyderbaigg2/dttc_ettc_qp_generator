"""Light, official-looking ttk styling shared across all tabs."""
import tkinter as tk
from tkinter import ttk

NAVY = "#1f3a5f"
NAVY_DARK = "#152a45"
BG = "#f4f6f9"
CARD_BG = "#ffffff"
ACCENT = "#c8a951"  # railway-gold accent
TEXT = "#1c1c1c"
MUTED = "#5a6472"
BORDER = "#d7dce3"

FONT_FAMILY = "Segoe UI"


def apply_theme(root: tk.Tk):
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", font=(FONT_FAMILY, 10), background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD_BG, relief="flat")
    style.configure("TLabel", background=BG, foreground=TEXT, font=(FONT_FAMILY, 10))
    style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT, font=(FONT_FAMILY, 10))
    style.configure("Header.TLabel", background=NAVY, foreground="white", font=(FONT_FAMILY, 16, "bold"))
    style.configure("SubHeader.TLabel", background=NAVY, foreground="#cdd9e8", font=(FONT_FAMILY, 9))
    style.configure("SectionTitle.TLabel", background=BG, foreground=NAVY, font=(FONT_FAMILY, 12, "bold"))
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=(FONT_FAMILY, 9))
    style.configure("CardMuted.TLabel", background=CARD_BG, foreground=MUTED, font=(FONT_FAMILY, 9))

    style.configure("TButton", font=(FONT_FAMILY, 10), padding=6)
    style.configure(
        "Accent.TButton",
        font=(FONT_FAMILY, 11, "bold"),
        padding=10,
        background=NAVY,
        foreground="white",
    )
    style.map(
        "Accent.TButton",
        background=[("active", NAVY_DARK), ("disabled", "#9aa7b8")],
        foreground=[("disabled", "#e5e8ec")],
    )

    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        font=(FONT_FAMILY, 10, "bold"),
        padding=(16, 10),
        background="#e4e9f0",
        foreground=NAVY,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", CARD_BG)],
        foreground=[("selected", NAVY)],
    )

    style.configure(
        "Treeview",
        background=CARD_BG,
        fieldbackground=CARD_BG,
        foreground=TEXT,
        rowheight=26,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        font=(FONT_FAMILY, 10, "bold"),
        background="#e4e9f0",
        foreground=NAVY,
        relief="flat",
    )
    style.map("Treeview", background=[("selected", NAVY)], foreground=[("selected", "white")])

    style.configure("TEntry", padding=4)
    style.configure("TCombobox", padding=4)
    style.configure("TLabelframe", background=BG, foreground=NAVY)
    style.configure("TLabelframe.Label", background=BG, foreground=NAVY, font=(FONT_FAMILY, 10, "bold"))
    style.configure("TCheckbutton", background=BG, foreground=TEXT)
    style.configure("Card.TCheckbutton", background=CARD_BG, foreground=TEXT)
    style.configure("Card.TRadiobutton", background=CARD_BG, foreground=TEXT)

    return style
