from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

import customtkinter as ctk

from config import Settings
from core.ai_engine import build_llm_client
from core.sql_engine import SQLEngine
from core.er_engine import EREngine
from core.normalization_engine import NormalizationEngine
from core.code_engine import CodeEngine
from db.repository import Repository
from utils.json_utils import safe_json_dumps
from ui.widgets import (
    make_labeled_text,
    clear_textbox,
    get_textbox,
    set_textbox,
    build_result_table,
    fill_result_table,
)


class AppGUI:
    """Main GUI application with tabs and persistence."""

    def __init__(self, settings: Settings, repo: Repository) -> None:
        self.settings = settings
        self.repo = repo

        self.llm = build_llm_client(settings)
        self.sql_engine = SQLEngine(self.llm)
        self.er_engine = EREngine()
        self.norm_engine = NormalizationEngine()
        self.code_engine = CodeEngine(self.llm)

        self.current_project_id: int | None = None

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("IS Student AI Assistant")
        self.root.geometry("1200x800")
        self.root.minsize(1100, 720)

        self._build_layout()
        self._load_projects_initial()

    def run(self) -> None:
        """Start Tk main loop."""
        self.root.mainloop()

    # ---------------- Layout ----------------

    def _build_layout(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Left panel: projects + history list
        self.left = ctk.CTkFrame(self.root, width=320)
        self.left.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)
        self.left.grid_rowconfigure(3, weight=1)
        self.left.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(self.left, text="Projects", font=ctk.CTkFont(size=18, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))

        # Project list (tk.Listbox inside CTkFrame)
        self.project_list = tk.Listbox(self.left, height=8)
        self.project_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        self.project_list.bind("<<ListboxSelect>>", self._on_project_select)

        btn_row = ctk.CTkFrame(self.left)
        btn_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_new_proj = ctk.CTkButton(btn_row, text="New", command=self._new_project)
        self.btn_ren_proj = ctk.CTkButton(btn_row, text="Rename", command=self._rename_project)
        self.btn_del_proj = ctk.CTkButton(btn_row, text="Delete", command=self._delete_project)
        self.btn_new_proj.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.btn_ren_proj.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.btn_del_proj.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        hist_lab = ctk.CTkLabel(self.left, text="History (Artifacts)", font=ctk.CTkFont(size=16, weight="bold"))
        hist_lab.grid(row=3, column=0, sticky="w", padx=10, pady=(5, 0))

        self.artifact_list = tk.Listbox(self.left)
        self.artifact_list.grid(row=4, column=0, sticky="nsew", padx=10, pady=8)
        self.left.grid_rowconfigure(4, weight=1)

        hist_btn_row = ctk.CTkFrame(self.left)
        hist_btn_row.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 10))
        hist_btn_row.grid_columnconfigure((0, 1), weight=1)

        self.btn_load_art = ctk.CTkButton(hist_btn_row, text="Load to tab", command=self._load_artifact_to_tab)
        self.btn_refresh_hist = ctk.CTkButton(hist_btn_row, text="Refresh", command=self._refresh_history)
        self.btn_load_art.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.btn_refresh_hist.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        # Right panel: tabs
        self.right = ctk.CTkFrame(self.root)
        self.right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right.grid_rowconfigure(0, weight=1)
        self.right.grid_columnconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(self.right)
        self.tabs.grid(row=0, column=0, sticky="nsew")

        self.tab_sql = self.tabs.add("SQL Lab")
        self.tab_er = self.tabs.add("ER Studio")
        self.tab_norm = self.tabs.add("Normalization")
        self.tab_code = self.tabs.add("Code Explainer")
        self.tab_hist = self.tabs.add("History/Projects")

        self._build_sql_tab()
        self._build_er_tab()
        self._build_norm_tab()
        self._build_code_tab()
        self._build_history_tab_info()

    # ---------------- SQL Lab tab ----------------

    def _build_sql_tab(self) -> None:
        self.tab_sql.grid_columnconfigure((0, 1), weight=1)
        self.tab_sql.grid_rowconfigure(3, weight=1)

        lab1, self.sql_ddl = make_labeled_text(self.tab_sql, "Schema/DDL", height=140)
        lab2, self.sql_task = make_labeled_text(self.tab_sql, "Task", height=90)
        lab3, self.sql_output = make_labeled_text(self.tab_sql, "Output", height=160)

        lab1.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.sql_ddl.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        lab2.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 0))
        self.sql_task.grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 10))

        btn_row = ctk.CTkFrame(self.tab_sql)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        btn_row.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        self.btn_sql_gen = ctk.CTkButton(btn_row, text="Generate SQL", command=self._sql_generate)
        self.btn_sql_explain = ctk.CTkButton(btn_row, text="Explain", command=self._sql_explain)
        self.btn_sql_opt = ctk.CTkButton(btn_row, text="Optimize", command=self._sql_optimize)
        self.btn_sql_run = ctk.CTkButton(btn_row, text="Run in SQLite", command=self._sql_run)
        self.btn_sql_clear = ctk.CTkButton(btn_row, text="Clear", command=self._sql_clear)
        self.btn_sql_explain_err = ctk.CTkButton(btn_row, text="Explain error", command=self._sql_explain_error)

        self.btn_sql_gen.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.btn_sql_explain.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.btn_sql_opt.grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        self.btn_sql_run.grid(row=0, column=3, padx=4, pady=4, sticky="ew")
        self.btn_sql_clear.grid(row=0, column=4, padx=4, pady=4, sticky="ew")
        self.btn_sql_explain_err.grid(row=0, column=5, padx=4, pady=4, sticky="ew")

        lab3.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        self.sql_output.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        self.tab_sql.grid_rowconfigure(4, weight=1)

        # Result table
        table_frame = ctk.CTkFrame(self.tab_sql)
        table_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.sql_table = build_result_table(table_frame)

        self.last_sql_error_text = ""

    def _sql_clear(self) -> None:
        clear_textbox(self.sql_output)
        fill_result_table(self.sql_table, [], [])
        self.last_sql_error_text = ""

    def _sql_generate(self) -> None:
        ddl = get_textbox(self.sql_ddl)
        task = get_textbox(self.sql_task)
        res = self.sql_engine.generate_sql(ddl=ddl, task=task)

        output = []
        output.append("=== Generated SQL ===")
        output.append(res.sql)
        output.append("\n=== Explanation ===")
        output.append(res.explanation)
        if res.warnings:
            output.append("\n=== Warnings ===")
            output.extend([f"- {w}" for w in res.warnings])

        set_textbox(self.sql_output, "\n".join(output))
        fill_result_table(self.sql_table, [], [])

        self._save_artifact("sql_lab", input_text=f"DDL:\n{ddl}\n\nTASK:\n{task}", output_text="\n".join(output),
                            meta={"action": "generate_sql"})

    def _sql_explain(self) -> None:
        sql_text = get_textbox(self.sql_output)
        if "=== Generated SQL ===" in sql_text:
            # Try to extract the SQL block from output
            sql_text = self._extract_between(sql_text, "=== Generated SQL ===", "=== Explanation ===") or sql_text

        res = self.sql_engine.explain_sql(sql_text)
        out = []
        out.append("=== Explanation ===")
        out.append(res.explanation)
        if res.issues:
            out.append("\n=== Issues ===")
            out.extend([f"- {x}" for x in res.issues])
        if res.optimized_sql:
            out.append("\n=== Optimized SQL ===")
            out.append(res.optimized_sql)

        set_textbox(self.sql_output, "\n".join(out))
        self._save_artifact("sql_lab", input_text=sql_text, output_text="\n".join(out),
                            meta={"action": "explain"})

    def _sql_optimize(self) -> None:
        sql_text = get_textbox(self.sql_output)
        if "=== Generated SQL ===" in sql_text:
            sql_text = self._extract_between(sql_text, "=== Generated SQL ===", "=== Explanation ===") or sql_text
        optimized = self.sql_engine.optimize_sql(sql_text)
        set_textbox(self.sql_output, optimized)

        self._save_artifact("sql_lab", input_text=sql_text, output_text=optimized,
                            meta={"action": "optimize"})

    def _sql_run(self) -> None:
        ddl = get_textbox(self.sql_ddl)

        # If output textbox contains structured sections, try get SQL from it; else use raw content
        sql_text = get_textbox(self.sql_output)
        if "=== Generated SQL ===" in sql_text:
            extracted = self._extract_between(sql_text, "=== Generated SQL ===", "=== Explanation ===")
            if extracted:
                sql_text = extracted.strip()

        res = self.sql_engine.run_in_sqlite(ddl=ddl, sql_text=sql_text, max_rows=100)
        self.last_sql_error_text = res.error_text

        if res.ok:
            set_textbox(self.sql_output, res.output_text)
            fill_result_table(self.sql_table, res.headers, res.rows)
            self._save_run(sql_text=sql_text, status="ok", error_text="", result={"headers": res.headers, "rows": res.rows})
            self._save_artifact("sql_lab", input_text=f"DDL:\n{ddl}\n\nSQL:\n{sql_text}",
                                output_text=res.output_text, meta={"action": "run", "ok": True})
        else:
            out = f"{res.output_text}\n\nERROR:\n{res.error_text}"
            set_textbox(self.sql_output, out)
            fill_result_table(self.sql_table, [], [])
            self._save_run(sql_text=sql_text, status="error", error_text=res.error_text, result={})
            self._save_artifact("sql_lab", input_text=f"DDL:\n{ddl}\n\nSQL:\n{sql_text}",
                                output_text=out, meta={"action": "run", "ok": False})

    def _sql_explain_error(self) -> None:
        if not self.last_sql_error_text:
            messagebox.showinfo("Explain error", "No last SQLite error to explain.")
            return
        sql_text = get_textbox(self.sql_output)
        prompt = f"SQLite error:\n{self.last_sql_error_text}\n\nContext:\n{sql_text}"
        res = self.code_engine.explain(prompt)
        out = []
        out.append("=== Error explanation ===")
        out.append(res.explanation)
        if res.issues:
            out.append("\n=== Suggestions ===")
            out.extend([f"- {x}" for x in res.issues])
        set_textbox(self.sql_output, "\n".join(out))

        self._save_artifact("sql_lab", input_text=prompt, output_text="\n".join(out),
                            meta={"action": "explain_error"})

    # ---------------- ER Studio tab ----------------

    def _build_er_tab(self) -> None:
        self.tab_er.grid_columnconfigure((0, 1), weight=1)
        self.tab_er.grid_rowconfigure(1, weight=1)
        self.tab_er.grid_rowconfigure(3, weight=1)

        lab_in, self.er_ddl = make_labeled_text(self.tab_er, "DDL input", height=220)
        lab_out, self.er_mermaid = make_labeled_text(self.tab_er, "Mermaid Output", height=260)

        lab_in.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        self.er_ddl.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

        btn_row = ctk.CTkFrame(self.tab_er)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_er_build = ctk.CTkButton(btn_row, text="Build ER (Mermaid)", command=self._er_build)
        self.btn_er_export = ctk.CTkButton(btn_row, text="Export Mermaid", command=self._er_export)
        self.btn_er_clear = ctk.CTkButton(btn_row, text="Clear", command=lambda: (clear_textbox(self.er_mermaid),))
        self.btn_er_build.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.btn_er_export.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.btn_er_clear.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        lab_out.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        self.er_mermaid.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        self.tab_er.grid_rowconfigure(4, weight=1)

    def _er_build(self) -> None:
        ddl = get_textbox(self.er_ddl)
        res = self.er_engine.build_mermaid(ddl)
        set_textbox(self.er_mermaid, res.mermaid)

        self._save_artifact("er_studio", input_text=ddl, output_text=res.mermaid,
                            meta={"tables": res.tables, "relationships": res.relationships})

    def _er_export(self) -> None:
        mermaid = get_textbox(self.er_mermaid)
        if not mermaid.strip():
            messagebox.showinfo("Export", "Mermaid output is empty.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(mermaid)
        messagebox.showinfo("Export", "Mermaid diagram copied to clipboard.")

    # ---------------- Normalization tab ----------------

    def _build_norm_tab(self) -> None:
        self.tab_norm.grid_columnconfigure((0, 1), weight=1)
        self.tab_norm.grid_rowconfigure(3, weight=1)

        lab_r, self.norm_rel = make_labeled_text(self.tab_norm, "Relation schema: R(A,B,C,...)", height=80)
        lab_f, self.norm_fds = make_labeled_text(self.tab_norm, "Functional dependencies: A->B, (A,C)->D ...", height=120)
        lab_rep, self.norm_report = make_labeled_text(self.tab_norm, "Report", height=320)

        lab_r.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.norm_rel.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        lab_f.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 0))
        self.norm_fds.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10))

        btn_row = ctk.CTkFrame(self.tab_norm)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        btn_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.btn_norm_keys = ctk.CTkButton(btn_row, text="Find Candidate Keys", command=self._norm_keys)
        self.btn_norm_check = ctk.CTkButton(btn_row, text="Check NF", command=self._norm_check)
        self.btn_norm_decomp = ctk.CTkButton(btn_row, text="Decompose", command=self._norm_decompose)
        self.btn_norm_clear = ctk.CTkButton(btn_row, text="Clear", command=lambda: clear_textbox(self.norm_report))
        self.btn_norm_keys.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.btn_norm_check.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.btn_norm_decomp.grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        self.btn_norm_clear.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        lab_rep.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        self.norm_report.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        self.tab_norm.grid_rowconfigure(4, weight=1)

    def _norm_keys(self) -> None:
        rel = get_textbox(self.norm_rel)
        fds = get_textbox(self.norm_fds)
        keys = self.norm_engine.find_keys_only(rel, fds)
        out = "Candidate keys:\n" + ("\n".join([f"- {k}" for k in keys]) if keys else "None")
        set_textbox(self.norm_report, out)

        self._save_artifact("normalization", input_text=f"{rel}\n{fds}", output_text=out,
                            meta={"action": "keys", "keys": keys})

    def _norm_check(self) -> None:
        rel = get_textbox(self.norm_rel)
        fds = get_textbox(self.norm_fds)
        rep = self.norm_engine.analyze(rel, fds)

        out = []
        out.append(rep.nf_report)
        out.append("\n--- Steps ---")
        out.extend(rep.steps)

        set_textbox(self.norm_report, "\n".join(out))
        self._save_artifact("normalization", input_text=f"{rel}\n{fds}", output_text="\n".join(out),
                            meta={"action": "check_nf", "meta": rep.meta})

    def _norm_decompose(self) -> None:
        rel = get_textbox(self.norm_rel)
        fds = get_textbox(self.norm_fds)
        rep = self.norm_engine.analyze(rel, fds)

        out = []
        out.append(rep.nf_report)
        out.append("\n--- Decomposition ---")
        out.append(rep.decomposition)
        out.append("\n--- Steps ---")
        out.extend(rep.steps)

        set_textbox(self.norm_report, "\n".join(out))
        self._save_artifact("normalization", input_text=f"{rel}\n{fds}", output_text="\n".join(out),
                            meta={"action": "decompose_bcnf", "meta": rep.meta})

    # ---------------- Code Explainer tab ----------------

    def _build_code_tab(self) -> None:
        self.tab_code.grid_columnconfigure((0, 1), weight=1)
        self.tab_code.grid_rowconfigure(1, weight=1)
        self.tab_code.grid_rowconfigure(4, weight=1)

        lab_in, self.code_input = make_labeled_text(self.tab_code, "Code input (SQL/Python)", height=260)
        lab_analysis, self.code_analysis = make_labeled_text(self.tab_code, "Analysis", height=200)
        lab_fix, self.code_corrected = make_labeled_text(self.tab_code, "Corrected code", height=220)

        lab_in.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        self.code_input.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

        btn_row = ctk.CTkFrame(self.tab_code)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        btn_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.btn_code_explain = ctk.CTkButton(btn_row, text="Explain", command=self._code_explain)
        self.btn_code_fix = ctk.CTkButton(btn_row, text="Fix", command=self._code_fix)
        self.btn_code_comments = ctk.CTkButton(btn_row, text="Add comments", command=self._code_comments)
        self.btn_code_clear = ctk.CTkButton(btn_row, text="Clear", command=self._code_clear)
        self.btn_code_explain.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.btn_code_fix.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.btn_code_comments.grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        self.btn_code_clear.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        lab_analysis.grid(row=3, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.code_analysis.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))

        lab_fix.grid(row=3, column=1, sticky="ew", padx=10, pady=(10, 0))
        self.code_corrected.grid(row=4, column=1, sticky="nsew", padx=10, pady=(0, 10))

    def _code_clear(self) -> None:
        clear_textbox(self.code_analysis)
        clear_textbox(self.code_corrected)

    def _code_explain(self) -> None:
        code = get_textbox(self.code_input)
        res = self.code_engine.explain(code)
        analysis = self._format_code_result(res)
        set_textbox(self.code_analysis, analysis)
        set_textbox(self.code_corrected, res.corrected_code)

        self._save_artifact("code_explainer", input_text=code, output_text=analysis + "\n\n---\n\n" + res.corrected_code,
                            meta={"action": "explain", "language": res.language, "issues": res.issues})

    def _code_fix(self) -> None:
        code = get_textbox(self.code_input)
        res = self.code_engine.fix(code)
        analysis = self._format_code_result(res)
        set_textbox(self.code_analysis, analysis)
        set_textbox(self.code_corrected, res.corrected_code)

        self._save_artifact("code_explainer", input_text=code, output_text=analysis + "\n\n---\n\n" + res.corrected_code,
                            meta={"action": "fix", "language": res.language, "issues": res.issues})

    def _code_comments(self) -> None:
        code = get_textbox(self.code_input)
        res = self.code_engine.add_comments(code)
        analysis = self._format_code_result(res)
        set_textbox(self.code_analysis, analysis)
        set_textbox(self.code_corrected, res.corrected_code)

        self._save_artifact("code_explainer", input_text=code, output_text=analysis + "\n\n---\n\n" + res.corrected_code,
                            meta={"action": "add_comments", "language": res.language, "issues": res.issues})

    def _format_code_result(self, res) -> str:
        out = []
        out.append(f"Language: {res.language}")
        out.append("")
        out.append(res.explanation)
        if res.issues:
            out.append("\nIssues:")
            out.extend([f"- {x}" for x in res.issues])
        return "\n".join(out)

    # ---------------- History/Projects tab (info panel) ----------------

    def _build_history_tab_info(self) -> None:
        self.tab_hist.grid_columnconfigure(0, weight=1)
        self.tab_hist.grid_rowconfigure(1, weight=1)

        info = ctk.CTkLabel(
            self.tab_hist,
            text=(
                "Projects and history are managed in the left panel.\n\n"
                "• Create/Rename/Delete project\n"
                "• Select a project to view artifacts history\n"
                "• Use 'Load to tab' to restore saved inputs/outputs into the right tab\n\n"
                "This tab is informational by design."
            ),
            justify="left"
        )
        info.grid(row=0, column=0, sticky="nw", padx=15, pady=15)

    # ---------------- Persistence helpers ----------------

    def _ensure_project(self) -> int:
        """Ensure there is a selected project; create default if needed."""
        if self.current_project_id is not None:
            return self.current_project_id

        projects = self.repo.list_projects()
        if projects:
            self.current_project_id = projects[0].id
            self._refresh_history()
            return self.current_project_id

        # Auto-create default project
        p = self.repo.create_project("Default Project")
        self.current_project_id = p.id
        self._load_projects_initial(select_project_id=p.id)
        return p.id

    def _save_artifact(self, module: str, input_text: str, output_text: str, meta: dict | None = None) -> None:
        """Save artifact in DB for current project."""
        pid = self._ensure_project()
        self.repo.add_artifact(project_id=pid, module=module, input_text=input_text, output_text=output_text, meta=meta or {})
        self._refresh_history()

    def _save_run(self, sql_text: str, status: str, error_text: str, result: dict) -> None:
        """Save SQL run record."""
        pid = self._ensure_project()
        self.repo.add_run(project_id=pid, sql_text=sql_text, status=status, error_text=error_text, result=result)

    # ---------------- Projects UI ----------------

    def _load_projects_initial(self, select_project_id: int | None = None) -> None:
        """Populate project list and select a project."""
        self.project_list.delete(0, tk.END)
        self._projects_cache = self.repo.list_projects()

        select_index = 0
        for i, p in enumerate(self._projects_cache):
            self.project_list.insert(tk.END, f"{p.id}: {p.name}")
            if select_project_id is not None and p.id == select_project_id:
                select_index = i

        if self._projects_cache:
            self.project_list.selection_clear(0, tk.END)
            self.project_list.selection_set(select_index)
            self.project_list.activate(select_index)
            self.current_project_id = self._projects_cache[select_index].id
            self._refresh_history()
        else:
            self.current_project_id = None
            self._refresh_history()

    def _on_project_select(self, event=None) -> None:
        sel = self.project_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self._projects_cache):
            return
        self.current_project_id = self._projects_cache[idx].id
        self._refresh_history()

    def _new_project(self) -> None:
        name = simpledialog.askstring("New project", "Project name:")
        if not name:
            return
        try:
            p = self.repo.create_project(name.strip())
            self._load_projects_initial(select_project_id=p.id)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _rename_project(self) -> None:
        pid = self._ensure_project()
        p = self.repo.get_project(pid)
        if not p:
            return
        new_name = simpledialog.askstring("Rename project", "New name:", initialvalue=p.name)
        if not new_name:
            return
        try:
            self.repo.rename_project(pid, new_name.strip())
            self._load_projects_initial(select_project_id=pid)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_project(self) -> None:
        pid = self._ensure_project()
        p = self.repo.get_project(pid)
        if not p:
            return
        if not messagebox.askyesno("Delete project", f"Delete project '{p.name}' and all its history?"):
            return
        try:
            self.repo.delete_project(pid)
            self._load_projects_initial()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------- History UI ----------------

    def _refresh_history(self) -> None:
        """Refresh artifact list for current project."""
        self.artifact_list.delete(0, tk.END)
        self._artifact_cache = []
        if self.current_project_id is None:
            return
        arts = self.repo.list_artifacts(project_id=self.current_project_id, limit=300)
        self._artifact_cache = arts

        for a in arts:
            self.artifact_list.insert(
                tk.END,
                f"{a.id} | {a.module} | {a.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    def _load_artifact_to_tab(self) -> None:
        """Load selected artifact into the corresponding tab."""
        sel = self.artifact_list.curselection()
        if not sel:
            messagebox.showinfo("Load", "Select an artifact first.")
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self._artifact_cache):
            return
        a = self._artifact_cache[idx]

        if a.module == "sql_lab":
            # Try to restore DDL/Task/SQL based on saved input_text patterns
            inp = a.input_text or ""
            if "DDL:" in inp and "TASK:" in inp:
                ddl = self._extract_after(inp, "DDL:") or ""
                task = self._extract_after(inp, "TASK:") or ""
                set_textbox(self.sql_ddl, ddl.strip())
                set_textbox(self.sql_task, task.strip())
                set_textbox(self.sql_output, a.output_text or "")
            elif "DDL:" in inp and "SQL:" in inp:
                ddl = self._extract_after(inp, "DDL:") or ""
                sql = self._extract_after(inp, "SQL:") or ""
                set_textbox(self.sql_ddl, ddl.strip())
                set_textbox(self.sql_output, sql.strip())
            else:
                set_textbox(self.sql_output, a.output_text or "")
            self.tabs.set("SQL Lab")

        elif a.module == "er_studio":
            set_textbox(self.er_ddl, a.input_text or "")
            set_textbox(self.er_mermaid, a.output_text or "")
            self.tabs.set("ER Studio")

        elif a.module == "normalization":
            # Input is typically "R(...)\nFDs"
            inp = (a.input_text or "").splitlines()
            if inp:
                set_textbox(self.norm_rel, inp[0])
                set_textbox(self.norm_fds, "\n".join(inp[1:]))
            set_textbox(self.norm_report, a.output_text or "")
            self.tabs.set("Normalization")

        elif a.module == "code_explainer":
            set_textbox(self.code_input, a.input_text or "")
            # Output stored as analysis + corrected code separated by "---"
            out = a.output_text or ""
            if "\n---\n\n" in out:
                analysis, corrected = out.split("\n---\n\n", 1)
                set_textbox(self.code_analysis, analysis)
                set_textbox(self.code_corrected, corrected)
            else:
                set_textbox(self.code_analysis, out)
            self.tabs.set("Code Explainer")

        else:
            messagebox.showinfo("Load", f"Unknown module: {a.module}")

    # ---------------- Small text helpers ----------------

    def _extract_between(self, text: str, start_marker: str, end_marker: str) -> str | None:
        """Extract substring between two markers."""
        s = text
        a = s.find(start_marker)
        if a < 0:
            return None
        a += len(start_marker)
        b = s.find(end_marker, a)
        if b < 0:
            return None
        return s[a:b].strip()

    def _extract_after(self, text: str, marker: str) -> str | None:
        """Extract everything after marker."""
        i = text.find(marker)
        if i < 0:
            return None
        return text[i + len(marker):].strip()