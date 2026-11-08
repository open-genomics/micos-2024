# -*- coding: utf-8 -*-
"""测试运行清单。"""

from __future__ import annotations

import json

from micos.manifest import RunManifest, StageRecord


def test_run_manifest_writes_environment_and_inputs(tmp_path):
    """清单应记录环境、输入文件与阶段状态。"""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "sample_R1.fastq.gz").write_text("r1", encoding="utf-8")
    (input_dir / "sample_R2.fastq.gz").write_text("r2", encoding="utf-8")

    results_dir = tmp_path / "results"
    db = tmp_path / "db"
    db.mkdir()
    manifest = RunManifest.create(
        input_dir=input_dir,
        results_dir=results_dir,
        parameters={"threads": 8},
        kneaddata_db=str(db),
        kraken2_db=None,
    )
    manifest.stages.append(
        StageRecord(
            name="质量控制",
            status="completed",
            started_at="2026-11-06T00:00:00+00:00",
            finished_at="2026-11-06T00:00:01+00:00",
            duration_sec=1.0,
        )
    )
    manifest.status = "completed"
    path = manifest.write()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["run_id"] == manifest.run_id
    assert data["status"] == "completed"
    assert data["parameters"]["threads"] == 8
    assert data["database_paths"]["kneaddata"]["exists"] is True
    assert data["database_paths"]["kraken2"]["exists"] is False
    assert {item["path"] for item in data["input_files"]} == {
        "sample_R1.fastq.gz",
        "sample_R2.fastq.gz",
    }
    assert data["stages"][0]["name"] == "质量控制"
    assert data["environment"]["micos_version"]


def test_git_commit_uses_package_repo_not_caller_cwd(monkeypatch, tmp_path):
    """git_commit 必须固定在包根执行，不能继承用户当前目录的仓库."""
    from pathlib import Path
    import subprocess

    from micos import manifest

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(cmd, 0, stdout="abc123\n", stderr="")

    monkeypatch.setattr(manifest.subprocess, "run", fake_run)
    monkeypatch.chdir(tmp_path)  # 模拟在任意目录运行

    assert manifest._git_commit() == "abc123"
    assert (
        Path(captured["cwd"]).resolve() == Path(manifest.__file__).resolve().parents[1]
    )
