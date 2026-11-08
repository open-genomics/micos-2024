# -*- coding: utf-8 -*-
"""物种分类模块。

该模块是**深层模块**，隐藏了物种分类的复杂性：
- 调用者只需提供输入目录和配置
- 样本发现、工具调用、结果聚合等逻辑被隐藏
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from micos.errors import NoSamplesError, StageOutputError
from micos.sample import Sample
from micos.utils import run_command_live

logger = logging.getLogger(__name__)


def run_taxonomic_profiling(
    input_dir: str | Path,
    output_dir: str | Path,
    threads: int,
    kraken2_db: str | Path,
    confidence: float = 0.1,
    metadata_path: str | Path | None = None,
) -> None:
    """执行物种分类 (Kraken2 + Krona).

    Args:
        input_dir: 输入目录（KneadData 清理后的 FASTQ 文件）
        output_dir: 输出目录
        threads: 线程数
        kraken2_db: Kraken2 数据库路径
        confidence: Kraken2 分类置信度阈值 (0.0-1.0)
        metadata_path: 可选的样本元数据 TSV 路径，按 sample-id 列
            与发现的样本名 join 填充 Sample.metadata

    Raises:
        subprocess.CalledProcessError: 工具执行失败时抛出
        FileNotFoundError: 工具未安装时抛出
    """
    logger.info("步骤 2: 开始物种分类分析...")

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 使用 Sample 类发现清洗后的样本
    metadata_arg = Path(metadata_path) if metadata_path else None
    samples = Sample.discover_cleaned(input_path, metadata_path=metadata_arg)
    if not samples:
        raise NoSamplesError(
            f"在 {input_path} 中未找到 KneadData 清洗后的配对样本；"
            "期望命名形如 sample_paired_1.fastq / sample_paired_2.fastq。"
        )

    # 2. 运行 Kraken2
    paired_samples = [sample for sample in samples if sample.is_paired]
    for sample in samples:
        if not sample.is_paired:
            logger.warning(f"样本 {sample.name} 不是双端测序，跳过 Kraken2。")

    # 每个 Kraken2 进程都会按 --threads 开线程；并行样本数与单样本线程数共享
    # 同一份线程预算，避免 N 个进程各开 threads 线程造成 CPU 超订。
    workers = max(1, min(len(paired_samples), threads))
    per_sample_threads = max(1, threads // workers)
    logger.info(
        f"--> 正在运行 Kraken2（{len(paired_samples)} 个样本，"
        f"并行 {workers}，每样本 {per_sample_threads} 线程）..."
    )

    def run_kraken2(sample: Sample) -> Path:
        logger.info(f"处理样本: {sample.name}")
        kraken2_output = output_path / f"{sample.name}.kraken"
        kraken2_report = output_path / f"{sample.name}.report"
        run_command_live(
            [
                "kraken2",
                "--db",
                str(kraken2_db),
                "--paired",
                str(sample.r1_path),
                str(sample.r2_path),
                "--output",
                str(kraken2_output),
                "--report",
                str(kraken2_report),
                "--confidence",
                str(confidence),
                "--threads",
                str(per_sample_threads),
            ]
        )
        return kraken2_report

    report_files: list[Path] = []
    if paired_samples:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # map 保持输入顺序，后续 kraken-biom/Krona 的输入与样本发现顺序一致。
            report_files = list(executor.map(run_kraken2, paired_samples))

    if not report_files:
        raise StageOutputError(
            f"Kraken2 执行完成，但 {output_path} 中没有生成任何 .report 文件。"
        )

    logger.info("--> 正在生成 BIOM 文件...")
    biom_output = output_path / "feature-table.biom"
    run_command_live(
        [
            "kraken-biom",
            *[str(f) for f in report_files],
            "-o",
            str(biom_output),
        ]
    )

    logger.info("--> 正在生成 Krona 图表...")
    for report_file in report_files:
        krona_output = output_path / f"{report_file.stem}.krona.html"
        # Kraken2 逐条输出（.kraken）第 2 列是 read ID、第 3 列是 taxid；
        # report 第 3 列却是 reads 计数，不能直接套用 -q 2 -t 3。
        kraken_file = report_file.with_suffix(".kraken")
        if kraken_file.exists():
            krona_input = ["-q", "2", "-t", "3", str(kraken_file)]
        else:
            logger.warning(
                f"未找到 {kraken_file}，改用 report 的 taxid/magnitude 列生成 Krona 图表。"
            )
            krona_input = ["-t", "5", "-m", "2", str(report_file)]
        run_command_live(
            [
                "ktImportTaxonomy",
                *krona_input,
                "-o",
                str(krona_output),
            ]
        )

    logger.info("物种分类分析完成。")
