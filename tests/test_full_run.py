# -*- coding: utf-8 -*-
"""测试完整流程编排模块。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from micos import full_run

CallRecord = tuple[Any, ...]
CallHandler = Callable[[CallRecord], None]


def _write_kneaddata_outputs(output_dir: str) -> None:
    kneaddata_dir = Path(output_dir) / "kneaddata"
    kneaddata_dir.mkdir(parents=True, exist_ok=True)
    (kneaddata_dir / "sample_paired_1.fastq").write_text("r1", encoding="utf-8")
    (kneaddata_dir / "sample_paired_2.fastq").write_text("r2", encoding="utf-8")


def _write_biom(output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "feature-table.biom").write_text("biom", encoding="utf-8")


def _stub_pipeline_stages(
    monkeypatch: pytest.MonkeyPatch,
    on_call: CallHandler | None = None,
) -> None:
    """用无副作用 stub 替换各分析阶段."""

    def fake_run_qc(
        input_dir: str,
        output_dir: str,
        threads: int,
        kneaddata_db: str,
        metadata_path: str | None = None,
    ) -> None:
        if on_call:
            on_call(("qc", input_dir, output_dir, threads, kneaddata_db, metadata_path))
        _write_kneaddata_outputs(output_dir)

    def fake_run_taxonomic_profiling(
        input_dir: str,
        output_dir: str,
        threads: int,
        kraken2_db: str,
        confidence: float = 0.1,
        metadata_path: str | None = None,
    ) -> None:
        if on_call:
            on_call(("tax", input_dir, output_dir, threads, kraken2_db, metadata_path))
        _write_biom(output_dir)

    def fake_run_diversity_analysis(input_biom: str, output_dir: str) -> None:
        if on_call:
            on_call(("div", input_biom, output_dir))

    def fake_run_functional_annotation(
        input_dir: str,
        output_dir: str,
        threads: int,
        metadata_path: str | None = None,
    ) -> None:
        if on_call:
            on_call(("func", input_dir, output_dir, threads, metadata_path))

    def fake_run_summarize(results_dir: str, output_file: str) -> None:
        if on_call:
            on_call(("summary", results_dir, output_file))

    monkeypatch.setattr(full_run, "run_qc", fake_run_qc)
    monkeypatch.setattr(
        full_run, "run_taxonomic_profiling", fake_run_taxonomic_profiling
    )
    monkeypatch.setattr(full_run, "run_diversity_analysis", fake_run_diversity_analysis)
    monkeypatch.setattr(
        full_run, "run_functional_annotation", fake_run_functional_annotation
    )
    monkeypatch.setattr(full_run, "run_summarize", fake_run_summarize)


def test_run_full_pipeline_uses_named_output_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """full-run 应输出到新的命名目录。"""
    calls: list[CallRecord] = []
    _stub_pipeline_stages(monkeypatch, calls.append)

    results_dir = tmp_path / "results"
    full_run.run_full_pipeline(
        input_dir=str(tmp_path / "input"),
        results_dir=str(results_dir),
        threads=16,
        kneaddata_db="/db/kneaddata",
        kraken2_db="/db/kraken2",
    )

    assert calls == [
        (
            "qc",
            str(tmp_path / "input"),
            str(results_dir / "quality_control"),
            16,
            "/db/kneaddata",
            None,
        ),
        (
            "tax",
            str(results_dir / "quality_control" / "kneaddata"),
            str(results_dir / "taxonomic_profiling"),
            16,
            "/db/kraken2",
            None,
        ),
        (
            "div",
            str(results_dir / "taxonomic_profiling" / "feature-table.biom"),
            str(results_dir / "diversity_analysis"),
        ),
        (
            "func",
            str(results_dir / "quality_control" / "kneaddata"),
            str(results_dir / "functional_annotation"),
            16,
            None,
        ),
        ("summary", str(results_dir), str(results_dir / "micos_summary_report.html")),
    ]


def test_run_full_pipeline_passes_metadata_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """full-run 应将 metadata_path 传递给各模块。"""
    captured: dict[str, str | None] = {}

    def on_call(entry: CallRecord) -> None:
        name, *rest = entry
        if name in {"qc", "tax", "func"}:
            captured[f"{name}_metadata"] = rest[-1]

    _stub_pipeline_stages(monkeypatch, on_call)

    full_run.run_full_pipeline(
        input_dir=str(tmp_path / "input"),
        results_dir=str(tmp_path / "results"),
        threads=4,
        kneaddata_db="/db/kneaddata",
        kraken2_db="/db/kraken2",
        metadata_path="config/samples.tsv",
    )

    assert captured == {
        "qc_metadata": "config/samples.tsv",
        "tax_metadata": "config/samples.tsv",
        "func_metadata": "config/samples.tsv",
    }


@pytest.mark.parametrize(
    "skip_flag,skipped_call",
    [
        ("skip_qc", "qc"),
        ("skip_taxonomy", "tax"),
        ("skip_functional", "func"),
        ("skip_diversity", "div"),
    ],
)
def test_run_full_pipeline_skips_selected_stage(
    skip_flag: str,
    skipped_call: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """每个 skip 选项应跳过对应阶段，其余阶段正常执行，summary 始终执行。"""
    called: list[str] = []
    _stub_pipeline_stages(monkeypatch, lambda entry: called.append(entry[0]))

    results_dir = tmp_path / "results"
    if skip_flag == "skip_taxonomy":
        tax_dir = results_dir / "taxonomic_profiling"
        tax_dir.mkdir(parents=True, exist_ok=True)
        (tax_dir / "feature-table.biom").write_text("biom", encoding="utf-8")

    skip_kwargs = {
        "skip_qc": False,
        "skip_taxonomy": False,
        "skip_functional": False,
        "skip_diversity": False,
        skip_flag: True,
    }

    full_run.run_full_pipeline(
        input_dir=str(tmp_path / "input"),
        results_dir=str(results_dir),
        threads=4,
        kneaddata_db=None if skip_flag == "skip_qc" else "/db/kneaddata",
        kraken2_db=None if skip_flag == "skip_taxonomy" else "/db/kraken2",
        **skip_kwargs,
    )

    assert skipped_call not in called
    assert "summary" in called


def test_run_full_pipeline_writes_run_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """完整流程应写入 run_manifest.json 并记录阶段。"""
    _stub_pipeline_stages(monkeypatch)

    results_dir = tmp_path / "results"
    full_run.run_full_pipeline(
        input_dir=str(tmp_path / "input"),
        results_dir=str(results_dir),
        threads=4,
        kneaddata_db="/db/kneaddata",
        kraken2_db="/db/kraken2",
    )

    manifest_path = results_dir / "run_manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    assert data["parameters"]["threads"] == 4
    assert [stage["name"] for stage in data["stages"]] == [
        "质量控制",
        "物种分类",
        "多样性分析",
        "功能注释",
        "结果汇总",
    ]
    assert all(stage["status"] == "completed" for stage in data["stages"])

def test_run_full_pipeline_marks_manifest_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """阶段失败时 manifest 应记录 failed 状态并保留错误。"""
    def failing_qc(**kwargs):
        raise RuntimeError("fastqc 未安装")

    monkeypatch.setattr(full_run, "run_qc", failing_qc)

    results_dir = tmp_path / "results"
    with pytest.raises(RuntimeError, match="fastqc"):
        full_run.run_full_pipeline(
            input_dir=str(tmp_path / "input"),
            results_dir=str(results_dir),
            threads=4,
            kneaddata_db="/db/kneaddata",
            kraken2_db="/db/kraken2",
        )

    data = json.loads((results_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert data["status"] == "failed"
    assert data["stages"][0]["name"] == "质量控制"
    assert data["stages"][0]["status"] == "failed"
    assert "fastqc" in data["stages"][0]["error"]
