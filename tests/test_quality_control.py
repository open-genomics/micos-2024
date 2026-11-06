# -*- coding: utf-8 -*-
"""测试质量控制模块（命令拼装层）。"""

from pathlib import Path

import pytest

from micos import quality_control
from micos.errors import NoSamplesError


def test_run_qc_assembles_fastqc_and_kneaddata_commands(tmp_path, monkeypatch):
    """run_qc 应拼装 FastQC 与 KneadData 命令并调用 run_command_live."""
    commands = []

    def fake_run(cmd):
        commands.append(list(cmd))

    monkeypatch.setattr(quality_control, "run_command_live", fake_run)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "sample001_R1.fastq.gz").write_text("r1")
    (input_dir / "sample001_R2.fastq.gz").write_text("r2")

    output_dir = tmp_path / "output"
    quality_control.run_qc(
        input_dir=input_dir,
        output_dir=output_dir,
        threads=8,
        kneaddata_db="/db/kneaddata",
    )

    # 1 条 fastqc（聚合所有样本文件）+ 1 条 kneaddata（每个配对样本一条）
    assert len(commands) == 2

    fastqc_cmd = commands[0]
    assert fastqc_cmd[0] == "fastqc"
    assert str(input_dir / "sample001_R1.fastq.gz") in fastqc_cmd
    assert str(input_dir / "sample001_R2.fastq.gz") in fastqc_cmd
    assert "-o" in fastqc_cmd
    assert str(output_dir / "fastqc_reports") in fastqc_cmd
    assert fastqc_cmd[fastqc_cmd.index("-t") + 1] == "8"

    kneaddata_cmd = commands[1]
    assert kneaddata_cmd[0] == "kneaddata"
    assert kneaddata_cmd.count("--input") == 2
    assert str(output_dir / "kneaddata") in kneaddata_cmd
    assert "/db/kneaddata" in kneaddata_cmd
    assert "sample001" in kneaddata_cmd


def test_run_qc_fails_when_no_samples(tmp_path, monkeypatch):
    """输入目录无配对样本时应 fail-closed，不调用任何命令."""
    commands = []
    monkeypatch.setattr(
        quality_control, "run_command_live", lambda cmd: commands.append(list(cmd))
    )

    input_dir = tmp_path / "empty_input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"

    with pytest.raises(NoSamplesError, match="未找到"):
        quality_control.run_qc(
            input_dir=input_dir,
            output_dir=output_dir,
            threads=4,
            kneaddata_db="/db/kneaddata",
        )

    assert commands == []
    # 输出目录在发现样本前创建，便于后续排错
    assert (output_dir / "fastqc_reports").exists()
    assert (output_dir / "kneaddata").exists()


def test_run_qc_passes_metadata_path_to_sample_discovery(tmp_path, monkeypatch):
    """run_qc 应将 metadata_path 转为 Path 传给 Sample.discover_paired."""
    captured = {}

    class FakeSample:
        @staticmethod
        def discover_paired(
            input_dir,
            r1_pattern="*_R1.fastq.gz",
            r2_suffix="_R2.fastq.gz",
            metadata_path=None,
            sample_id_column="sample-id",
        ):
            captured["metadata_path"] = metadata_path
            return []

    monkeypatch.setattr(quality_control, "Sample", FakeSample)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    with pytest.raises(NoSamplesError):
        quality_control.run_qc(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
            threads=4,
            kneaddata_db="/db/kneaddata",
            metadata_path="config/samples.tsv",
        )

    assert captured["metadata_path"] == Path("config/samples.tsv")
