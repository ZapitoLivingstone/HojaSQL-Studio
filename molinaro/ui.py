from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shlex
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from molinaro.query_engine import QueryEngine, QueryResult
from molinaro.resources import resource_path
from molinaro.updater import check_for_updates, open_download_page
from molinaro.version import APP_NAME, APP_VERSION
from molinaro.workbook import EXCEL_EXTENSIONS, TableMeta, WorkbookSession, quote_identifier


APP_TITLE = APP_NAME
SQL_KEYWORDS = [
    "SELECT",
    "FROM",
    "WHERE",
    "GROUP BY",
    "ORDER BY",
    "LIMIT",
    "JOIN",
    "LEFT JOIN",
    "RIGHT JOIN",
    "INNER JOIN",
    "ON",
    "COUNT(*)",
    "AS",
    "AND",
    "OR",
    "IN",
    "LIKE",
    "DISTINCT",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
]
COMMANDS = [
    ".help",
    ".tables",
    ".columns",
    ".cols",
    ".selectcols",
    ".schema",
    ".findcol",
    ".find",
    ".preview",
    ".count",
    ".open",
    ".view",
    ".export",
    ".last",
    ".rerun",
    ".status",
    ".limit",
    ".maxcols",
    ".width",
    ".mode",
    ".clear",
    ".quit",
]
COMMAND_ALIASES = {
    ".cols": ".columns",
    ".find": ".findcol",
}
def resolve_state_dir() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    if state_home:
        return Path(state_home).expanduser() / "molinaro"
    return Path.home() / ".local" / "state" / "molinaro"


STATE_DIR = resolve_state_dir()
VIEWS_FILE = STATE_DIR / "saved_views.json"


@dataclass(slots=True)
class ConsoleSettings:
    limit: int = 100
    maxcols: int = 12
    width: int = 160
    mode: str = "table"


class AutoCompletePopup:
    def __init__(self, master: tk.Widget, on_pick):
        self.on_pick = on_pick
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg="#1b0f06")
        self.listbox = tk.Listbox(
            self.window,
            bg="#1b0f06",
            fg="#ffd36a",
            selectbackground="#2ef2c5",
            selectforeground="#081019",
            activestyle="none",
            highlightthickness=1,
            highlightbackground="#ff9f43",
            bd=0,
            font=("Consolas", 10),
            height=8,
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda _: self.pick())
        self.listbox.bind("<Return>", lambda _: self.pick())

    def show(self, x: int, y: int, suggestions: list[str]) -> None:
        self.listbox.delete(0, "end")
        for suggestion in suggestions:
            self.listbox.insert("end", suggestion)
        self.listbox.selection_clear(0, "end")
        if suggestions:
            self.listbox.selection_set(0)
            self.window.geometry(f"+{x}+{y}")
            self.window.deiconify()
            self.window.lift()
        else:
            self.hide()

    def hide(self) -> None:
        self.window.withdraw()

    def visible(self) -> bool:
        return str(self.window.state()) != "withdrawn"

    def move(self, direction: int) -> None:
        if not self.visible() or self.listbox.size() == 0:
            return
        current = self.listbox.curselection()
        index = current[0] if current else 0
        index = max(0, min(self.listbox.size() - 1, index + direction))
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.activate(index)

    def current(self) -> str | None:
        selection = self.listbox.curselection()
        if not selection:
            return None
        return self.listbox.get(selection[0])

    def pick(self) -> str:
        value = self.current()
        if value is not None:
            self.on_pick(value)
        self.hide()
        return "break"


