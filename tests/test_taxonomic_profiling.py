# -*- coding: utf-8 -*-
"""测试物种分类模块（命令拼装层）。"""

from pathlib import Path

import pytest

from micos import taxonomic_profiling
from micos.errors import NoSamplesError


def test_run_taxonomic_profiling_assembles_kraken2_biom_and_krona_commands(
    tmp_path, monkeypatch
):
    """run_taxonomic_profiling 应拼装 Kraken2/kraken-biom/Krona 命令."""
    commands = []

    def fake_run(cmd):
        commands.append(list(cmd))
        # 模拟 kraken2 生成 report 文件，触发后续 kraken-biom 与 Krona
        if cmd[0] == "kraken2":
            report_idx = cmd.index("--report")
            Path(cmd[report_idx + 1]).write_text("report")

    monkeypatch.setattr(taxonomic_profiling, "run_command_live", fake_run)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "sample001_paired_1.fastq").write_text("r1")
    (input_dir / "sample001_paired_2.fastq").write_text("r2")

    output_dir = tmp_path / "output"
    taxonomic_profiling.run_taxonomic_profiling(
        input_dir=input_dir,
        output_dir=output_dir,
        threads=8,
        kraken2_db="/db/kraken2",
        confidence=0.1,
    )

    # 1 kraken2 + 1 kraken-biom + 1 ktImportTaxonomy
    assert [cmd[0] for cmd in commands] == [
        "kraken2",
        "kraken-biom",
        "ktImportTaxonomy",
    ]

    kraken2_cmd = commands[0]
    assert kraken2_cmd[0] == "kraken2"
    assert "/db/kraken2" in kraken2_cmd
    assert "--paired" in kraken2_cmd
    assert kraken2_cmd[kraken2_cmd.index("--confidence") + 1] == "0.1"
    assert kraken2_cmd[kraken2_cmd.index("--threads") + 1] == "8"

    biom_cmd = commands[1]
    assert biom_cmd[0] == "kraken-biom"
    assert str(output_dir / "feature-table.biom") in biom_cmd

    krona_cmd = commands[2]
    assert krona_cmd[0] == "ktImportTaxonomy"
    assert "-o" in krona_cmd


def test_run_taxonomic_profiling_fails_when_no_samples(tmp_path, monkeypatch):
    """无样本时应 fail-closed，不调用任何命令."""
    commands = []
    monkeypatch.setattr(
        taxonomic_profiling,
        "run_command_live",
        lambda cmd: commands.append(list(cmd)),
    )

    input_dir = tmp_path / "empty"
    input_dir.mkdir()
    output_dir = tmp_path / "output"

    with pytest.raises(NoSamplesError, match="未找到"):
        taxonomic_profiling.run_taxonomic_profiling(
            input_dir=input_dir,
            output_dir=output_dir,
            threads=4,
            kraken2_db="/db/kraken2",
        )

    assert commands == []


def test_run_taxonomic_profiling_passes_metadata_path(tmp_path, monkeypatch):
    """run_taxonomic_profiling 应将 metadata_path 转为 Path 传给 Sample.discover_cleaned."""
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

    monkeypatch.setattr(taxonomic_profiling, "Sample", FakeSample)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    with pytest.raises(NoSamplesError):
        taxonomic_profiling.run_taxonomic_profiling(
            input_dir=input_dir,
            output_dir=tmp_path / "output",
            threads=4,
            kraken2_db="/db/kraken2",
            metadata_path="config/samples.tsv",
        )

    assert captured["metadata_path"] == Path("config/samples.tsv")
