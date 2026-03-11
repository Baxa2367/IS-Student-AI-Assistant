from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk


def make_labeled_text(parent, label: str, height: int = 120) -> tuple[ctk.CTkLabel, ctk.CTkTextbox]:
    """Create label + CTkTextbox block."""
    lab = ctk.CTkLabel(parent, text=label)
    txt = ctk.CTkTextbox(parent, height=height)
    return lab, txt


def clear_textbox(tb: ctk.CTkTextbox) -> None:
    """Clear CTkTextbox content."""
    tb.delete("1.0", "end")


def get_textbox(tb: ctk.CTkTextbox) -> str:
    """Get all text from CTkTextbox."""
    return tb.get("1.0", "end").rstrip()


def set_textbox(tb: ctk.CTkTextbox, text: str) -> None:
    """Replace CTkTextbox content."""
    clear_textbox(tb)
    tb.insert("1.0", text or "")


def build_result_table(parent) -> ttk.Treeview:
    """Create a ttk.Treeview for SELECT results."""
    tree = ttk.Treeview(parent, columns=(), show="headings", height=8)
    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)
    return tree


def fill_result_table(tree: ttk.Treeview, headers: list[str], rows: list[list[object]]) -> None:
    """Fill treeview with headers and rows."""
    # Clear previous
    for col in tree["columns"]:
        tree.heading(col, text="")
    tree.delete(*tree.get_children())

    tree["columns"] = headers
    for h in headers:
        tree.heading(h, text=h)
        tree.column(h, width=120, stretch=True)

    for r in rows:
        tree.insert("", "end", values=[_cell_to_str(x) for x in r])


def _cell_to_str(x: object) -> str:
    """Convert DB cell to printable string."""
    if x is None:
        return "NULL"
    return str(x)