class MolinaroApp:
    def __init__(self, initial_path: Path | None = None):
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} | Cyber SQL Console")
        self.root.geometry("1480x920")
        self.root.minsize(1180, 760)
        self.root.configure(bg="#050913")
        self._set_window_icon()

        self.workbook: WorkbookSession | None = None
        self.engine: QueryEngine | None = None
        self.current_result: QueryResult | None = None
        self.settings = ConsoleSettings()
        self.last_query: str | None = None
        self.file_var = tk.StringVar(value="Sin archivo abierto")
        self.status_var = tk.StringVar(value="Selecciona un Excel para comenzar.")
        self.table_search_var = tk.StringVar()
        self.column_search_var = tk.StringVar()
        self.view_name_var = tk.StringVar()
        self.popup: AutoCompletePopup | None = None
        self.saved_views: dict[str, str] = {}
        self.update_info: dict[str, str] | None = None

        self._configure_style()
        self._build_layout()
        self._bind_events()

        if initial_path:
            self.open_workbook(initial_path)
        else:
            self.root.after(50, self.open_workbook_dialog)
        self.root.after(1200, self.start_update_check)

    def _set_window_icon(self) -> None:
        ico_path = resource_path("chopper.ico")
        png_path = resource_path("assets/hojasql.png")
        try:
            if png_path.exists():
                self.icon_image = tk.PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self.icon_image)
        except tk.TclError:
            self.icon_image = None
        try:
            if ico_path.exists():
                self.root.iconbitmap(str(ico_path))
        except tk.TclError:
            pass

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("Root.TFrame", background="#050913")
        style.configure("Card.TFrame", background="#0a1422", relief="flat")
        style.configure("Header.TLabel", background="#0a1422", foreground="#ff4fd8", font=("Segoe UI Semibold", 18))
        style.configure("Muted.TLabel", background="#0a1422", foreground="#7eb4c4")
        style.configure("Section.TLabel", background="#0a1422", foreground="#74f7ff", font=("Segoe UI Semibold", 11))
        style.configure("Status.TLabel", background="#09111d", foreground="#c5f4ff", padding=(10, 7))
        style.configure("Accent.TButton", background="#14253d", foreground="#74f7ff", padding=(10, 7))
        style.map("Accent.TButton", background=[("active", "#1f395d")], foreground=[("active", "#ffffff")])
        style.configure("Treeview", background="#07111c", fieldbackground="#07111c", foreground="#d5ecff", rowheight=26)
        style.configure("Treeview.Heading", background="#0f2034", foreground="#74f7ff", font=("Segoe UI Semibold", 10))
        style.map("Treeview", background=[("selected", "#ff4fd8")], foreground=[("selected", "#06101b")])

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self.root, style="Root.TFrame", padding=14)
        root_frame.pack(fill="both", expand=True)

        header = ttk.Frame(root_frame, style="Card.TFrame", padding=14)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text=APP_TITLE, style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Selecciona un Excel, escribe comandos o SQL en una consola ciberpunk y revisa los resultados abajo.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 10))

        controls = ttk.Frame(header, style="Card.TFrame")
        controls.pack(fill="x")
        ttk.Button(controls, text="Abrir Excel", command=self.open_workbook_dialog, style="Accent.TButton").pack(side="left")
        ttk.Button(controls, text="Ejecutar", command=self.execute_current, style="Accent.TButton").pack(side="left", padx=8)
        ttk.Button(controls, text="Exportar", command=self.export_result, style="Accent.TButton").pack(side="left")
        ttk.Button(controls, text="Todas las columnas", command=self.show_all_columns, style="Accent.TButton").pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Buscar actualizaciones", command=self.check_updates_manually, style="Accent.TButton").pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Limpiar consola", command=self.clear_console, style="Accent.TButton").pack(side="left", padx=(8, 0))
        ttk.Label(controls, textvariable=self.file_var, style="Muted.TLabel").pack(side="right")

        body = ttk.Panedwindow(root_frame, orient="horizontal")
        body.pack(fill="both", expand=True)

        sidebar = ttk.Frame(body, style="Card.TFrame", padding=12)
        main = ttk.Frame(body, style="Card.TFrame", padding=12)
        body.add(sidebar, weight=1)
        body.add(main, weight=4)

        ttk.Label(sidebar, text="Tablas", style="Section.TLabel").pack(anchor="w")
        ttk.Entry(sidebar, textvariable=self.table_search_var).pack(fill="x", pady=(8, 10))
        self.tables_list = tk.Listbox(
            sidebar,
            bg="#07111c",
            fg="#74f7ff",
            selectbackground="#ff4fd8",
            selectforeground="#081019",
            exportselection=False,
            highlightthickness=0,
            bd=0,
            font=("Consolas", 10),
        )
        self.tables_list.pack(fill="both", expand=True)

        ttk.Label(sidebar, text="Vistas guardadas", style="Section.TLabel").pack(anchor="w", pady=(12, 0))
        self.views_list = tk.Listbox(
            sidebar,
            bg="#07111c",
            fg="#ffd36a",
            selectbackground="#ff9f43",
            selectforeground="#081019",
            exportselection=False,
            highlightthickness=0,
            bd=0,
            font=("Consolas", 10),
            height=6,
        )
        self.views_list.pack(fill="both", expand=False, pady=(8, 0))
        views_actions = ttk.Frame(sidebar, style="Card.TFrame")
        views_actions.pack(fill="x", pady=(8, 10))
        ttk.Button(views_actions, text="Guardar vista", command=self.prompt_save_view, style="Accent.TButton").pack(side="left")
        ttk.Button(views_actions, text="Cargar vista", command=self.load_selected_view_into_editor, style="Accent.TButton").pack(side="left", padx=6)

        ttk.Label(sidebar, text="Columnas", style="Section.TLabel").pack(anchor="w", pady=(12, 0))
        ttk.Entry(sidebar, textvariable=self.column_search_var).pack(fill="x", pady=(8, 10))
        self.columns_list = tk.Listbox(
            sidebar,
            bg="#07111c",
            fg="#c5f4ff",
            selectbackground="#1df2ff",
            selectforeground="#07111c",
            exportselection=False,
            highlightthickness=0,
            bd=0,
            font=("Consolas", 10),
        )
        self.columns_list.pack(fill="both", expand=True)
        column_actions = ttk.Frame(sidebar, style="Card.TFrame")
        column_actions.pack(fill="x", pady=(8, 0))
        ttk.Button(column_actions, text="Insertar", command=self.insert_selected_column, style="Accent.TButton").pack(side="left")
        ttk.Button(column_actions, text="Copiar", command=self.copy_selected_column, style="Accent.TButton").pack(side="left", padx=6)

        terminal_card = ttk.Frame(main, style="Card.TFrame")
        terminal_card.pack(fill="both", expand=False)
        ttk.Label(terminal_card, text="Consola SQL", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            terminal_card,
            text="Enter ejecuta. Shift+Enter inserta una nueva linea. TAB autocompleta.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 8))

        terminal_panel = tk.Frame(terminal_card, bg="#06101b", highlightbackground="#1df2ff", highlightthickness=1)
        terminal_panel.pack(fill="x")
        self.console_input = tk.Text(
            terminal_panel,
            height=10,
            wrap="word",
            bg="#06101b",
            fg="#75ffef",
            insertbackground="#ff4fd8",
            selectbackground="#14395d",
            relief="flat",
            font=("Consolas", 11),
            padx=12,
            pady=12,
            undo=True,
        )
        self.console_input.pack(fill="x")
        self.popup = AutoCompletePopup(self.root, self.apply_completion)

        ttk.Label(terminal_card, text="Salida de comandos", style="Section.TLabel").pack(anchor="w", pady=(10, 6))
        log_frame = tk.Frame(terminal_card, bg="#04101a", highlightbackground="#16314d", highlightthickness=1)
        log_frame.pack(fill="x", pady=(10, 0))
        self.console_log = tk.Text(
            log_frame,
            height=7,
            wrap="word",
            bg="#04101a",
            fg="#c5f4ff",
            relief="flat",
            font=("Consolas", 10),
            padx=12,
            pady=10,
            state="disabled",
        )
        self.console_log.pack(fill="x")

        result_card = ttk.Frame(main, style="Card.TFrame")
        result_card.pack(fill="both", expand=True, pady=(12, 0))
        ttk.Label(result_card, text="Resultados", style="Section.TLabel").pack(anchor="w")
        self.result_summary = ttk.Label(result_card, text="Sin resultados.", style="Muted.TLabel")
        self.result_summary.pack(anchor="w", pady=(4, 8))

        tree_frame = ttk.Frame(result_card, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.results_tree = ttk.Treeview(tree_frame, show="headings")
        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.results_tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        status = ttk.Label(root_frame, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        status.pack(fill="x", pady=(12, 0))

    def _bind_events(self) -> None:
        self.console_input.bind("<Return>", self.on_return_pressed)
        self.console_input.bind("<Shift-Return>", self.insert_newline)
        self.console_input.bind("<Tab>", self.on_tab_pressed)
        self.console_input.bind("<KeyRelease>", self.on_editor_changed)
        self.console_input.bind("<Down>", self.on_popup_down)
        self.console_input.bind("<Up>", self.on_popup_up)
        self.console_input.bind("<Escape>", self.on_popup_escape)
        self.tables_list.bind("<<ListboxSelect>>", self.on_table_selected)
        self.tables_list.bind("<Double-Button-1>", self.insert_selected_table)
        self.tables_list.bind("<Button-3>", self.show_table_menu)
        self.columns_list.bind("<Double-Button-1>", self.insert_selected_column)
        self.columns_list.bind("<Button-3>", self.show_column_menu)
        self.columns_list.bind("<Control-c>", self.copy_selected_column_event)
        self.views_list.bind("<Double-Button-1>", self.load_selected_view_into_editor_event)
        self.views_list.bind("<Button-3>", self.show_view_menu)
        self.table_search_var.trace_add("write", lambda *_: self.refresh_tables())
        self.column_search_var.trace_add("write", lambda *_: self.refresh_columns())

    def run(self) -> None:
        self.root.mainloop()

    def open_workbook_dialog(self) -> None:
        selected = filedialog.askopenfilename(
            title="Selecciona un archivo Excel",
            filetypes=[("Archivos Excel", "*.xlsx *.xls *.xlsm"), ("Todos los archivos", "*.*")],
        )
        if selected:
            self.open_workbook(Path(selected))

    def open_workbook(self, xlsx_path: Path) -> None:
        path = Path(xlsx_path).expanduser().resolve()
        if not path.exists():
            messagebox.showerror(APP_TITLE, f"No existe el archivo:\n{path}")
            return
        if path.suffix.lower() not in EXCEL_EXTENSIONS:
            messagebox.showerror(APP_TITLE, "Selecciona un archivo Excel valido.")
            return

        try:
            if self.workbook is not None:
                self.workbook.close()
            self.workbook = WorkbookSession.load(path)
            self.engine = QueryEngine(self.workbook)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"No pude abrir el Excel.\n\n{exc}")
            return

        self.file_var.set(str(path))
        self.status_var.set(f"Archivo cargado: {path.name}")
        self.current_result = None
        self.last_query = None
        self.result_summary.configure(text="Sin resultados.")
        self.clear_console()
        self.refresh_tables()
        self.load_saved_views()
        self._clear_tree()
        self.log_banner()
        self.log_help()

        if self.workbook.tables:
            self.tables_list.selection_clear(0, "end")
            self.tables_list.selection_set(0)
            self.tables_list.event_generate("<<ListboxSelect>>")
            first = self.workbook.tables[0].table_name
            self.console_input.delete("1.0", "end")
            self.console_input.insert("1.0", f"SELECT *\nFROM {first}\nLIMIT 50;")
            self.console_input.focus_set()

    def log(self, message: str = "", tag: str = "plain") -> None:
        colors = {
            "plain": "#c5f4ff",
            "accent": "#74f7ff",
            "magenta": "#ff4fd8",
            "warn": "#ffc857",
            "error": "#ff7a90",
            "ok": "#7dff8d",
            "dim": "#7eb4c4",
        }
        self.console_log.configure(state="normal")
        if tag not in self.console_log.tag_names():
            self.console_log.tag_configure(tag, foreground=colors.get(tag, "#c5f4ff"))
        self.console_log.insert("end", message + "\n", tag)
        self.console_log.see("end")
        self.console_log.configure(state="disabled")

    def clear_console(self) -> None:
        self.console_log.configure(state="normal")
        self.console_log.delete("1.0", "end")
        self.console_log.configure(state="disabled")
        self.status_var.set("Consola limpiada.")

    def log_banner(self) -> None:
        if self.workbook is None:
            return
        self.log("=============================== HojaSQL Studio Cyber SQL Console ===============================", "magenta")
        self.log(f"Archivo: {self.workbook.xlsx_path}", "accent")
        self.log(f"Versión: {APP_VERSION}", "dim")
        self.log(f"Tablas cargadas: {len(self.workbook.tables)}", "dim")
        self.log("Enter ejecuta | Shift+Enter agrega linea | TAB autocompleta | .help muestra comandos", "dim")
        self.log("", "plain")

    def log_help(self) -> None:
        self.log("Comandos disponibles:", "accent")
        self.log(".help | .tables | .cols TABLA [TEXTO] | .find TEXTO | .schema TABLA", "dim")
        self.log(".preview TABLA [N] | .count TABLA | .selectcols TABLA | .open | .export [RUTA]", "dim")
        self.log(".status | .last | .rerun | .limit N | .maxcols N|all | .width N | .mode table|csv|json | .view NOMBRE", "dim")
        self.log("", "plain")

    def refresh_tables(self) -> None:
        self.tables_list.delete(0, "end")
        if self.workbook is None:
            return
        needle = self.table_search_var.get().strip().lower()
        for table in self.workbook.tables:
            label = f"{table.table_name}  [{table.rows} filas]"
            if needle and needle not in label.lower():
                continue
            self.tables_list.insert("end", label)

    def refresh_columns(self) -> None:
        self.columns_list.delete(0, "end")
        table = self.selected_table()
        if table is None:
            return
        needle = self.column_search_var.get().strip().lower()
        for column in table.columns:
            label = f"{column} :: {table.dtypes[column]}"
            if needle and needle not in label.lower():
                continue
            self.columns_list.insert("end", label)

    def refresh_views(self) -> None:
        self.views_list.delete(0, "end")
        for view_name in sorted(self.saved_views):
            self.views_list.insert("end", view_name)

    def selected_table(self) -> TableMeta | None:
        if self.workbook is None:
            return None
        selection = self.tables_list.curselection()
        if not selection:
            return None
        label = self.tables_list.get(selection[0])
        return self.workbook.find_table(label.split("  [", 1)[0])

    def on_table_selected(self, event=None) -> None:
        self.refresh_columns()

    def show_table_menu(self, event) -> str:
        index = self.tables_list.nearest(event.y)
        if index < 0:
            return "break"
        self.tables_list.selection_clear(0, "end")
        self.tables_list.selection_set(index)
        menu = tk.Menu(self.root, tearoff=0, bg="#081019", fg="#74f7ff", activebackground="#ff9f43", activeforeground="#081019")
        menu.add_command(label="Ver tabla", command=self.preview_selected_table)
        menu.add_command(label="Contar filas", command=self.count_selected_table)
        menu.add_command(label="Insertar nombre", command=self.insert_selected_table)
        menu.add_command(label="Cargar SELECT base", command=self.load_selected_table_template)
        menu.add_command(label="Cargar SELECT con columnas", command=self.load_selected_table_columns_query)
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()
        return "break"

    def show_column_menu(self, event) -> str:
        index = self.columns_list.nearest(event.y)
        if index < 0:
            return "break"
        self.columns_list.selection_clear(0, "end")
        self.columns_list.selection_set(index)
        menu = tk.Menu(self.root, tearoff=0, bg="#081019", fg="#c5f4ff", activebackground="#2ef2c5", activeforeground="#081019")
        menu.add_command(label="Insertar columna", command=self.insert_selected_column)
        menu.add_command(label="Copiar nombre", command=self.copy_selected_column)
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()
        return "break"

    def show_view_menu(self, event) -> str:
        index = self.views_list.nearest(event.y)
        if index < 0:
            return "break"
        self.views_list.selection_clear(0, "end")
        self.views_list.selection_set(index)
        menu = tk.Menu(self.root, tearoff=0, bg="#081019", fg="#ffd36a", activebackground="#ff9f43", activeforeground="#081019")
        menu.add_command(label="Cargar vista", command=self.load_selected_view_into_editor)
        menu.add_command(label="Ejecutar vista", command=self.run_selected_view)
        menu.add_command(label="Eliminar vista", command=self.delete_selected_view)
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()
        return "break"

    def insert_selected_table(self, event=None) -> None:
        table = self.selected_table()
        if table is not None:
            self.console_input.insert("insert", table.table_name)
            self.status_var.set(f"Tabla insertada: {table.table_name}")

    def insert_selected_column(self, event=None) -> None:
        selection = self.columns_list.curselection()
        if not selection:
            return "break" if event is not None else None
        label = self.columns_list.get(selection[0])
        column_name = label.split(" :: ", 1)[0]
        self.console_input.insert("insert", quote_identifier(column_name))
        self.status_var.set(f"Columna insertada: {column_name}")
        return "break" if event is not None else None

    def copy_selected_column(self) -> None:
        selection = self.columns_list.curselection()
        if not selection:
            self.status_var.set("Selecciona una columna para copiar.")
            return
        label = self.columns_list.get(selection[0])
        column_name = label.split(" :: ", 1)[0]
        self.root.clipboard_clear()
        self.root.clipboard_append(column_name)
        self.status_var.set(f"Columna copiada: {column_name}")

    def copy_selected_column_event(self, event=None) -> str:
        self.copy_selected_column()
        return "break"

    def editor_text(self) -> str:
        return self.console_input.get("1.0", "end").strip()

    def on_return_pressed(self, event=None) -> str:
        self.execute_current()
        return "break"

    def insert_newline(self, event=None) -> str:
        self.console_input.insert("insert", "\n")
        self.update_completions()
        return "break"

    def on_tab_pressed(self, event=None) -> str:
        if self.popup and self.popup.visible():
            return self.popup.pick()
        self.update_completions(force=True)
        if self.popup and self.popup.visible():
            return "break"
        self.console_input.insert("insert", "    ")
        return "break"

    def on_popup_down(self, event=None) -> str | None:
        if self.popup and self.popup.visible():
            self.popup.move(1)
            return "break"
        return None

    def on_popup_up(self, event=None) -> str | None:
        if self.popup and self.popup.visible():
            self.popup.move(-1)
            return "break"
        return None

    def on_popup_escape(self, event=None) -> str | None:
        if self.popup and self.popup.visible():
            self.popup.hide()
            return "break"
        return None

    def on_editor_changed(self, event=None) -> None:
        self.update_completions()

    def completion_words(self) -> list[str]:
        words = set(COMMANDS + SQL_KEYWORDS)
        if self.workbook is not None:
            words.update(table.table_name for table in self.workbook.tables)
            words.update(self.saved_views.keys())
            for table in self.workbook.tables:
                for column in table.columns:
                    words.add(column)
                    words.add(quote_identifier(column))
        return sorted(words, key=str.lower)

    def current_token(self) -> tuple[str, str]:
        content = self.console_input.get("1.0", "insert")
        token = ""
        for char in reversed(content):
            if char.isspace():
                break
            token = char + token
        return content, token

    def update_completions(self, force: bool = False) -> None:
        if self.popup is None:
            return
        _, token = self.current_token()
        if not token and not force:
            self.popup.hide()
            return

        matches = [word for word in self.completion_words() if word.lower().startswith(token.lower()) and word != token]
        matches = matches[:10]
        if not matches:
            self.popup.hide()
            return

        bbox = self.console_input.bbox("insert")
        if bbox is None:
            self.popup.hide()
            return
        x, y, width, height = bbox
        abs_x = self.console_input.winfo_rootx() + x
        abs_y = self.console_input.winfo_rooty() + y + height + 4
        self.popup.show(abs_x, abs_y, matches)

    def apply_completion(self, value: str) -> None:
        _, token = self.current_token()
        if token:
            self.console_input.delete(f"insert-{len(token)}c", "insert")
        self.console_input.insert("insert", value)

    def execute_current(self) -> None:
        if self.workbook is None or self.engine is None:
            messagebox.showinfo(APP_TITLE, "Primero selecciona un archivo Excel.")
            return

        text = self.editor_text()
        if not text:
            return
        if self.popup:
            self.popup.hide()

        self.log(f">>> {text}", "magenta")

        try:
            if text.startswith("."):
                self.handle_command(text)
            else:
                self.run_sql(text.rstrip(";"))
        except Exception as exc:
            self.log(f"Error: {exc}", "error")
            self.status_var.set("Operacion fallida.")

    def run_sql(self, sql: str) -> None:
        if self.engine is None:
            return
        result = self.engine.run(sql, row_limit=self.settings.limit)
        self.current_result = result
        self.last_query = sql
        self.render_result(result)
        suffix = " | truncado" if result.truncated else ""
        self.log(f"Query OK en {result.elapsed_seconds:.3f}s{suffix}", "ok")
        self.status_var.set("Consulta ejecutada correctamente.")

    def handle_command(self, raw_command: str) -> None:
        parts = shlex.split(raw_command)
        if not parts:
            return
        command = COMMAND_ALIASES.get(parts[0], parts[0])

        if command == ".help":
            self.log_help()
        elif command == ".tables":
            self.show_tables_in_log()
        elif command == ".columns" and len(parts) in {2, 3}:
            self.show_columns(parts[1], parts[2] if len(parts) == 3 else None)
        elif command == ".schema" and len(parts) == 2:
            self.show_columns(parts[1], None, schema=True)
        elif command == ".findcol" and len(parts) == 2:
            self.find_columns(parts[1])
        elif command == ".preview" and len(parts) in {2, 3}:
            limit = int(parts[2]) if len(parts) == 3 else self.settings.limit
            self.run_sql(f"SELECT * FROM {parts[1]} LIMIT {limit}")
        elif command == ".count" and len(parts) == 2:
            self.run_sql(f"SELECT COUNT(*) AS filas FROM {parts[1]}")
        elif command == ".selectcols" and len(parts) == 2:
            self.load_table_columns_query(parts[1])
        elif command == ".open":
            if len(parts) == 2:
                self.open_workbook(Path(parts[1]))
            else:
                self.open_workbook_dialog()
        elif command == ".view" and len(parts) == 2:
            self.load_view_into_editor(parts[1])
        elif command == ".export":
            self.export_result(parts[1] if len(parts) == 2 else None)
        elif command == ".last":
            self.log(self.last_query or "No hay consulta anterior.", "dim")
        elif command == ".rerun":
            if self.last_query:
                self.run_sql(self.last_query)
            else:
                self.log("No hay consulta anterior.", "warn")
        elif command == ".status":
            self.show_status()
        elif command == ".limit" and len(parts) == 2:
            self.settings.limit = max(1, int(parts[1]))
            self.log(f"limit = {self.settings.limit}", "ok")
        elif command == ".maxcols" and len(parts) == 2:
            value = parts[1].lower()
            if value in {"all", "0"}:
                self.settings.maxcols = 0
                self.log("maxcols = todas", "ok")
            else:
                self.settings.maxcols = max(1, int(parts[1]))
                self.log(f"maxcols = {self.settings.maxcols}", "ok")
            self.rerender_current_result()
        elif command == ".width" and len(parts) == 2:
            self.settings.width = max(60, int(parts[1]))
            self.log(f"width = {self.settings.width}", "ok")
        elif command == ".mode" and len(parts) == 2 and parts[1] in {"table", "csv", "json"}:
            self.settings.mode = parts[1]
            self.log(f"mode = {self.settings.mode}", "ok")
        elif command == ".clear":
            self.clear_console()
            self.log_banner()
        elif command == ".quit":
            self.root.destroy()
        else:
            self.log("Comando no reconocido o argumentos invalidos. Usa .help", "warn")

    def show_tables_in_log(self) -> None:
        if self.workbook is None:
            return
        self.log("Tablas cargadas:", "accent")
        for table in self.workbook.tables:
            self.log(f"- {table.table_name} | hoja={table.sheet_name.strip()} | filas={table.rows} | columnas={len(table.columns)}", "dim")

    def show_columns(self, table_name: str, term: str | None, schema: bool = False) -> None:
        if self.workbook is None:
            return
        table = self.workbook.find_table(table_name)
        if table is None:
            self.log(f"No existe la tabla: {table_name}", "error")
            return
        title = f"Schema {table_name}:" if schema else f"Columnas {table_name}:"
        self.log(title, "accent")
        found = 0
        for column in table.columns:
            dtype = table.dtypes[column]
            if term and term.lower() not in column.lower():
                continue
            self.log(f"- {column} :: {dtype}", "dim")
            found += 1
            if found >= 120:
                self.log("Mostrando 120 columnas. Usa filtro para acotar.", "warn")
                break
        if found == 0:
            self.log("No encontre columnas que coincidan.", "warn")

    def find_columns(self, term: str) -> None:
        if self.workbook is None:
            return
        self.log(f"Buscando columnas con '{term}':", "accent")
        found = 0
        for table in self.workbook.tables:
            for column in table.columns:
                if term.lower() in column.lower():
                    self.log(f"- {table.table_name}.{column} :: {table.dtypes[column]}", "dim")
                    found += 1
                    if found >= 160:
                        self.log("Mostrando 160 coincidencias. Refina el termino.", "warn")
                        return
        if found == 0:
            self.log("Sin coincidencias.", "warn")

    def show_status(self) -> None:
        if self.workbook is None:
            return
        self.log("Estado actual:", "accent")
        self.log(f"- archivo: {self.workbook.xlsx_path}", "dim")
        self.log(f"- limit: {self.settings.limit}", "dim")
        self.log(f"- maxcols: {self.settings.maxcols}", "dim")
        self.log(f"- width: {self.settings.width}", "dim")
        self.log(f"- mode: {self.settings.mode}", "dim")
        self.log(f"- ultima_consulta: {'si' if self.last_query else 'no'}", "dim")

    def render_result(self, result: QueryResult) -> None:
        if self.settings.mode == "csv":
            self.log(result.dataframe.to_csv(index=False).rstrip(), "dim")
        elif self.settings.mode == "json":
            self.log(result.dataframe.to_json(orient="records", force_ascii=False, indent=2), "dim")

        visible = result.dataframe.copy() if self.settings.maxcols <= 0 else result.dataframe.iloc[:, : self.settings.maxcols].copy()
        self._clear_tree()
        columns = [str(column) for column in visible.columns]
        self.results_tree["columns"] = columns
        for column in columns:
            self.results_tree.heading(column, text=column)
            self.results_tree.column(column, width=min(max(len(column) * 11, 90), 220), stretch=False)
        for row in visible.fillna("").astype(str).itertuples(index=False, name=None):
            self.results_tree.insert("", "end", values=row)

        hidden = len(result.dataframe.columns) - len(visible.columns)
        summary = f"{len(result.dataframe)} filas x {len(result.dataframe.columns)} columnas | {result.elapsed_seconds:.3f}s"
        if hidden > 0:
            summary += f" | {hidden} columnas ocultas por maxcols"
        else:
            summary += " | mostrando todas las columnas"
        if result.truncated:
            summary += " | truncado por limit"
        self.result_summary.configure(text=summary)

    def _clear_tree(self) -> None:
        self.results_tree.delete(*self.results_tree.get_children())
        self.results_tree["columns"] = ()

    def export_result(self, explicit_path: str | None = None) -> None:
        if self.engine is None or self.last_query is None:
            self.log("No hay consulta para exportar.", "warn")
            return

        if explicit_path:
            output = explicit_path
        else:
            output = filedialog.asksaveasfilename(
                title="Exportar resultado",
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv"), ("Todos los archivos", "*.*")],
            )
        if not output:
            return

        saved = self.engine.export(self.last_query, Path(output))
        self.log(f"Exportado: {saved}", "ok")
        self.status_var.set(f"Resultado exportado a {saved}")

    def rerender_current_result(self) -> None:
        if self.current_result is not None:
            self.render_result(self.current_result)

    def show_all_columns(self) -> None:
        self.settings.maxcols = 0
        self.rerender_current_result()
        self.log("Mostrando todas las columnas del resultado actual.", "ok")
        self.status_var.set("Mostrando todas las columnas.")

    def start_update_check(self) -> None:
        thread = threading.Thread(target=self._background_update_check, daemon=True)
        thread.start()

    def _background_update_check(self) -> None:
        update_info = check_for_updates()
        if update_info:
            self.root.after(0, lambda: self.notify_update_available(update_info, automatic=True))

    def check_updates_manually(self) -> None:
        self.status_var.set("Buscando actualizaciones...")
        thread = threading.Thread(target=self._manual_update_check, daemon=True)
        thread.start()

    def _manual_update_check(self) -> None:
        update_info = check_for_updates()
        self.root.after(0, lambda: self.finish_manual_update_check(update_info))

    def finish_manual_update_check(self, update_info: dict[str, str] | None) -> None:
        if update_info:
            self.notify_update_available(update_info, automatic=False)
            return
        self.log("No hay actualizaciones disponibles.", "dim")
        self.status_var.set("Ya tienes la última versión disponible.")
        messagebox.showinfo(APP_TITLE, "Ya tienes la última versión disponible.")

    def notify_update_available(self, update_info: dict[str, str], automatic: bool) -> None:
        self.update_info = update_info
        version = update_info["version"]
        self.log(f"Actualización disponible: {version}", "warn")
        self.status_var.set(f"Actualización disponible: {version}")
        prompt = (
            f"Hay una nueva versión disponible: {version}\n\n"
            f"Versión actual: {APP_VERSION}\n"
            "¿Quieres abrir la descarga?"
        )
        if automatic:
            prompt = "Se detectó una nueva versión.\n\n" + prompt
        if messagebox.askyesno(APP_TITLE, prompt):
            open_download_page(update_info["url"] or update_info["html_url"])

    def preview_selected_table(self) -> None:
        table = self.selected_table()
        if table is None:
            return
        self.run_sql(f"SELECT * FROM {table.table_name} LIMIT {self.settings.limit}")

    def count_selected_table(self) -> None:
        table = self.selected_table()
        if table is None:
            return
        self.run_sql(f"SELECT COUNT(*) AS filas FROM {table.table_name}")

    def load_selected_table_template(self) -> None:
        table = self.selected_table()
        if table is None:
            return
        self.console_input.delete("1.0", "end")
        self.console_input.insert("1.0", f"SELECT *\nFROM {table.table_name}\nLIMIT 50;")
        self.console_input.focus_set()
        self.status_var.set(f"Plantilla cargada para {table.table_name}")

    def load_selected_table_columns_query(self) -> None:
        table = self.selected_table()
        if table is None:
            return
        self.load_table_columns_query(table.table_name)

    def load_table_columns_query(self, table_name: str) -> None:
        if self.workbook is None:
            return
        table = self.workbook.find_table(table_name)
        if table is None:
            self.log(f"No existe la tabla: {table_name}", "warn")
            return
        columns_sql = ",\n".join(f"    {quote_identifier(column)}" for column in table.columns)
        query = f"SELECT\n{columns_sql}\nFROM {table.table_name}\nLIMIT 50;"
        self.console_input.delete("1.0", "end")
        self.console_input.insert("1.0", query)
        self.console_input.focus_set()
        self.status_var.set(f"SELECT con columnas cargado para {table.table_name}")
        self.log(f"SELECT con {len(table.columns)} columnas cargado para {table.table_name}", "ok")

    def ensure_state_dir(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    def workbook_key(self) -> str | None:
        if self.workbook is None:
            return None
        return hashlib.sha1(str(self.workbook.xlsx_path).encode("utf-8")).hexdigest()

    def read_views_store(self) -> dict[str, dict[str, str]]:
        if not VIEWS_FILE.exists():
            return {}
        try:
            return json.loads(VIEWS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def write_views_store(self, store: dict[str, dict[str, str]]) -> None:
        self.ensure_state_dir()
        VIEWS_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_or_replace_view(self, view_name: str, sql: str) -> None:
        if self.workbook is None:
            return
        self.workbook.connection.sql(f"CREATE OR REPLACE VIEW {quote_identifier(view_name)} AS {sql}")

    def load_saved_views(self) -> None:
        self.saved_views = {}
        key = self.workbook_key()
        if key is None:
            self.refresh_views()
            return
        store = self.read_views_store()
        self.saved_views = store.get(key, {})
        for view_name, sql in self.saved_views.items():
            try:
                self.create_or_replace_view(view_name, sql)
            except Exception as exc:
                self.log(f"No pude cargar vista {view_name}: {exc}", "warn")
        self.refresh_views()

    def prompt_save_view(self) -> None:
        sql = self.editor_text().rstrip(";")
        if not sql or sql.startswith("."):
            self.log("Escribe una consulta SQL antes de guardar una vista.", "warn")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Guardar vista")
        dialog.configure(bg="#0a1422")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Nombre de la vista", style="Section.TLabel").pack(anchor="w", padx=14, pady=(14, 6))
        entry = ttk.Entry(dialog, textvariable=self.view_name_var)
        entry.pack(fill="x", padx=14, pady=(0, 12))
        entry.focus_set()

        def save():
            name = self.view_name_var.get().strip()
            if not name:
                messagebox.showwarning(APP_TITLE, "Ingresa un nombre para la vista.")
                return
            try:
                self.save_view(name, sql)
            except Exception as exc:
                messagebox.showerror(APP_TITLE, f"No pude guardar la vista.\n\n{exc}")
                return
            self.view_name_var.set("")
            dialog.destroy()

        buttons = ttk.Frame(dialog, style="Card.TFrame")
        buttons.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(buttons, text="Guardar", command=save, style="Accent.TButton").pack(side="left")
        ttk.Button(buttons, text="Cancelar", command=dialog.destroy, style="Accent.TButton").pack(side="left", padx=8)

    def save_view(self, view_name: str, sql: str) -> None:
        key = self.workbook_key()
        if key is None:
            return
        self.create_or_replace_view(view_name, sql)
        store = self.read_views_store()
        workbook_views = store.setdefault(key, {})
        workbook_views[view_name] = sql
        self.write_views_store(store)
        self.saved_views[view_name] = sql
        self.refresh_views()
        self.status_var.set(f"Vista guardada: {view_name}")
        self.log(f"Vista guardada: {view_name}", "ok")

    def selected_view_name(self) -> str | None:
        selection = self.views_list.curselection()
        if not selection:
            return None
        return self.views_list.get(selection[0])

    def load_view_into_editor(self, view_name: str) -> None:
        sql = self.saved_views.get(view_name)
        if not sql:
            self.log(f"No existe la vista: {view_name}", "warn")
            return
        self.console_input.delete("1.0", "end")
        self.console_input.insert("1.0", sql.rstrip(";") + ";")
        self.console_input.focus_set()
        self.status_var.set(f"Vista cargada: {view_name}")

    def load_selected_view_into_editor(self) -> None:
        view_name = self.selected_view_name()
        if view_name:
            self.load_view_into_editor(view_name)

    def load_selected_view_into_editor_event(self, event=None) -> str:
        self.load_selected_view_into_editor()
        return "break"

    def run_selected_view(self) -> None:
        view_name = self.selected_view_name()
        if not view_name:
            return
        self.run_sql(f"SELECT * FROM {quote_identifier(view_name)} LIMIT {self.settings.limit}")

    def delete_selected_view(self) -> None:
        view_name = self.selected_view_name()
        if not view_name:
            return
        if not messagebox.askyesno(APP_TITLE, f"Eliminar la vista '{view_name}'?"):
            return
        key = self.workbook_key()
        if key is None:
            return
        store = self.read_views_store()
        workbook_views = store.get(key, {})
        workbook_views.pop(view_name, None)
        if self.workbook is not None:
            try:
                self.workbook.connection.sql(f"DROP VIEW IF EXISTS {quote_identifier(view_name)}")
            except Exception:
                pass
        self.write_views_store(store)
        self.saved_views.pop(view_name, None)
        self.refresh_views()
        self.status_var.set(f"Vista eliminada: {view_name}")
