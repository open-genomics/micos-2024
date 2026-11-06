# -*- coding: utf-8 -*-
"""质量控制模块，包含 FastQC 和 KneadData 的功能。

该模块是**深层模块**，隐藏了质量控制的复杂性：
- 调用者只需提供输入目录和配置
- 样本发现、配对验证、工具调用等逻辑被隐藏
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from micos.errors import NoSamplesError
from micos.sample import Sample
from micos.utils import run_command_live

logger = logging.getLogger(__name__)


def run_qc(
    input_dir: str | Path,
    output_dir: str | Path,
    threads: int,
    kneaddata_db: str | Path,
    metadata_path: str | Path | None = None,
) -> None:
    """执行质量控制 (FastQC + KneadData).

    这是一个深层模块的接口，调用者只需提供必要的配置，
    样本发现、配对验证、工具调用等细节被隐藏。

    Args:
        input_dir: 输入 FASTQ 文件目录
        output_dir: 输出目录
        threads: 线程数
        kneaddata_db: KneadData 数据库路径
        metadata_path: 可选的样本元数据 TSV 路径，按 sample-id 列
            与发现的样本名 join 填充 Sample.metadata

    Raises:
        subprocess.CalledProcessError: 工具执行失败时抛出
        FileNotFoundError: 工具未安装时抛出
    """
    logger.info("步骤 1: 开始质量控制分析...")

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # 1. 创建输出目录
    fastqc_output_dir = output_path / "fastqc_reports"
    kneaddata_output_dir = output_path / "kneaddata"
    fastqc_output_dir.mkdir(parents=True, exist_ok=True)
    kneaddata_output_dir.mkdir(parents=True, exist_ok=True)

    # 2. 使用 Sample 类发现样本
    metadata_arg = Path(metadata_path) if metadata_path else None
    samples = Sample.discover_paired(input_path, metadata_path=metadata_arg)
    if not samples:
        raise NoSamplesError(
            f"在 {input_path} 中未找到配对的 FASTQ 文件；"
            "期望命名形如 sample_R1.fastq.gz / sample_R2.fastq.gz。"
        )

    if metadata_arg:
        matched = sum(1 for s in samples if s.metadata)
        logger.info(
            f"已加载 {matched}/{len(samples)} 个样本的元数据 (来源: {metadata_arg})"
        )

    # 3. 运行 FastQC
    logger.info("--> 正在运行 FastQC...")
    all_fastq_files: list[str] = []
    for sample in samples:
        all_fastq_files.extend(str(f) for f in sample.files)

    fastqc_cmd = [
        "fastqc",
        *all_fastq_files,
        "-o",
        str(fastqc_output_dir),
        "-t",
        str(threads),
    ]
    try:
        run_command_live(fastqc_cmd)
        logger.info("FastQC 运行成功。")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"FastQC 运行失败: {e}")
        logger.error("请确保 fastqc 已安装并位于系统的 PATH 中。")
        raise

    # 4. 运行 KneadData
    logger.info("--> 正在运行 KneadData...")
    for sample in samples:
        if not sample.is_paired:
            logger.warning(f"样本 {sample.name} 不是双端测序，跳过 KneadData。")
            continue

        logger.info(f"处理样本: {sample.name}")

        kneaddata_cmd = [
            "kneaddata",
            "--input",
            str(sample.r1_path),
            "--input",
            str(sample.r2_path),
            "--output",
            str(kneaddata_output_dir),
            "--reference-db",
            str(kneaddata_db),
            "--threads",
            str(threads),
            "--output-prefix",
            sample.name,
        ]
        try:
            run_command_live(kneaddata_cmd)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"KneadData 运行失败 (样本: {sample.name}): {e}")
            logger.error(
                "请确保 kneaddata 已安装并位于系统的 PATH 中，并且数据库路径正确。"
            )
            raise

    logger.info("质量控制分析完成。")
