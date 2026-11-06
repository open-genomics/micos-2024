# -*- coding: utf-8 -*-
"""环境自检（micos doctor）。"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from micos.manifest import TOOL_NAMES


@dataclass
class ToolStatus:
    """外部工具检查结果。"""

    name: str
    found: bool
    path: str | None
    version: str | None


@dataclass
class PathStatus:
    """路径检查结果。"""

    name: str
    path: str | None
    exists: bool
    required: bool


def _tool_version(executable: str) -> str | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else None


def check_tools(names: tuple[str, ...] = TOOL_NAMES) -> list[ToolStatus]:
    """检查工具是否存在并尽量读取版本。"""
    statuses: list[ToolStatus] = []
    for name in names:
        path = shutil.which(name)
        statuses.append(
            ToolStatus(
                name=name,
                found=path is not None,
                path=path,
                version=_tool_version(path) if path else None,
            )
        )
    return statuses


def check_path(name: str, value: str | None, required: bool = False) -> PathStatus:
    """检查数据库或输入路径。"""
    path = Path(value) if value else None
    return PathStatus(
        name=name,
        path=str(path) if path else None,
        exists=path.exists() if path else False,
        required=required,
    )


def build_report(kneaddata_db: str | None, kraken2_db: str | None) -> dict[str, Any]:
    """构建 doctor 报告。"""
    tools = check_tools()
    paths = [
        check_path("KneadData 数据库", kneaddata_db),
        check_path("Kraken2 数据库", kraken2_db),
    ]
    missing_tools = [tool.name for tool in tools if not tool.found]
    invalid_paths = [path.name for path in paths if path.path and not path.exists]
    return {
        "ok": not missing_tools and not invalid_paths,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "tools": [asdict(tool) for tool in tools],
        "paths": [asdict(path) for path in paths],
        "missing_tools": missing_tools,
        "invalid_paths": invalid_paths,
    }


def render_text(report: dict[str, Any]) -> str:
    """渲染人类可读的 doctor 输出。"""
    lines = [
        "MICOS 环境自检",
        f"Python: {report['python_version']}",
        f"平台: {report['platform']}",
        "",
        "外部工具:",
    ]
    for tool in report["tools"]:
        if tool["found"]:
            version = f"  {tool['version']}" if tool["version"] else ""
            lines.append(f"  [OK] {tool['name']}: {tool['path']}{version}")
        else:
            lines.append(f"  [MISSING] {tool['name']}")
    lines.append("")
    lines.append("路径:")
    for path in report["paths"]:
        if not path["path"]:
            lines.append(f"  [SKIP] {path['name']}: 未提供")
        elif path["exists"]:
            lines.append(f"  [OK] {path['name']}: {path['path']}")
        else:
            lines.append(f"  [MISSING] {path['name']}: {path['path']}")
    lines.append("")
    lines.append("结果: " + ("通过" if report["ok"] else "存在缺失项"))
    return "\n".join(lines)


def run_doctor(
    kneaddata_db: str | None = None,
    kraken2_db: str | None = None,
    json_output: bool = False,
) -> int:
    """执行自检并返回进程退出码。"""
    report = build_report(kneaddata_db, kraken2_db)
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 4
