# -*- coding: utf-8 -*-
"""运行清单（run manifest）与执行环境采集。"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from micos import __version__

MANIFEST_NAME = "run_manifest.json"
TOOL_NAMES = (
    "fastqc",
    "kneaddata",
    "kraken2",
    "kraken-biom",
    "ktImportTaxonomy",
    "qiime",
    "humann",
)
FASTQ_PATTERNS = ("*.fastq", "*.fastq.gz", "*.fq", "*.fq.gz")


def utc_now() -> str:
    """返回秒级 UTC ISO 时间戳。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run_id() -> str:
    """生成可按时间排序的 run id。"""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _tool_version(executable: str) -> str | None:
    """读取工具版本；失败或超时返回 None。"""
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


def collect_tool_versions() -> dict[str, dict[str, str | bool | None]]:
    """采集已知外部工具的路径与版本。"""
    tools: dict[str, dict[str, str | bool | None]] = {}
    for name in TOOL_NAMES:
        path = shutil.which(name)
        tools[name] = {
            "found": path is not None,
            "path": path,
            "version": _tool_version(path) if path else None,
        }
    return tools


def _git_commit() -> str | None:
    """读取 MICOS 包所在仓库的 commit；不在 git 仓库中时返回 None。

    必须显式指定 cwd：继承调用者目录会把用户分析项目的 commit 误记成
    MICOS 代码版本。安装为 wheel 时包根通常没有 .git，返回 None 是正确结果。
    """
    repo_root = Path(__file__).resolve().parents[1]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and commit else None


def collect_environment() -> dict[str, Any]:
    """采集足以复现一次运行的软件环境信息。"""
    return {
        "micos_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _git_commit(),
        "tools": collect_tool_versions(),
    }


def collect_input_files(input_dir: str | Path) -> list[dict[str, Any]]:
    """记录输入 FASTQ 的相对路径、大小和 mtime。"""
    root = Path(input_dir)
    if not root.exists():
        return []

    records: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for pattern in FASTQ_PATTERNS:
        for path in sorted(root.glob(pattern)):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            stat = path.stat()
            records.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
    return records


def collect_database_paths(
    kneaddata_db: str | None, kraken2_db: str | None
) -> dict[str, dict[str, Any]]:
    """记录数据库路径是否存在。"""
    result: dict[str, dict[str, Any]] = {}
    for name, value in (("kneaddata", kneaddata_db), ("kraken2", kraken2_db)):
        path = Path(value) if value else None
        result[name] = {
            "path": str(path) if path else None,
            "exists": path.exists() if path else False,
        }
    return result


@dataclass
class StageRecord:
    """单个阶段的执行记录。"""

    name: str
    status: str
    started_at: str
    finished_at: str | None = None
    duration_sec: float | None = None
    error: str | None = None


@dataclass
class RunManifest:
    """一次完整运行的清单。"""

    run_id: str
    started_at: str
    input_dir: str
    results_dir: str
    parameters: dict[str, Any]
    environment: dict[str, Any]
    database_paths: dict[str, dict[str, Any]]
    input_files: list[dict[str, Any]]
    status: str = "running"
    finished_at: str | None = None
    stages: list[StageRecord] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        input_dir: str | Path,
        results_dir: str | Path,
        parameters: dict[str, Any],
        kneaddata_db: str | None,
        kraken2_db: str | None,
    ) -> "RunManifest":
        """创建运行清单并采集环境。"""
        return cls(
            run_id=new_run_id(),
            started_at=utc_now(),
            input_dir=str(input_dir),
            results_dir=str(results_dir),
            parameters=parameters,
            environment=collect_environment(),
            database_paths=collect_database_paths(kneaddata_db, kraken2_db),
            input_files=collect_input_files(input_dir),
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为可 JSON 序列化的字典。"""
        data = asdict(self)
        data["manifest_path"] = str(Path(self.results_dir) / MANIFEST_NAME)
        return data

    def write(self) -> Path:
        """原子写入 results/<run_manifest.json>。"""
        path = Path(self.results_dir) / MANIFEST_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(path)
        return path
