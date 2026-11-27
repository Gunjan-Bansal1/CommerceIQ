"""
CommerceIQ - Clean In-Process Jupyter Notebook Builder & Executor

Creates structured `.ipynb` files from markdown/code cell specs and executes
every code cell sequentially in an isolated IPython InteractiveShell, capturing
stdout, rich HTML/text DataFrames, and inline Matplotlib PNG figures.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import uuid
from pathlib import Path
from typing import Any

os.environ.setdefault(
    "IPYTHONDIR",
    str(Path(__file__).resolve().parents[2] / ".cache_ipython"),
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from IPython.core.interactiveshell import InteractiveShell


def md_cell(text: str) -> dict[str, Any]:
    lines = text.strip().splitlines(keepends=True)
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "markdown",
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": lines,
    }


def code_cell(code: str) -> dict[str, Any]:
    lines = code.strip().splitlines(keepends=True)
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "outputs": [],
        "source": lines,
    }


def build_and_execute_notebook(
    cells: list[dict[str, Any]],
    output_path: Path,
    working_dir: Path,
) -> Path:
    """Execute code cells in order and save populated `.ipynb` with outputs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    old_cwd = Path.cwd()
    os.chdir(working_dir)

    shell = InteractiveShell()
    captured_displays: list[dict[str, Any]] = []

    def _display(*objs: Any, **kwargs: Any) -> None:
        for obj in objs:
            data: dict[str, Any] = {"text/plain": repr(obj).splitlines(keepends=True)}
            if isinstance(obj, pd.DataFrame):
                data["text/plain"] = obj.to_string().splitlines(keepends=True)
                data["text/html"] = obj.to_html(max_rows=30, max_cols=20).splitlines(keepends=True)
            elif hasattr(obj, "_repr_html_"):
                html = obj._repr_html_()
                if html:
                    data["text/html"] = html.splitlines(keepends=True)
            captured_displays.append(
                {
                    "data": data,
                    "metadata": {},
                    "output_type": "display_data",
                }
            )

    def _capture_open_figures() -> None:
        for fignum in list(plt.get_fignums()):
            fig = plt.figure(fignum)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            captured_displays.append(
                {
                    "data": {
                        "image/png": b64,
                        "text/plain": ["<Figure>"],
                    },
                    "metadata": {},
                    "output_type": "display_data",
                }
            )
            plt.close(fig)

    orig_show = plt.show
    plt.show = lambda *a, **kw: _capture_open_figures()
    shell.user_ns["display"] = _display

    exec_counter = 0
    try:
        for cell in cells:
            if cell["cell_type"] != "code":
                continue
            exec_counter += 1
            captured_displays.clear()
            stdout_buf = io.StringIO()
            code_str = "".join(cell["source"])
            with contextlib.redirect_stdout(stdout_buf):
                res = shell.run_cell(code_str, store_history=False)
            _capture_open_figures()
            if res.error_before_exec or res.error_in_exec:
                err = res.error_before_exec or res.error_in_exec
                raise RuntimeError(f"Notebook cell {exec_counter} failed: {err}")

            outputs: list[dict[str, Any]] = []
            text_out = stdout_buf.getvalue()
            if text_out:
                outputs.append(
                    {
                        "name": "stdout",
                        "output_type": "stream",
                        "text": text_out.splitlines(keepends=True),
                    }
                )
            outputs.extend(captured_displays)
            if res.result is not None:
                res_data: dict[str, Any] = {
                    "text/plain": repr(res.result).splitlines(keepends=True)
                }
                if isinstance(res.result, pd.DataFrame):
                    res_data["text/plain"] = res.result.to_string().splitlines(keepends=True)
                    res_data["text/html"] = res.result.to_html(max_rows=30, max_cols=20).splitlines(keepends=True)
                outputs.append(
                    {
                        "data": res_data,
                        "execution_count": exec_counter,
                        "metadata": {},
                        "output_type": "execute_result",
                    }
                )
            cell["execution_count"] = exec_counter
            cell["outputs"] = outputs
    finally:
        plt.show = orig_show
        plt.close("all")
        os.chdir(old_cwd)

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": ".venv (3.13.3)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.13.3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    output_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
