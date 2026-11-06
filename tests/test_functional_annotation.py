# -*- coding: utf-8 -*-
"""测试功能注释模块（命令拼装层）。"""

from pathlib import Path

import pytest

from micos import functional_annotation
from micos.errors import NoSamplesError


def test_run_functional_annotation_assembles_humann_command(tmp_path, monkeypatch):
    """run_functional_annotation 应合并 reads 并拼装 HUMAnN 命令."""
    commands = []

    def fake_run(cmd):
        commands.append(list(cmd))

    monkeypatch.setattr(functional_annotation, "run_command_live", fake_run)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "sample001_paired_1.fastq").write_text("r1")
    (input_dir / "sample001_paired_2.fastq").write_text("r2")

    output_dir = tmp_path / "output"
    functional_annotation.run_functional_annotation(
        input_dir=input_dir,
        output_dir=output_dir,
        threads=8,
    )

    assert len(commands) == 1
    humann_cmd = commands[0]
    assert humann_cmd[0] == "humann"
    assert "--input" in humann_cmd
    assert str(output_dir) in humann_cmd
    assert humann_cmd[humann_cmd.index("--threads") + 1] == "8"
    assert humann_cmd[humann_cmd.index("--output-basename") + 1] == "sample001"

    # 临时输入目录应被清理
    assert not (output_dir / "temp_humann_input").exists()


def test_run_functional_annotation_fails_when_no_samples(tmp_path, monkeypatch):
    """无样本时应 fail-closed，不调用任何命令."""
    commands = []
    monkeypatch.setattr(
        functional_annotation,
        "run_command_live",
        lambda cmd: commands.append(list(cmd)),
    )

    input_dir = tmp_path / "empty"
    input_dir.mkdir()
    output_dir = tmp_path / "output"

    with pytest.raises(NoSamplesError, match="未找到"):
        functional_annotation.run_functional_annotation(
            input_dir=input_dir,
            output_dir=output_dir,
            threads=4,
        )

    assert commands == []


def test_run_functional_annotation_passes_metadata_path(tmp_path, monkeypatch):
    """run_functional_annotation 应将 metadata_path 转为 Path 传给 Sample.discover_cleaned."""
    captured = {}

    class FakeSample:
        @staticmethod
        def discover_cleaned(
            input_dir,
            pattern="*_paired_1.fastq",
            metadata_path=None,
            sample_id_column="sample-id",
        ):
            captured["metadata_path"] = metadata_path
            return []

    monkeypatch.setattr(functional_annotation, "Sample", FakeSample)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    with pytest.raises(NoSamplesError):
        functional_annotation.run_functional_annotation(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
            threads=4,
            metadata_path="config/samples.tsv",
        )

    assert captured["metadata_path"] == Path("config/samples.tsv")
