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
            output_idx = cmd.index("--output")
            Path(cmd[output_idx + 1]).write_text("read\t1\t562")

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
    assert str(output_dir / "sample001.kraken") in krona_cmd
    assert krona_cmd[krona_cmd.index("-t") + 1] == "3"


def test_run_taxonomic_profiling_parallel_samples_share_thread_budget(
    tmp_path, monkeypatch
):
    """多样本并行时，每个 Kraken2 的 --threads 之和不超过总线程预算."""
    commands = []

    def fake_run(cmd):
        commands.append(list(cmd))
        if cmd[0] == "kraken2":
            report_idx = cmd.index("--report")
            Path(cmd[report_idx + 1]).write_text("report")
            output_idx = cmd.index("--output")
            Path(cmd[output_idx + 1]).write_text("read\t1\t562")

    monkeypatch.setattr(taxonomic_profiling, "run_command_live", fake_run)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    for name in ("sample001", "sample002"):
        (input_dir / f"{name}_paired_1.fastq").write_text("r1")
        (input_dir / f"{name}_paired_2.fastq").write_text("r2")

    output_dir = tmp_path / "output"
    taxonomic_profiling.run_taxonomic_profiling(
        input_dir=input_dir,
        output_dir=output_dir,
        threads=4,
        kraken2_db="/db/kraken2",
    )

    kraken2_cmds = [cmd for cmd in commands if cmd[0] == "kraken2"]
    assert len(kraken2_cmds) == 2
    per_sample_threads = [int(cmd[cmd.index("--threads") + 1]) for cmd in kraken2_cmds]
    # 2 个样本并行，4 线程预算 -> 每样本 2 线程
    assert per_sample_threads == [2, 2]
    assert sum(per_sample_threads) <= 4

    biom_cmd = next(cmd for cmd in commands if cmd[0] == "kraken-biom")
    assert str(output_dir / "sample001.report") in biom_cmd
    assert str(output_dir / "sample002.report") in biom_cmd
    # 样本发现顺序保持稳定，biom 输入顺序与之一致
    assert biom_cmd.index(str(output_dir / "sample001.report")) < biom_cmd.index(
        str(output_dir / "sample002.report")
    )


def test_run_taxonomic_profiling_ignores_stale_report_files(tmp_path, monkeypatch):
    """输出目录中历史运行的 .report 不应混入本次 BIOM 与 Krona."""
    commands = []

    def fake_run(cmd):
        commands.append(list(cmd))
        if cmd[0] == "kraken2":
            report_idx = cmd.index("--report")
            Path(cmd[report_idx + 1]).write_text("report")
            output_idx = cmd.index("--output")
            Path(cmd[output_idx + 1]).write_text("read\t1\t562")

    monkeypatch.setattr(taxonomic_profiling, "run_command_live", fake_run)

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "sample001_paired_1.fastq").write_text("r1")
    (input_dir / "sample001_paired_2.fastq").write_text("r2")

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    stale_report = output_dir / "stale_sample.report"
    stale_report.write_text("stale")

    taxonomic_profiling.run_taxonomic_profiling(
        input_dir=input_dir,
        output_dir=output_dir,
        threads=4,
        kraken2_db="/db/kraken2",
    )

    sample_report = str(output_dir / "sample001.report")
    sample_kraken = str(output_dir / "sample001.kraken")
    biom_cmd = next(cmd for cmd in commands if cmd[0] == "kraken-biom")
    assert sample_report in biom_cmd
    assert str(stale_report) not in biom_cmd

    krona_cmds = [cmd for cmd in commands if cmd[0] == "ktImportTaxonomy"]
    assert len(krona_cmds) == 1
    assert sample_kraken in krona_cmds[0]
    assert "-q" in krona_cmds[0] and "-t" in krona_cmds[0]
    assert str(stale_report) not in krona_cmds[0]


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
